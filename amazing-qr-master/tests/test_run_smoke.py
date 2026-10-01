# -*- coding: utf-8 -*-
"""Smoke tests for amzqr.amzqr.run — the public API.

These only exercise the no-picture path (base QR scaled 3x and saved), to
avoid depending on any image fixtures. They confirm the public contract
(returned tuple shape + output file existence) without pinning pixels.
"""

import os

import pytest

from amzqr import amzqr


def test_run_plain_writes_png(tmp_path):
    ver, level, name = amzqr.run("https://github.com", save_dir=str(tmp_path))
    out = os.path.join(str(tmp_path), os.path.basename(name))
    assert os.path.isfile(out)
    assert os.path.getsize(out) > 0
    assert ver >= 1
    assert level in ("L", "M", "Q", "H")


def test_run_rejects_unsupported_chars(tmp_path):
    with pytest.raises(ValueError):
        amzqr.run("你好", save_dir=str(tmp_path))


def test_run_rejects_bad_version(tmp_path):
    with pytest.raises(ValueError):
        amzqr.run("https://github.com", version=0, save_dir=str(tmp_path))


# --- extension validation ----------------------------------------------------


def _make_dummy_file(path, suffix):
    """Create a minimal (1×1) image file at the given path for extension tests.

    Uses ``format="PNG"`` so that Pillow can write the file even when the
    extension is not a standard image extension (e.g. ``.svg`` / ``.bmp2``).
    """
    from PIL import Image

    fpath = path / ("dummy" + suffix)
    img = Image.new("RGB", (1, 1), "white")
    img.save(str(fpath), format="PNG")
    return str(fpath)


def test_run_accepts_jpeg_extension(tmp_path):
    """`.jpeg` (5 chars) must be accepted, not rejected by a fragile [-4:] slice."""
    pic = _make_dummy_file(tmp_path, ".jpeg")
    ver, level, name = amzqr.run("https://github.com", picture=pic, save_dir=str(tmp_path))
    assert os.path.isfile(name)


def test_run_accepts_uppercase_extension(tmp_path):
    """`.JPEG` / `.PNG` etc. must be accepted case-insensitively."""
    for ext in (".JPEG", ".PNG", ".BMP", ".JPG", ".GIF"):
        pic = _make_dummy_file(tmp_path, ext)
        ver, level, name = amzqr.run("https://github.com", picture=pic, save_dir=str(tmp_path))
        assert os.path.isfile(name)


def test_run_rejects_unsupported_picture_extension(tmp_path):
    """`.tiff` / `.webp` etc. must raise ValueError."""
    for ext in (".tiff", ".webp", ".svg", ".bmp2"):
        pic = _make_dummy_file(tmp_path, ext)
        with pytest.raises(ValueError, match="Wrong picture!"):
            amzqr.run("https://github.com", picture=pic, save_dir=str(tmp_path))


def test_run_rejects_unsupported_save_name_extension(tmp_path):
    """save_name with unsupported extension must raise ValueError."""
    for ext in ("output.tiff", "output.webp", "output.svg"):
        with pytest.raises(ValueError, match="Wrong save_name!"):
            amzqr.run("https://github.com", save_name=ext, save_dir=str(tmp_path))


def test_run_accepts_jpeg_save_name(tmp_path):
    """`.jpeg` save_name must be accepted."""
    ver, level, name = amzqr.run("https://github.com", save_name="out.jpeg", save_dir=str(tmp_path))
    assert os.path.isfile(name)


def test_run_accepts_uppercase_save_name(tmp_path):
    """`.JPEG` / `.PNG` save_name must be accepted case-insensitively."""
    for ext in ("out.JPEG", "out.PNG", "out.BMP", "out.JPG", "out.GIF"):
        ver, level, name = amzqr.run("https://github.com", save_name=ext, save_dir=str(tmp_path))
        assert os.path.isfile(name)


def test_run_gif_picture_requires_gif_save_name(tmp_path):
    """GIF picture + non-GIF save_name must raise ValueError."""
    pic = _make_dummy_file(tmp_path, ".gif")
    with pytest.raises(ValueError, match="Wrong save_name!"):
        amzqr.run("https://github.com", picture=pic, save_name="out.png", save_dir=str(tmp_path))


def test_run_gif_picture_accepts_uppercase_gif_save_name(tmp_path):
    """GIF picture + .GIF (uppercase) save_name must pass validation."""
    pic = _make_dummy_file(tmp_path, ".gif")
    ver, level, name = amzqr.run(
        "https://github.com", picture=pic, save_name="out.GIF", save_dir=str(tmp_path)
    )
    assert os.path.isfile(name)
