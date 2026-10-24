from PIL import Image, ImageDraw, ImageFont


def generate(root):
    destination = root / ".artifacts" / "icons"
    destination.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 504, 504), radius=100, fill="#0b766c")
    font = ImageFont.truetype(str(root / "aipm_toolkit/assets/fonts/DejaVuSans-Bold.ttf"), 245)
    draw.text((256, 270), "AI", font=font, anchor="mm", fill="white")
    image.save(destination / "icon.png")
    image.save(destination / "icon.ico", sizes=[(size, size) for size in (16, 32, 48, 64, 128, 256)])
    image.save(destination / "icon.icns")
    return destination
