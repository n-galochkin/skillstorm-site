"""Prepare web-optimised assets for the Skillstorm site."""
from PIL import Image
from pathlib import Path
import subprocess

PROJ = Path(r"C:\Projects\SkillStorm")
HERE = Path(__file__).parent
OUT = HERE / "site" / "assets"
OUT.mkdir(parents=True, exist_ok=True)
CLIP = Path(r"C:\CloudStorage\Yandex.Disk\Video\Skillstorm Videos\Clips\3. Опубликовано\2026-10-15 anime-opening-full.mp4")


def save(img, name, width=None, quality=80, alpha=False):
    im = img.convert("RGBA" if alpha else "RGB")
    if width and im.width > width:
        h = round(im.height * width / im.width)
        im = im.resize((width, h), Image.LANCZOS)
    p = OUT / name
    im.save(p, "WEBP", quality=quality, method=6)
    print(f"{name:24} {im.width}x{im.height} {p.stat().st_size // 1024}KB")


# Key art + logo + cloud
save(Image.open(PROJ / "Content/Splash/Splash.png"), "keyart.webp", 1800, 82)
save(Image.open(PROJ / "Content/Splash/Splash.png"), "keyart-tiny.webp", 32, 60)
save(Image.open(PROJ / "Content/Slate/StartScreen/Logo.png"), "logo.webp", 900, 90, alpha=True)
save(Image.open(PROJ / "Content/Slate/StartScreen/TransitionCloud.png"), "cloud.webp", 760, 78, alpha=True)

# Real in-game screens (portrait captures)
hall = PROJ / "Saved/ArtReview/HallUI"
for src, dst in [
    ("choices-second-chance.png", "ui-levelup.webp"),
    ("map.png", "ui-map.webp"),
    ("forge.png", "ui-forge.webp"),
    ("equipment.png", "ui-equipment.webp"),
    ("mastery.png", "ui-mastery.webp"),
    ("region.png", "ui-region.webp"),
    ("defeat.png", "ui-defeat.webp"),
]:
    save(Image.open(hall / src), dst, 560, 80)

# Real gameplay stills from the published clip: crop away the burned-in caption
for t, dst in [("9.6", "gp-combat.webp"), ("12.5", "gp-storm.webp"), ("12.8", "gp-synergy.webp")]:
    raw = HERE / f"raw_{t}.png"
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-ss", t, "-i", str(CLIP), "-frames:v", "1", str(raw), "-y"],
        check=True,
    )
    im = Image.open(raw)
    im = im.crop((0, 0, im.width, int(im.height * 0.55)))  # caption starts below this
    save(im, dst, 900, 82)
    raw.unlink()

# Compressed loop of the published clip + poster
subprocess.run([
    "ffmpeg", "-nostdin", "-v", "error", "-i", str(CLIP),
    "-vf", "scale=540:-2", "-c:v", "libx264", "-crf", "30", "-preset", "slow",
    "-profile:v", "main", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
    str(OUT / "devlog-clip.mp4"), "-y",
], check=True)
print("devlog-clip.mp4", (OUT / "devlog-clip.mp4").stat().st_size // 1024, "KB")

raw = HERE / "poster.png"
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", "2.0", "-i", str(CLIP),
                "-frames:v", "1", str(raw), "-y"], check=True)
save(Image.open(raw), "devlog-poster.webp", 540, 78)
raw.unlink()

total = sum(p.stat().st_size for p in OUT.iterdir())
print(f"TOTAL {total // 1024} KB in {OUT}")
