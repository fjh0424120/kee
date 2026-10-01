# -*- coding: utf-8 -*-
"""Benchmark: pure QR code generation via theqrmodule.get_qrcode()."""

import pytest

from amzqr.mylibs import theqrmodule

WORDS = {
    "short": "https://github.com/x-hw/amazing-qr",
    "long": "https://github.com/x-hw/amazing-qr" * 10,
}


@pytest.mark.parametrize("version", [1, 10, 20, 40])
@pytest.mark.parametrize("ecl", ["L", "M", "Q", "H"])
@pytest.mark.parametrize("words_key", ["short", "long"])
def test_bench_qr_generation(benchmark, tmp_path, version, ecl, words_key):
    """Benchmark the full QR generation pipeline: encode → ECC → structure → matrix → draw."""
    words = WORDS[words_key]
    result = benchmark(theqrmodule.get_qrcode, version, ecl, words, str(tmp_path))
    ver, qr_path = result
    assert ver >= version
    assert qr_path.endswith(".png")
