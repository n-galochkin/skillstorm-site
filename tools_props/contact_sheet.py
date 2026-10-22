"""Tile the per-model renders into a labelled contact sheet so a whole family can
be judged side by side against the reference. Plain CPython + Pillow."""
import os
import sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(ROOT, "renders")
CELL = 300
COLS = 4


def main():
    out = sys.argv[1]
    names = sys.argv[2:]
    rows = (len(names) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * CELL, rows * (CELL + 22)), (236, 238, 235))
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(names):
        p = os.path.join(R, n + ".png")
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB").resize((CELL, CELL), Image.LANCZOS)
        x = (i % COLS) * CELL
        y = (i // COLS) * (CELL + 22)
        sheet.paste(im, (x, y))
        d.rectangle([x, y + CELL, x + CELL, y + CELL + 22], fill=(28, 32, 34))
        d.text((x + 6, y + CELL + 5), n, fill=(240, 240, 235))
    dst = os.path.join(R, out + ".png")
    sheet.save(dst)
    print("SHEET", dst, sheet.size)


main()
