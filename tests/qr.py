from utils.qr import generate_qr, decode_qr

def test_qr():
    generate_qr("Hello, World!", "tests/hello.png")
    assert decode_qr("tests/hello.png") == "Hello, World!"

if __name__ == "__main__":
    test_qr()
    print("QR code tests passed!")