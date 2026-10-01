# -*- coding: utf-8 -*-
"""Benchmark: static picture QR code combine via amzqr.run()."""

import os

import pytest
from PIL import Image

from amzqr import amzqr

WORDS = {
    "short": "https://github.com/x-hw/amazing-qr",
    "long": "https://github.com/x-hw/amazing-qr" * 10,
}


def _make_bg(path, size):
    """Generate a solid-colour RGB image at *path* with the given square *size*."""
    img = Image.new("RGB", (size, size), color=(128, 128, 128))
    img.save(path)


@pytest.mark.parametrize("bg_size", [100, 400, 1200])
@pytest.mark.parametrize("colorized", [True, False])
@pytest.mark.parametrize("version", [1, 10, 40])
@pytest.mark.parametrize("ecl", ["L", "M", "Q", "H"])
@pytest.mark.parametrize("words_key", ["short", "long"])
def test_bench_combine_static(benchmark, tmp_path, bg_size, colorized, version, ecl, words_key):
    """Benchmark amzqr.run() with a static picture, covering all parameter combinations."""
    bg_path = os.path.join(str(tmp_path), "bg.png")
    _make_bg(bg_path, bg_size)

    words = WORDS[words_key]

    def _run():
        ver, level, name = amzqr.run(
            words,
            version=version,
            level=ecl,
            picture=bg_path,
            colorized=colorized,
            save_dir=str(tmp_path),
            save_name="out.png",
        )
        return ver, level, name

    result = benchmark(_run)
    ver, level, name = result
    assert ver >= version
    assert level == ecl
    assert os.path.isfile(name)
