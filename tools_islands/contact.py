"""Compose the island renders into one contact sheet for review."""
import os
import sys

import numpy as np
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "renders")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
names = argv[0].split(",") if argv else [
    'landing', 'combat', 'skills', 'storm', 'forge', 'devlog',
    'islet_01', 'islet_02', 'islet_03', 'islet_04', 'islet_05', 'islet_06',
    'islet_07', 'islet_08']
cols = int(argv[1]) if len(argv) > 1 else 3
scale = float(argv[2]) if len(argv) > 2 else 0.42
out_name = argv[3] if len(argv) > 3 else "_sheet.png"

tiles = []
tw = th = 0
for n in names:
    p = os.path.join(SHOTS, n + ".png")
    if not os.path.exists(p):
        continue
    img = bpy.data.images.load(p)
    w, h = img.size
    px = np.array(img.pixels[:]).reshape(h, w, 4)
    sw, sh = int(w * scale), int(h * scale)
    yi = (np.arange(sh) * (h / sh)).astype(int)
    xi = (np.arange(sw) * (w / sw)).astype(int)
    tiles.append(px[yi][:, xi])
    tw, th = sw, sh
    bpy.data.images.remove(img)

rows = (len(tiles) + cols - 1) // cols
sheet = np.zeros((rows * th, cols * tw, 4))
sheet[..., 3] = 1.0
for i, t in enumerate(tiles):
    r, c = divmod(i, cols)
    r = rows - 1 - r  # bottom-up pixel order
    sheet[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = t

out = bpy.data.images.new("sheet", cols * tw, rows * th, alpha=True)
out.pixels = sheet.ravel()
out.filepath_raw = os.path.join(SHOTS, out_name)
out.file_format = 'PNG'
out.save()
print("[sheet]", out.filepath_raw, cols * tw, rows * th)
