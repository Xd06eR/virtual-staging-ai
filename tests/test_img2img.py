"""Cleanup helper for img2img (Q2/Q8: safe, non-silent unlink)."""
from app.img2img import _safe_unlink


def test_safe_unlink_removes_existing(tmp_path):
    f = tmp_path / "temp.png"
    f.write_bytes(b"x")
    _safe_unlink(f)
    assert not f.exists()


def test_safe_unlink_missing_is_noop(tmp_path):
    _safe_unlink(tmp_path / "ghost.png")  # must not raise
