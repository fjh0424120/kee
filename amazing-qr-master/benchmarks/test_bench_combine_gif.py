# -*- coding: utf-8 -*-
"""Benchmark: GIF multi-frame QR code combine via amzqr.run()."""

import os

import pytest
from PIL import Image

from amzqr import amzqr

WORDS = {
    "short": "https://github.com/x-hw/amazing-qr",
    "long": "https://github.com/x-hw/amazing-qr" * 10,
}


def _make_test_gif(path, frame_count, size):
    """Generate a multi-frame GIF at *path* with solid-colour frames.

    Each frame is a solid RGB square of the given *size*.  All frames share
    a uniform 100 ms duration.
    """
    frames = []
    for i in range(frame_count):
        im = Image.new("RGB", (size, size), color=(min(i * 80, 255), 0, 0))
        frames.append(im)
    durations = [100] * frame_count
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
    )


@pytest.mark.parametrize("frame_count", [1, 3, 10])
@pytest.mark.parametrize("bg_size", [100, 400, 1200])
@pytest.mark.parametrize("colorized", [True, False])
@pytest.mark.parametrize("version", [1, 10, 40])
@pytest.mark.parametrize("ecl", ["L", "M", "Q", "H"])
@pytest.mark.parametrize("words_key", ["short", "long"])
def test_bench_combine_gif(
    benchmark, tmp_path, frame_count, bg_size, colorized, version, ecl, words_key
):
    """Benchmark amzqr.run() with a GIF picture, covering all parameter combinations."""
    gif_path = os.path.join(str(tmp_path), "input.gif")
    _make_test_gif(gif_path, frame_count, bg_size)

    words = WORDS[words_key]

    def _run():
        ver, level, name = amzqr.run(
            words,
            version=version,
            level=ecl,
            picture=gif_path,
            colorized=colorized,
            save_dir=str(tmp_path),
            save_name="out.gif",
        )
        return ver, level, name

    result = benchmark(_run)
    ver, level, name = result
    assert ver >= version
    assert level == ecl
    assert os.path.isfile(name)
