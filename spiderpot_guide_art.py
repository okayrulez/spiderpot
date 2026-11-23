"""Local artwork for the walkthrough. Only the selected wallpaper is read."""
from PIL import Image, ImageDraw, ImageOps

from spiderpot_support import resource


def rounded(size, radius, fill, outline=None):
    image = Image.new("RGBA", size)
    ImageDraw.Draw(image).rounded_rectangle((0, 0, size[0]-1, size[1]-1), radius,
                                            fill=fill, outline=outline, width=2)
    return image


def fitted(path, size):
    with Image.open(path) as source:
        return ImageOps.fit(ImageOps.exif_transpose(source).convert("RGB"), size,
                            Image.Resampling.LANCZOS)


def guide_scene(scene, size, slide_paths):
    w, h = 1140, 300
    try:
        with Image.open(resource("Assets/spider_noir.jpg")) as source:
            portrait = ImageOps.fit(source.convert("RGB"), (590, h), centering=(.5, .12))
        backdrop = Image.new("RGB", (w, h), "#242330")
        feather = Image.linear_gradient("L").rotate(90).resize(portrait.size).point(lambda v: min(255, (255-v)*3))
        backdrop.paste(portrait, (0, 0), feather)
    except OSError:
        backdrop = Image.new("RGB", (w, h), "#262735")
    # Keep the Noir artwork visible on the left and give the mode preview a quiet backdrop.
    veil = Image.linear_gradient("L").rotate(90).resize((w, h)).point(lambda v: 65 + v*175//255)
    canvas = Image.composite(Image.new("RGB", (w, h), "#191723"), backdrop, veil)
    draw = ImageDraw.Draw(canvas)

    def screen(box, content, frame="#e6dfe3"):
        x, y, right, bottom = box
        draw.rounded_rectangle((x+5, y+7, right+5, bottom+7), 13, fill="#14121b")
        draw.rounded_rectangle(box, 13, fill=frame)
        inner = (right-x-12, bottom-y-12)
        panel = ImageOps.fit(content, inner, Image.Resampling.LANCZOS)
        canvas.paste(panel, (x+6, y+6), rounded(inner, 8, "white").getchannel("A"))

    if scene in ("spider", "check"):
        for i, path in enumerate(slide_paths[:3][::-1]):
            try:
                photo = fitted(path, (450, 236))
            except (ValueError, OSError):
                continue
            offset = (min(len(slide_paths), 3)-1-i)*14
            screen((594+offset, 34-offset//2, 1018+offset, 266-offset//2), photo)
    elif scene in ("black", "invisible"):
        panel = Image.new("RGB", (420, 225), "#08090c")
        if scene == "invisible":
            painter = ImageDraw.Draw(panel)
            painter.rectangle((0, 0, 420, 225), fill="#8895b5")
            for x, y, color in ((45, 24, "#cccadc"), (116, 56, "#f7f5f4")):
                painter.rounded_rectangle((x, y, x+228, y+126), 9, fill=color, outline="#67687b")
                painter.line((x+1, y+23, x+225, y+23), fill="#9e9bab", width=2)
                for n in range(3):
                    painter.ellipse((x+10+n*10, y+9, x+14+n*10, y+13), fill="#7e798b")
            painter.rounded_rectangle((135, 204, 285, 216), 6, fill="#e1e1eb")
        screen((594, 34, 1018, 266), panel)
    elif scene == "camera":
        draw.rounded_rectangle((669, 67, 933, 239), 27, fill="#e9dfe1")
        draw.rounded_rectangle((708, 49, 783, 98), 14, fill="#e9dfe1")
        draw.ellipse((742, 79, 894, 231), fill="#343246")
        draw.ellipse((760, 97, 876, 213), fill="#9089a5")
        draw.ellipse((775, 112, 861, 198), fill="#282737")
        draw.ellipse((790, 127, 812, 149), fill="#e7dfed")
        draw.ellipse((691, 92, 705, 106), fill="#b82e4b")
    else:
        draw.rounded_rectangle((647, 72, 758, 137), 15, fill="#e3b5a5")
        draw.rounded_rectangle((647, 99, 949, 239), 16, fill="#bb876f")
        draw.rounded_rectangle((682, 73, 918, 205), 9, fill="#f9f3ed")
        draw.rounded_rectangle((697, 56, 898, 181), 8, fill="#ccbbc8", outline="#fcf7f4", width=6)
        draw.rounded_rectangle((641, 130, 955, 248), 16, fill="#e8b79e")
    result = canvas.convert("RGBA")
    result.putalpha(rounded((w, h), 25, "white").getchannel("A"))
    return result.resize(size, Image.Resampling.LANCZOS)
