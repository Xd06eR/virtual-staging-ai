"""Error handling for WorkflowManager (Q3: no silent default dimensions)."""
import pytest
from PIL import UnidentifiedImageError

from app.workflow_manager import WorkflowManager


def test_get_image_dimensions_raises_on_non_image(tmp_path):
    bad = tmp_path / "notimage.txt"
    bad.write_text("not an image")
    wm = WorkflowManager()
    with pytest.raises(UnidentifiedImageError):
        wm._get_image_dimensions(bad)
