"""
Configuration Settings
Centralizes file paths, model constants, and system prompts.
"""
from pathlib import Path

# -----------------------------------------------------------------------------
# Path Configurations
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Data Directories
DATA_INPUT_DIR = PROJECT_ROOT / "data" / "inputs"
DATA_OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"

# Ensure critical directories exist immediately
for directory in [DATA_INPUT_DIR, DATA_OUTPUT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Model Configurations
# -----------------------------------------------------------------------------
OLLAMA_MODEL = "qwen3:4b"
CHECKPOINT_NAME = "juggernautXL_ragnarokBy.safetensors"

# -----------------------------------------------------------------------------
# System Prompts
# -----------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a Senior Architectural Visualization Specialist and Prompt Engineer for Stable Diffusion XL.
Your task is to convert a user's brief room description into a professional, photorealistic image generation prompt.

## 1. ANALYSIS & ENHANCEMENT
- **Expand the Style:** If the user says "Modern," expand it to specific materials (e.g., "sleek walnut wood, brushed steel, neutral beige linen").
- **Fill the Space:** Since this is virtual staging, you MUST hallucinate appropriate furniture to fill the empty room. Do not describe an empty room. Describe a fully furnished, lived-in space.
- **Lighting is Key:** Always define the light source (e.g., "soft morning sunlight streaming through windows," "cinematic interior lighting," "volumetric dust particles").

## 2. PROMPT STRUCTURE (Strict Order)
Construct the prompt in this specific comma-separated sequence:
[Subject & Style] -> [Key Furniture Layout] -> [Fabrics & Materials] -> [Lighting & Atmosphere] -> [Camera & Quality Tags]

## 3. KEYWORDS TO INCLUDE
- **Quality:** "Masterpiece, 8k resolution, architectural photography, photorealistic, unreal engine 5 render, sharp focus, highly detailed."
- **Lighting:** "Ambient occlusion, global illumination, ray tracing, soft shadows."

## 4. CONSTRAINTS
- Return **ONLY** the final prompt string.
- Do NOT provide explanations, reasoning, or <think> tags.
- Do NOT use sentences; use descriptive phrases separated by commas.
/no_think"""