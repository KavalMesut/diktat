import math
from PIL import Image, ImageDraw, ImageFilter

def create_diktat_icon():
    # 2x supersampling for ultra-crisp antialiasing
    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Outer Squircle / Rounded Rectangle
    # Padding
    pad = 70
    x0, y0, x1, y1 = pad, pad, size - pad, size - pad
    radius = 210

    # Draw gradient on a separate layer inside the rounded rect
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=255)

    # Create gradient layer from #FF9100 (255, 145, 0) to #DF301C (223, 48, 28)
    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(gradient)
    
    c_start = (255, 155, 20)  # Vibrant orange top-left
    c_end = (223, 48, 28)     # Deep crimson-orange bottom-right
    
    for y in range(size):
        ratio_y = y / size
        for x in range(size):
            ratio_x = x / size
            t = (ratio_x * 0.4 + ratio_y * 0.6)
            r = int(c_start[0] + (c_end[0] - c_start[0]) * t)
            g = int(c_start[1] + (c_end[1] - c_start[1]) * t)
            b = int(c_start[2] + (c_end[2] - c_start[2]) * t)
            gradient.putpixel((x, y), (r, g, b, 255))

    # Apply mask to gradient
    squircle = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    squircle.paste(gradient, (0, 0), mask)

    # Subtle inner top-edge highlight
    highlight_mask = Image.new("L", (size, size), 0)
    h_draw = ImageDraw.Draw(highlight_mask)
    h_draw.rounded_rectangle([x0 + 8, y0 + 8, x1 - 8, y1 - 8], radius=radius - 8, outline=255, width=14)
    # Blend highlight softly
    highlight_layer = Image.new("RGBA", (size, size), (255, 255, 255, 70))
    squircle.paste(highlight_layer, (0, 0), highlight_mask)

    # Composite base squircle onto canvas
    img = Image.alpha_composite(img, squircle)
    draw = ImageDraw.Draw(img)

    # 2. Draw Microphone Emblem in #FFF1D1 (255, 241, 209)
    cream = (255, 241, 209, 255)
    cream_glow = (255, 241, 209, 60)
    cyan_accent = (0, 183, 205, 240)

    center_x = size // 2
    center_y = size // 2 - 20

    # Microphone Capsule
    capsule_w = 110
    capsule_h = 240
    cap_x0 = center_x - capsule_w // 2
    cap_y0 = center_y - 120
    cap_x1 = center_x + capsule_w // 2
    cap_y1 = cap_y0 + capsule_h

    # Capsule main body
    draw.rounded_rectangle([cap_x0, cap_y0, cap_x1, cap_y1], radius=capsule_w // 2, fill=cream)

    # Capsule subtle decorative mic grill slot
    grill_w = 40
    grill_y = cap_y0 + 75
    draw.line([center_x - grill_w, grill_y, center_x + grill_w, grill_y], fill=(223, 80, 40, 200), width=6)
    draw.line([center_x - grill_w + 10, grill_y + 24, center_x + grill_w - 10, grill_y + 24], fill=(223, 80, 40, 200), width=6)

    # Microphone U-shaped cradle / arc
    arc_pad = 38
    arc_x0 = cap_x0 - arc_pad
    arc_y0 = cap_y0 + 50
    arc_x1 = cap_x1 + arc_pad
    arc_y1 = cap_y1 + arc_pad + 20

    draw.arc([arc_x0, arc_y0, arc_x1, arc_y1], start=0, end=180, fill=cream, width=28)

    # Mic Stand Stem
    stem_top = arc_y1 - 10
    stem_bottom = stem_top + 80
    draw.line([center_x, stem_top, center_x, stem_bottom], fill=cream, width=28)

    # Mic Base
    base_w = 190
    base_h = 26
    base_y = stem_bottom - 2
    draw.rounded_rectangle(
        [center_x - base_w // 2, base_y, center_x + base_w // 2, base_y + base_h],
        radius=base_h // 2,
        fill=cream
    )

    # 3. Sound Wave Accents on sides (Left & Right waves in cyan & cream)
    # Left inner wave
    draw.arc([center_x - 300, center_y - 100, center_x - 170, center_y + 60], start=120, end=240, fill=cream, width=22)
    # Left outer wave
    draw.arc([center_x - 380, center_y - 160, center_x - 210, center_y + 120], start=125, end=235, fill=cyan_accent, width=18)

    # Right inner wave
    draw.arc([center_x + 170, center_y - 100, center_x + 300, center_y + 60], start=300, end=420, fill=cream, width=22)
    # Right outer wave
    draw.arc([center_x + 210, center_y - 160, center_x + 380, center_y + 120], start=305, end=415, fill=cyan_accent, width=18)

    # Downsample to 512x512 with LANCZOS for premium antialiasing
    final_512 = img.resize((512, 512), Image.Resampling.LANCZOS)
    
    # Save icon.png
    final_512.save("icon.png", "PNG")

    # Generate multi-size icon.ico
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    final_512.save("icon.ico", format="ICO", sizes=ico_sizes)
    print("icon.png and icon.ico created successfully!")

if __name__ == "__main__":
    create_diktat_icon()
