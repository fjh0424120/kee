#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile

from PIL import Image, ImageChops, ImageDraw

from amzqr.mylibs import theqrmodule


def _build_combine_mask(data_w, data_h, ver):
    """Return an "L" (data_w x data_h) paste mask: 255 = draw bg, 0 = keep QR.

    Covers only the geometric reserved regions (finders, timing, alignment,
    sampling holes); the background-transparency term is applied by the
    caller via ImageChops.multiply.  Reads layout constants from
    amzqr.mylibs.constant.
    """
    from amzqr.mylibs.constant import (
        FINDER_REGION_PX,
        TIMING_MODULE,
        alig_location,
    )
    from amzqr.mylibs.constant import (
        PIXELS_PER_MODULE as ppm,
    )

    mask = Image.new("L", (data_w, data_h), 255)
    draw = ImageDraw.Draw(mask)

    # (2)(3)(4) finder + separator: three FINDER_REGION_PX corners.
    fr = FINDER_REGION_PX
    draw.rectangle([0, 0, fr - 1, fr - 1], fill=0)  # top-left
    draw.rectangle([0, data_h - fr, fr - 1, data_h - 1], fill=0)  # bottom-left
    draw.rectangle([data_w - fr, 0, data_w - 1, fr - 1], fill=0)  # top-right

    # (1) timing pattern: module-6 row and column (PPM px wide).
    t0 = TIMING_MODULE * ppm
    t1 = (TIMING_MODULE + 1) * ppm - 1
    draw.rectangle([t0, 0, t1, data_h - 1], fill=0)  # column
    draw.rectangle([0, t0, data_w - 1, t1], fill=0)  # row

    # (5) alignment patterns (ver > 1): 5x5-module blocks around each
    # non-finder-adjacent centre.
    if ver > 1:
        aloc = alig_location[ver - 2]
        L = len(aloc)
        for a in range(L):
            for b in range(L):
                if (a == b == 0) or (a == L - 1 and b == 0) or (a == 0 and b == L - 1):
                    continue
                x0, x1 = ppm * (aloc[a] - 2), ppm * (aloc[a] + 3) - 1
                y0, y1 = ppm * (aloc[b] - 2), ppm * (aloc[b] + 3) - 1
                draw.rectangle([x0, y0, x1, y1], fill=0)

    # (6) sampling holes: the exact centre sub-pixel of every module (i%PPM ==
    # PPM//2 AND j%PPM == PPM//2) -> keep QR. One point() call for all centres.
    centre = ppm // 2
    pts = [(x, y) for x in range(centre, data_w, ppm) for y in range(centre, data_h, ppm)]
    draw.point(pts, fill=0)

    return mask


# Positional parameters
#   words: str
#
# Optional parameters
#   version: int, from 1 to 40
#   level: str, just one of ('L','M','Q','H')
#   picutre: str, a filename of a image
#   colorized: bool
#   contrast: float
#   brightness: float
#   save_name: str, the output filename like 'example.png'
#   save_dir: str, the output directory
#
# See [https://github.com/x-hw/amazing-qr] for more details!
def run(
    words,
    version=1,
    level="H",
    picture=None,
    colorized=False,
    contrast=1.0,
    brightness=1.0,
    save_name=None,
    save_dir=os.getcwd(),
):

    supported_chars = r"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ··,.:;+-*/\~!@#$%^&`'=<>[]()?_{}|"

    # check every parameter
    if not isinstance(words, str) or any(i not in supported_chars for i in words):
        raise ValueError("Wrong words! Make sure the characters are supported!")
    if not isinstance(version, int) or version not in range(1, 41):
        raise ValueError("Wrong version! Please choose a int-type value from 1 to 40!")
    if not isinstance(level, str) or len(level) > 1 or level not in "LMQH":
        raise ValueError("Wrong level! Please choose a str-type level from {'L','M','Q','H'}!")
    if picture:
        if (
            not isinstance(picture, str)
            or not os.path.isfile(picture)
            or os.path.splitext(picture)[1].lower() not in (".jpg", ".jpeg", ".png", ".bmp", ".gif")
        ):
            raise ValueError(
                "Wrong picture! Input a filename that exists and be tailed with one of {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}!"
            )
        if (
            os.path.splitext(picture)[1].lower() == ".gif"
            and save_name
            and os.path.splitext(save_name)[1].lower() != ".gif"
        ):
            raise ValueError(
                "Wrong save_name! If the picuter is .gif format, the output filename should be .gif format, too!"
            )
        if not isinstance(colorized, bool):
            raise ValueError("Wrong colorized! Input a bool-type value!")
        if not isinstance(contrast, float):
            raise ValueError("Wrong contrast! Input a float-type value!")
        if not isinstance(brightness, float):
            raise ValueError("Wrong brightness! Input a float-type value!")
    if save_name and (
        not isinstance(save_name, str)
        or os.path.splitext(save_name)[1].lower() not in (".jpg", ".jpeg", ".png", ".bmp", ".gif")
    ):
        raise ValueError(
            "Wrong save_name! Input a filename tailed with one of {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}!"
        )
    if not os.path.isdir(save_dir):
        raise ValueError("Wrong save_dir! Input a existing-directory!")

    def combine(ver, qr_name, bg_name, colorized, contrast, brightness, save_dir, save_name=None):
        from PIL import ImageEnhance

        from amzqr.mylibs.constant import DATA_OFFSET_PX, PASTE_OFFSET_PX

        qr = Image.open(qr_name)
        qr = qr.convert("RGBA") if colorized else qr

        bg0 = Image.open(bg_name).convert("RGBA")
        bg0 = ImageEnhance.Contrast(bg0).enhance(contrast)
        bg0 = ImageEnhance.Brightness(bg0).enhance(brightness)

        data_w = qr.size[0] - DATA_OFFSET_PX
        data_h = qr.size[1] - DATA_OFFSET_PX

        # Scale bg to cover the data area, preserving aspect ratio, then
        # center-crop to exactly data_w × data_h.
        if bg0.size[0] < bg0.size[1]:
            # Portrait: fit width to data_w, scale height proportionally
            new_w = data_w
            new_h = int(bg0.size[1] * (new_w / bg0.size[0]))
        else:
            # Landscape or square: fit height to data_h, scale width proportionally
            new_h = data_h
            new_w = int(bg0.size[0] * (new_h / bg0.size[1]))

        bg0 = bg0.resize((new_w, new_h))
        left = (new_w - data_w) // 2
        top = (new_h - data_h) // 2
        bg0 = bg0.crop((left, top, left + data_w, top + data_h))

        bg = bg0 if colorized else bg0.convert("1")

        # Composite via a reserved-region mask + one C-accelerated paste,
        # replacing the former per-pixel putpixel loop (fast for large versions).
        mask = _build_combine_mask(data_w, data_h, ver)
        # Threshold bg alpha to binary (0/255) so paste hard-replaces, matching
        # the former putpixel which drew semi-transparent bg pixels at full
        # strength instead of alpha-blending them.
        mask = ImageChops.multiply(mask, bg0.getchannel("A").point(lambda v: 255 if v else 0))
        qr.paste(bg, (PASTE_OFFSET_PX, PASTE_OFFSET_PX), mask)

        qr_name = (
            os.path.join(save_dir, os.path.splitext(os.path.basename(bg_name))[0] + "_qrcode.png")
            if not save_name
            else os.path.join(save_dir, save_name)
        )
        qr.resize((qr.size[0] * 3, qr.size[1] * 3)).save(qr_name)
        return qr_name

    with tempfile.TemporaryDirectory() as tempdir:
        ver, qr_name = theqrmodule.get_qrcode(version, level, words, tempdir)

        if picture and os.path.splitext(picture)[1].lower() == ".gif":
            im = Image.open(picture)
            durations = []
            im.save(os.path.join(tempdir, "0.png"))
            durations.append(im.info.get("duration", 0))
            while True:
                try:
                    seq = im.tell()
                    im.seek(seq + 1)
                    im.save(os.path.join(tempdir, "%s.png" % (seq + 1)))
                    durations.append(im.info.get("duration", 0))
                except EOFError:
                    break

            imsname = []
            for s in range(seq + 1):
                bg_name = os.path.join(tempdir, "%s.png" % s)
                imsname.append(
                    combine(ver, qr_name, bg_name, colorized, contrast, brightness, tempdir)
                )

            qr_name = (
                os.path.join(
                    save_dir, os.path.splitext(os.path.basename(picture))[0] + "_qrcode.gif"
                )
                if not save_name
                else os.path.join(save_dir, save_name)
            )
            frames = [Image.open(pic) for pic in imsname]
            frames[0].save(
                qr_name,
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=0,
            )
        elif picture:
            qr_name = combine(
                ver, qr_name, picture, colorized, contrast, brightness, save_dir, save_name
            )
        elif qr_name:
            qr = Image.open(qr_name)
            qr_name = (
                os.path.join(save_dir, os.path.basename(qr_name))
                if not save_name
                else os.path.join(save_dir, save_name)
            )
            qr.resize((qr.size[0] * 3, qr.size[1] * 3)).save(qr_name)

        return ver, level, qr_name
