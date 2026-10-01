# -*- coding: utf-8 -*-
"""Unit tests for amzqr.amzqr._build_combine_mask.

The helper builds the reserved-region paste mask that combine() uses to
composite the background onto the QR. These tests lock the mask's geometry
(finder / timing / alignment / sampling holes), and a gold-standard parity
test compares the final mask (geometric mask x bg-alpha) against a naive
per-pixel reimplementation of the former combine() hot loop, proving the
optimized path is pixel-identical to the old one.
"""

import pytest
from PIL import Image, ImageChops

from amzqr import amzqr
from amzqr.mylibs import constant


def _data_area(ver):
    n = (ver - 1) * 4 + 21  # matrix side in modules
    return n * constant.PIXELS_PER_MODULE, n * constant.PIXELS_PER_MODULE


def test_mask_allows_clear_data_pixel():
    data_w, data_h = _data_area(1)  # ver1: n=21 -> 63 px
    mask = amzqr._build_combine_mask(data_w, data_h, 1)
    # (30,30) is a data pixel: outside finders, timing, and sampling holes.
    assert mask.getpixel((30, 30)) == 255


def test_mask_reserves_finder_corners():
    data_w, data_h = _data_area(1)
    mask = amzqr._build_combine_mask(data_w, data_h, 1)
    assert mask.getpixel((5, 5)) == 0  # top-left
    assert mask.getpixel((data_w - 5, 5)) == 0  # top-right
    assert mask.getpixel((5, data_h - 5)) == 0  # bottom-left


def test_mask_reserves_timing():
    data_w, data_h = _data_area(1)
    t = constant.TIMING_MODULE * constant.PIXELS_PER_MODULE  # 18
    mask = amzqr._build_combine_mask(data_w, data_h, 1)
    assert mask.getpixel((t + 1, 10)) == 0  # timing column
    assert mask.getpixel((10, t + 1)) == 0  # timing row


def test_mask_reserves_only_module_centers():
    # The sampling hole is the exact module center (i%3==1 AND j%3==1); a
    # neighbour sharing only ONE coordinate must stay drawable. Guards the
    # AND semantics (centre pixel only), not a full line.
    data_w, data_h = _data_area(1)
    mask = amzqr._build_combine_mask(data_w, data_h, 1)
    assert mask.getpixel((31, 31)) == 0  # centre of module (10,10)
    assert mask.getpixel((31, 30)) == 255  # shares x only -> not a hole


def test_mask_reserves_alignment_blocks():
    data_w, data_h = _data_area(7)
    mask = amzqr._build_combine_mask(data_w, data_h, 7)
    aloc = constant.alig_location[7 - 2]
    L = len(aloc)
    found = False
    for a in range(L):
        for b in range(L):
            if (a == b == 0) or (a == L - 1 and b == 0) or (a == 0 and b == L - 1):
                continue
            cx, cy = aloc[a], aloc[b]
            x = cx * constant.PIXELS_PER_MODULE + 1
            y = cy * constant.PIXELS_PER_MODULE + 1
            assert mask.getpixel((x, y)) == 0
            found = True
    assert found


def _naive_ref_mask(data_w, data_h, ver, alpha):
    """Mirror the ORIGINAL combine() hot loop condition, as an oracle."""
    from amzqr.mylibs.constant import (
        FINDER_REGION_PX,
        TIMING_MODULE,
        alig_location,
    )
    from amzqr.mylibs.constant import (
        PIXELS_PER_MODULE as ppm,
    )

    aligs = []
    if ver > 1:
        aloc = alig_location[ver - 2]
        L = len(aloc)
        for a in range(L):
            for b in range(L):
                if (a == b == 0) or (a == L - 1 and b == 0) or (a == 0 and b == L - 1):
                    continue
                for i in range(ppm * (aloc[a] - 2), ppm * (aloc[a] + 3)):
                    for j in range(ppm * (aloc[b] - 2), ppm * (aloc[b] + 3)):
                        aligs.append((i, j))
    timing = set(range(TIMING_MODULE * ppm, (TIMING_MODULE + 1) * ppm))
    rfs = data_w - FINDER_REGION_PX
    bfs = data_h - FINDER_REGION_PX
    ref = Image.new("L", (data_w, data_h), 255)
    for i in range(data_w):
        for j in range(data_h):
            if (
                (i in timing)
                or (j in timing)
                or (i < FINDER_REGION_PX and j < FINDER_REGION_PX)
                or (i < FINDER_REGION_PX and j >= bfs)
                or (i >= rfs and j < FINDER_REGION_PX)
                or (i, j) in aligs
                or (i % ppm == ppm // 2 and j % ppm == ppm // 2)
                or alpha.getpixel((i, j)) == 0
            ):
                ref.putpixel((i, j), 0)
    return ref


@pytest.mark.parametrize("ver", [1, 2, 7])
def test_mask_parity_with_original_loop(ver):
    data_w, data_h = _data_area(ver)
    # alpha covers the full brightness range across three regions: opaque
    # (255), a partially-transparent band (128), and fully transparent (0).
    # The partial band exercises the semi-transparent pg path, where the
    # original putpixel drew the bg pixel at full strength instead of
    # alpha-blending; the oracle treats any alpha != 0 as "draw".
    alpha = Image.new("L", (data_w, data_h), 255)
    for x in range(data_w // 4, 3 * data_w // 4):
        for y in range(data_h // 4, 3 * data_h // 4):
            alpha.putpixel((x, y), 128)
    for x in range(data_w // 2 - data_w // 8, data_w // 2 + data_w // 8):
        for y in range(data_h // 2 - data_h // 8, data_h // 2 + data_h // 8):
            alpha.putpixel((x, y), 0)
    # Replicate combine()'s pipeline: threshold bg alpha to binary (0/255)
    # before multiplying, so the final mask hard-replaces like putpixel did.
    got = ImageChops.multiply(
        amzqr._build_combine_mask(data_w, data_h, ver),
        alpha.point(lambda v: 255 if v else 0),
    )
    ref = _naive_ref_mask(data_w, data_h, ver, alpha)
    diff = ImageChops.difference(got, ref)
    assert diff.getbbox() is None, (ver, diff.getbbox())
