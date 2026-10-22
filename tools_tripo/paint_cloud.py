"""Turn the game's photographic start-screen cumulus into a soft painted one that
sits with the stylised islands: smooth light from above, a lavender underside, the
big masses kept and the fine billow dissolved."""
import os, sys
import numpy as np
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import mask as M

SRC = r'C:/Projects/SkillStorm/Content/Slate/StartScreen/TransitionCloud.png'
DST = r'C:/Users/acter/Downloads/Skillstorm/web-demo/site/assets/cloud_bank.webp'

def blur(x, r):
    return np.asarray(Image.fromarray((np.clip(x, 0, 1) * 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255.0

im = Image.open(SRC).convert('RGBA').resize((384, 384), Image.LANCZOS)
a = np.asarray(im).astype(np.float32) / 255.0
al = a[..., 3]
lab, n = M.label(al > 0.08)
sizes = np.bincount(lab.ravel()); sizes[0] = 0
al = np.where(np.isin(lab, np.flatnonzero(sizes >= sizes.max() * 0.01)), al, 0.0)
L = (a[..., :3] * np.array([0.2126, 0.7152, 0.0722])).sum(-1)

ys = np.linspace(0, 1, al.shape[0])[:, None] * np.ones_like(al)
inside = al > 0.5
top, bot = ys[inside].min(), ys[inside].max()
vert = 1 - np.clip((ys - top) / (bot - top), 0, 1)          # 1 at the top, 0 underneath
lum = blur(L, 4.0)
lo, hi = np.percentile(lum[inside], [5, 95])
lum = np.clip((lum - lo) / (hi - lo), 0, 1)
t = np.clip(0.55 * vert + 0.45 * lum, 0, 1)
t = t * t * (3 - 2 * t)

shadow = np.array([0.70, 0.72, 0.86])
light = np.array([1.00, 0.965, 0.90])
rgb = shadow + (light - shadow) * t[..., None]
alpha = blur(al, 1.6)
alpha = np.clip((alpha - 0.1) / 0.75, 0, 1)
out = np.dstack([rgb, alpha])
img = Image.fromarray((out * 255).astype(np.uint8), 'RGBA').resize((512, 512), Image.LANCZOS)
img.save(DST, 'WEBP', quality=90, method=6)
prev = Image.new('RGB', (1024, 512), (24, 120, 170))
old = Image.open(SRC).convert('RGBA').resize((512, 512))
prev.paste(old, (0, 0), old); prev.paste(img, (512, 0), img)
prev.save(os.path.join(HERE, 'cloud_painted_preview.jpg'), quality=90)
print(os.path.getsize(DST))
