"""
Data Models
Defines the Pydantic schemas for API requests and responses.
"""
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import DATA_INPUT_DIR, SAMPLES_DIR

# image_path is confined to these roots to prevent path traversal — the API must
# never read or copy a file the caller points it at outside the data dirs.
ALLOWED_INPUT_ROOTS = (DATA_INPUT_DIR.resolve(), SAMPLES_DIR.resolve())
ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class EnhancePromptRequest(BaseModel):
    room_description: str = Field(
        ..., min_length=1, max_length=2000, description="User provided description of the room"
    )


class EnhancePromptResponse(BaseModel):
    enhanced_prompt: str
    room_description: str
    success: bool
    error: Optional[str] = None

    @model_validator(mode="after")
    def _success_xor_error(self):
        if self.success and self.error is not None:
            raise ValueError("error must be None when success is True")
        if not self.success and self.error is None:
            raise ValueError("error must be set when success is False")
        return self


class GenerateImageRequest(BaseModel):
    enhanced_prompt: str = Field(..., min_length=1, max_length=4000)
    room_description: str = Field(..., min_length=1, max_length=2000)
    image_path: str = Field(..., description="Path to the input image, inside an allowed data dir")
    target_resolution: int = Field(
        1024, ge=256, le=4096, description="Target resolution for the shortest side"
    )

    @field_validator("image_path")
    @classmethod
    def _confine_image_path(cls, value: str) -> str:
        resolved = Path(value).resolve()
        if resolved.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
            raise ValueError(f"unsupported image type: {resolved.suffix or '(none)'}")
        if not any(resolved.is_relative_to(root) for root in ALLOWED_INPUT_ROOTS):
            raise ValueError("image_path must be inside an allowed input directory")
        return str(resolved)


class GenerateImageResponse(BaseModel):
    enhanced_prompt: Optional[str] = None
    image_path: Optional[str] = None
    success: bool
    error: Optional[str] = None

    @model_validator(mode="after")
    def _success_xor_error(self):
        if self.success and self.error is not None:
            raise ValueError("error must be None when success is True")
        if not self.success and self.error is None:
            raise ValueError("error must be set when success is False")
        return self
