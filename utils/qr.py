"""generate and decode QR codes.

Requirements:
- pip install qrcode[pil] pyzbar
"""
import os
from pathlib import Path
from typing import Optional
from PIL import Image

import qrcode
from pyzbar.pyzbar import decode as zbar_decode

def generate_qr(
    data: str,
    path: str,
    box_size: int = 10,
    border: int = 4,
    fill_color: str = "black",
    back_color: str = "white",
) -> None:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=box_size, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill_color, back_color=back_color)

    out_dir = os.path.dirname(os.path.abspath(path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    img.save(path)


def decode_qr(path: str) -> Optional[str]:
    img = Image.open(path)
    decoded = zbar_decode(img)
    if not decoded:
        return None
    return decoded[0].data.decode("utf-8")


__all__ = ["generate_qr", "decode_qr"]
