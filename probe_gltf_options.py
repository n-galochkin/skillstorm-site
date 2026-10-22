"""Probe: what GLTFExportOptions offers, and how big an animation is without its mesh."""
import os
import unreal

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site", "assets", "models", "_probe")
os.makedirs(OUT, exist_ok=True)


def log(m):
    unreal.log_warning("[probe] {}".format(m))


opts = unreal.GLTFExportOptions()
props = sorted(p for p in dir(opts) if not p.startswith("_"))
log("options: " + ", ".join(props))

anim = "/Game/Characters/Animations/A_Walk"
for preview in (True, False):
    o = unreal.GLTFExportOptions()
    o.set_editor_property("export_uniform_scale", 0.01)
    try:
        o.set_editor_property("export_preview_mesh", preview)
    except Exception as exc:
        log("preview flag failed: {}".format(exc))
    target = os.path.join(OUT, "walk_preview_{}.glb".format(int(preview)))
    try:
        ok = unreal.GLTFExporter.export_to_gltf(unreal.load_asset(anim), target, o, set())
        size = os.path.getsize(target) // 1024 if os.path.exists(target) else 0
        log("preview={} ok={} size={} KB".format(preview, ok, size))
    except Exception as exc:
        log("preview={} FAILED {}".format(preview, exc))
