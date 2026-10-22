"""Turn the generated island models into the site's archipelago.

Every model goes through Blender once (metres, waterline, texture size, heightmap,
compression) into site/assets/isles/, and the arrangement measured off the
painting becomes site/archipelago.js: the six islands the page's chapters stop at,
and every other island and rock where the painting has it.

Run: python build_islands.py [--skip-blender]
"""
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.normpath(os.path.join(HERE, "..", "site"))
OUT = os.path.join(SITE, "assets", "isles")
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"

# the page's camera works best with the archipelago near the origin; the painting's
# own camera then stands at (0, OFFSET) looking down -Z
OFFSET_Z = 300.0
DEPTH = 0.75          # half-depth of an island as a share of its half-width

RAW = {
    "isle_01": "raw/isle_01_solid_p1.glb",
    "isle_12": "raw/isle_12_p1.glb",
    "isle_05": "raw/isle_05_p2.glb",   # P1 came out crude on the harbour town; P2 kept the quay
    "rock_a": "raw/rock_a.glb",
}
KEEP = {"isle_11": 0.55}            # its crop carried the palm strip that is isle_07
# metres, world frame: where the painting's depth estimate lets two islands overlap
NUDGE = {"isle_14": [22.0, 30.0]}
ROCK_MODELS = [("rock_a", 10.0), ("isle_17", None)]
FAR_POOL = ["isle_09", "isle_10", "isle_12", "isle_13", "isle_14", "isle_18"]

# the chapters of the page, in reading order, and the island each one stops at
CHAPTERS = [
    ("landing", "isle_01", {"ru": "Берег", "en": "The Shore"}, {}),
    ("combat", "isle_04", {"ru": "Бой", "en": "The Fight"}, {"arena": True, "arenaOffset": [19.4, -1.6], "arenaRadius": 16}),
    ("skills", "isle_03", {"ru": "Навыки", "en": "Skills"}, {}),
    ("storm", "volcano", {"ru": "Шторм", "en": "The Storm"}, {"storm": True, "view": 1.6}),
    ("forge", "isle_05", {"ru": "Кузня", "en": "The Forge"}, {}),
    ("devlog", "isle_02", {"ru": "Верфь", "en": "The Yard"}, {}),
]


def prepare(model_id, src, radius, tex, keep=1.0):
    args = [BLENDER, "-b", "-P", os.path.join(HERE, "prepare_island.py"), "--",
            os.path.join(HERE, src), OUT, model_id, "%.3f" % radius, "0.05",
            str(tex), "0", "%.3f" % keep]
    res = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in res.stdout.splitlines():
        if line.startswith("PREPARED "):
            return json.loads(line[len("PREPARED "):])
    sys.stderr.write(res.stdout[-3000:] + res.stderr[-2000:])
    raise SystemExit("prepare failed for " + model_id)


def yaw_toward_camera(x, z):
    # the models' front faces +X; turn it toward the painting's camera
    dx, dz = 0.0 - x, OFFSET_Z - z
    return math.atan2(-dz, dx)


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    skip = "--skip-blender" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    layout = json.load(open(os.path.join(HERE, "islands_layout.json"), encoding="utf-8"))
    places = layout["islands"]

    manifest_path = os.path.join(OUT, "manifest.json")
    entries = {}
    if skip and os.path.exists(manifest_path):
        entries = {e["id"]: e for e in json.load(open(manifest_path, encoding="utf-8"))["islands"]}

    for p in places:
        if p["kind"] != "island" or (skip and p["id"] in entries):
            continue
        src = RAW.get(p["id"], "raw/%s_p1.glb" % p["id"])
        tex = 1024 if p["radius"] >= 30 else 512
        entries[p["id"]] = prepare(p["id"], src, p["radius"], tex, KEEP.get(p["id"], 1.0))
        print("prepared", p["id"], entries[p["id"]]["triangles"], "tris")
    if not (skip and "rock_a" in entries):
        entries["rock_a"] = prepare("rock_a", RAW["rock_a"], 10.0, 512)

    json.dump({
        "note": "Generated islands for the Skillstorm site. Metres, Y up, origin at the island "
                "centre, y=0 the waterline, front facing +X. <id>_height.png: 256x256 16-bit "
                "heightmap over the island's bounding square; column runs along +X, row along +Z.",
        "islands": list(entries.values()),
    }, open(manifest_path, "w", encoding="utf-8"), indent=1)

    chapter_of = {isle: (cid, name, extra) for cid, isle, name, extra in CHAPTERS}
    chapters, others = {}, []
    rock_i = 0
    far_i = 0
    for p in places:
        # The painting is measured at each island's near waterline, which is its
        # front edge, not its middle; the model's centre lies half a depth further
        # along the line of sight.
        px, pz = p["pos"]
        d = math.hypot(px, pz) or 1.0
        push = p["radius"] * DEPTH
        x, z = px + px / d * push, pz + pz / d * push + OFFSET_Z
        nx, nz = NUDGE.get(p["id"], (0.0, 0.0))
        x, z = x + nx, z + nz
        spec = {"pos": [round(x, 2), round(z, 2)], "radius": p["radius"],
                "yaw": round(yaw_toward_camera(x, z), 4)}
        if p["kind"] == "island":
            spec["model"] = p["id"]
            spec["scale"] = 1
        elif p["kind"] == "far":
            # a far island is a few pixels in the painting: one of the small generated
            # islands, turned and sized so no two neighbours look alike
            far_i += 1
            pool = FAR_POOL if p["radius"] >= 12 else [m for m, _ in ROCK_MODELS]
            model = pool[(far_i * 7) % len(pool)]
            spec["model"] = model
            spec["scale"] = round(p["radius"] / entries[model]["radius"], 4)
            spec["yaw"] = round(spec["yaw"] + far_i * 2.3, 4)
        else:
            model, mr = ROCK_MODELS[rock_i % len(ROCK_MODELS)]
            rock_i += 1
            mr = mr or entries[model]["radius"]
            spec["model"] = model
            spec["scale"] = round(p["radius"] / mr, 4)
            spec["yaw"] = round(spec["yaw"] + rock_i * 1.7, 4)   # no two rocks alike
        if p["id"] in chapter_of:
            cid, name, extra = chapter_of[p["id"]]
            extra = dict(extra)
            off = extra.pop("arenaOffset", None)
            if off:
                # measured on the island's heightmap: the flattest dry circle
                extra["arenaPos"] = [round(spec["pos"][0] + off[0], 2), round(spec["pos"][1] + off[1], 2)]
            chapters[cid] = dict({"id": cid, "name": name}, **spec, **extra)
        else:
            others.append(dict({"id": p["id"]}, **spec))

    lines = [
        "/* The archipelago, in one place: the site's route, its chapters and its map legend",
        "   all read from this. Generated by tools_tripo/build_islands.py from the layout",
        "   measured off the start-screen painting; positions are metres on the sea plane,",
        "   x east, z south. `model` names the mesh in assets/isles, `yaw` turns its front",
        "   toward the painting's camera, `scale` resizes a shared rock. */",
        "",
        "export const PAINTING_CAMERA = %s;" % js({
            "pos": [0, layout["camera"]["height"], OFFSET_Z],
            "pitchDeg": layout["camera"]["pitch_deg"], "fovY": layout["camera"]["fov_y"]}),
        "",
        "export const ISLANDS = [",
    ]
    for cid, _, _, _ in CHAPTERS:
        lines.append("  %s," % js(chapters[cid]))
    lines += ["];", "", "/* Every other island and rock of the painting, in its place. */",
              "export const ISLETS = ["]
    for o in others:
        lines.append("  %s," % js(o))
    lines += ["];", ""]
    open(os.path.join(SITE, "archipelago.js"), "w", encoding="utf-8").write("\n".join(lines))
    total = sum(os.path.getsize(os.path.join(OUT, e["mesh"])) for e in entries.values())
    print("wrote archipelago.js: %d chapters, %d others; meshes %.1f MB"
          % (len(chapters), len(others), total / 1e6))


if __name__ == "__main__":
    main()
