from PIL import Image, ImageDraw

def create_ui_assets():
    # 1. Checkmark icon (32x32)
    img_check = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d_check = ImageDraw.Draw(img_check)
    # Draw dark checkmark on transparent background
    d_check.line([(12, 34), (26, 48), (52, 16)], fill=(12, 18, 30, 255), width=8, joint="curve")
    img_check = img_check.resize((24, 24), Image.Resampling.LANCZOS)
    img_check.save("icon_check.png", "PNG")

    # 2. Chevron down icon (32x32)
    img_chev = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d_chev = ImageDraw.Draw(img_chev)
    d_chev.line([(14, 22), (32, 42), (50, 22)], fill=(255, 145, 0, 255), width=7, joint="curve")
    img_chev = img_chev.resize((20, 20), Image.Resampling.LANCZOS)
    img_chev.save("icon_chevron.png", "PNG")

    print("UI asset icons created!")

if __name__ == "__main__":
    create_ui_assets()
