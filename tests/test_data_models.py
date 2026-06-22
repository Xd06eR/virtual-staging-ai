"""Validation invariants for app.data_models (audit hardening).

Covers S1 (image_path confinement), S3 (resolution bounds), S6 (string bounds),
and the success/error illegal-state rule on response models.
"""
import pytest
from pydantic import ValidationError

from app.config import DATA_INPUT_DIR, SAMPLES_DIR
from app.data_models import (
    EnhancePromptRequest,
    EnhancePromptResponse,
    GenerateImageRequest,
    GenerateImageResponse,
)

VALID_INPUT = str(DATA_INPUT_DIR / "empty_room_00001.png")
VALID_SAMPLE = str(SAMPLES_DIR / "demo.png")


def make_request(**overrides):
    base = dict(
        enhanced_prompt="a cozy staged room",
        room_description="cozy",
        image_path=VALID_INPUT,
        target_resolution=1024,
    )
    base.update(overrides)
    return GenerateImageRequest(**base)


class TestImagePathConfinement:
    def test_accepts_path_inside_input_dir(self):
        assert make_request().image_path == VALID_INPUT

    def test_accepts_path_inside_samples_dir(self):
        assert make_request(image_path=VALID_SAMPLE).image_path == VALID_SAMPLE

    def test_rejects_absolute_path_outside_roots(self):
        with pytest.raises(ValidationError):
            make_request(image_path="/etc/passwd")

    def test_rejects_traversal_escape(self):
        escape = str(DATA_INPUT_DIR / ".." / ".." / ".." / "etc" / "passwd")
        with pytest.raises(ValidationError):
            make_request(image_path=escape)

    def test_rejects_unsupported_extension(self):
        with pytest.raises(ValidationError):
            make_request(image_path=str(DATA_INPUT_DIR / "secret.txt"))


class TestTargetResolutionBounds:
    def test_rejects_zero(self):
        with pytest.raises(ValidationError):
            make_request(target_resolution=0)

    def test_rejects_too_large(self):
        with pytest.raises(ValidationError):
            make_request(target_resolution=100_000)

    def test_accepts_in_range(self):
        assert make_request(target_resolution=2048).target_resolution == 2048


class TestStringBounds:
    def test_rejects_empty_description(self):
        with pytest.raises(ValidationError):
            EnhancePromptRequest(room_description="")

    def test_rejects_overlong_description(self):
        with pytest.raises(ValidationError):
            EnhancePromptRequest(room_description="x" * 5000)

    def test_accepts_normal_description(self):
        assert EnhancePromptRequest(room_description="a modern living room").room_description


class TestResponseIllegalState:
    def test_success_with_error_rejected(self):
        with pytest.raises(ValidationError):
            EnhancePromptResponse(
                enhanced_prompt="p", room_description="d", success=True, error="boom"
            )

    def test_failure_without_error_rejected(self):
        with pytest.raises(ValidationError):
            GenerateImageResponse(success=False)

    def test_valid_success_response(self):
        resp = GenerateImageResponse(enhanced_prompt="p", image_path="/out/x.png", success=True)
        assert resp.success and resp.error is None