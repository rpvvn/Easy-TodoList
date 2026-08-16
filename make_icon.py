# -*- coding: utf-8 -*-
"""生成 MaterialTodo.exe 的 app.ico 图标（纯 Pillow，无需 Qt）。"""

from PIL import Image, ImageDraw


def build_master(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = size * 0.055
    radius = size * 0.235

    # 圆角渐变底（从上到下由亮蓝渐变到靛蓝）
    top = (114, 141, 255, 255)
    bottom = (76, 100, 232, 255)
    box = [margin, margin, size - margin, size - margin]
    for y in range(int(box[1]), int(box[3])):
        t = (y - box[1]) / max(1, (box[3] - box[1]))
        t = max(0.0, min(1.0, t))
        r = max(0, min(255, round(top[0] + (bottom[0] - top[0]) * t)))
        g = max(0, min(255, round(top[1] + (bottom[1] - top[1]) * t)))
        b = max(0, min(255, round(top[2] + (bottom[2] - top[2]) * t)))
        draw.line([(box[0], y), (box[2], y)], fill=(r, g, b, 255), width=1)

    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(box, radius=radius, fill=255)
    img.putalpha(mask)

    # 白色圆头对勾
    draw = ImageDraw.Draw(img)
    width = max(3, round(size * 0.075))
    draw.line(
        [(size * 0.275, size * 0.525), (size * 0.435, size * 0.685), (size * 0.735, size * 0.325)],
        fill=(255, 255, 255, 255),
        width=width,
        joint="curve",
    )
    return img


def main():
    master = build_master(256)
    master.save(
        "app.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("app.ico generated.")


if __name__ == "__main__":
    main()
