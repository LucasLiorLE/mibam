from utils.qr import generate_qr, decode_qr

generate_qr("t", "tests/t.png")

print(decode_qr("tests/t.png"))