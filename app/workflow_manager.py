"""
Workflow Manager
Handles loading and modifying the ComfyUI workflow JSON format.
"""
import json
import random
import copy
from pathlib import Path
from PIL import Image

from app.config import CHECKPOINT_NAME

class WorkflowManager:
    DEFAULT_WORKFLOW_PATH = Path("workflows/virtual_staging_workflow.json")

    def __init__(self):
        self.checkpoint_name = CHECKPOINT_NAME
        self.base_workflow = self._load_base_workflow()

    def _load_base_workflow(self) -> dict:
        """Loads the template JSON workflow from disk."""
        # Resolve relative to this file so the loader works from any CWD.
        workflow_path = Path(__file__).parent.parent / self.DEFAULT_WORKFLOW_PATH
        with open(workflow_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _get_image_dimensions(self, image_path: Path) -> tuple[int, int]:
        """Read image dimensions. Let PIL raise if the file is not a valid image."""
        with Image.open(image_path) as img:
            return img.size

    def _get_optimized_scale_factor(self, width: int, height: int, target: int = 1024, threshold: int = 128) -> float:
        """
        Calculates input scale factor for SDXL with a threshold to avoid unnecessary resizing.
        This ensures the image enters the diffusion process at an optimal size (approx 1024).
        """
        shortest_side = min(width, height)
        if shortest_side == 0:
            return 1.0

        # THRESHOLD CHECK: If within tolerance, skip resizing
        if abs(shortest_side - target) <= threshold:
            print(f"Image ({width}x{height}) is within SDXL threshold. Skipping initial resize.")
            return 1.0
        
        # CALC SCALE: If outside threshold, calculate factor for both upscale/downscale
        scale = target / shortest_side

        action = "Upscaling" if scale > 1.0 else "Downscaling"
        print(f"Image outside threshold. {action} input to ~{target}px.")
        
        return scale

    def create_custom_workflow(self, prompt: str, input_image_path: Path, output_prefix: str, target_resolution: int = 1024) -> dict:
        """
        Generates a runtime workflow with specific inputs inserted.
        
        Modifications:
        1. Injects image path, prompt, seed, and checkpoint.
        2. Calculates scaling to ensure SDXL works at ~1024px (Input Factor).
        3. Calculates final scaling to reach User Target Resolution (Output Factor).
        """
        workflow = copy.deepcopy(self.base_workflow)
        
        # 1. Calculations
        width, height = self._get_image_dimensions(input_image_path)
        shortest_side = min(width, height)

        input_scale_factor = self._get_optimized_scale_factor(width, height, target=1024, threshold=128)
        current_working_resolution = shortest_side * input_scale_factor

        if current_working_resolution > 0:
            final_scale_factor = target_resolution / current_working_resolution
        else:
            final_scale_factor = 1.0

        seed = random.randint(1, 1_000_000_000_000)

        # 2. Node Mapping (Node ID -> Input Key -> Value)
        node_updates = {
            "2":   {"image": input_image_path.name},      # Load Image Node
            "22":  {"text": prompt},                      # Positive Prompt Node
            "25":  {"seed": seed},                        # KSampler Node
            "7":   {"ckpt_name": self.checkpoint_name},   # Checkpoint Loader
            "213": {"factor": input_scale_factor},        # Initial Scale Node (SDXL Optimization)
            "126": {"filename_prefix": output_prefix},    # Save Image Node
        }

        # Apply updates
        for node_id, inputs in node_updates.items():
            if node_id in workflow:
                workflow[node_id]["inputs"].update(inputs)

        # 3. Topology Optimization
        is_final_res_exact = abs(target_resolution - current_working_resolution) < 1
        
        if is_final_res_exact:
            # Bypass Final Upscale: Connect VAE Decode (26) directly to Save Image (126)
            workflow["126"]["inputs"]["images"] = ["26", 0]
            # Remove Upscale Node (131) to keep graph clean
            workflow.pop("131", None)
        else:
            # Enable Final Upscale: Configure Upscale Node (131)
            if "131" in workflow:
                workflow["131"]["inputs"]["factor"] = final_scale_factor
                # Connect Upscale Node output to Save Image input
                workflow["126"]["inputs"]["images"] = ["131", 0]

        return workflow