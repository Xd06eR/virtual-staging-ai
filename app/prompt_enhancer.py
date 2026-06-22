"""
Prompt Enhancer Module
Handles interaction with Ollama to convert raw descriptions into Stable Diffusion prompts.
"""
import ollama
from app.config import OLLAMA_MODEL, SYSTEM_PROMPT

class Ollama:
    def __init__(self, model_name: str = OLLAMA_MODEL, system_prompt: str = SYSTEM_PROMPT):
        self.model_name = model_name
        self.system_prompt = system_prompt

    def enhance_prompt(self, room_description: str) -> str:
        """
        Sends the user description to Ollama and returns a refined prompt.
        
        Args:
            room_description (str): Raw user input.
            
        Returns:
            str: The enhanced prompt suitable for image generation.
        """
        try:
            # Append /no_think to discourage chain-of-thought output if model supports it
            prompt_content = f"{room_description}\n/no_think"
            
            response = ollama.generate(
                model=self.model_name,
                system=self.system_prompt,
                prompt=prompt_content,
                stream=False,
                keep_alive=0
            )
            return response["response"].strip()
        
        except Exception as e:
            raise RuntimeError(f"Ollama interaction failed: {e}") from e