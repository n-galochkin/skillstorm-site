"""Export the meshes and animations the web scene needs into .glb.

Headless:
  UnrealEditor-Cmd.exe Skillstorm.uproject -run=pythonscript -script="<this file>"

Writes into <this file's folder>/site/assets/models/.
"""
import os
import unreal

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site", "assets", "models")
os.makedirs(OUT, exist_ok=True)

# (asset path, output name)
STATIC = [
    ("/Game/PPFantasyWeapons/Meshes/Sword_1H/SM_PP_T01_Beginner_Sword_1H_001", "sword"),
    ("/Game/Environment/Meshes/Crops/SM_Tree_01", "tree_01"),
    ("/Game/Environment/Meshes/Crops/SM_Tree_02", "tree_02"),
    ("/Game/Environment/Meshes/Crops/SM_Stone_01", "stone_01"),
    ("/Game/Environment/Meshes/Crops/SM_Stone_02", "stone_02"),
    ("/Game/Environment/Meshes/Foliage/SM_GrassClump_01", "grass_01"),
    ("/Game/Environment/Meshes/Foliage/SM_GrassClump_03", "grass_03"),
    ("/Game/Environment/Meshes/Building/SM_House_01", "house_01"),
    ("/Game/Environment/Meshes/Building/SM_Monument_01", "monument_01"),
]

SKELETAL = [
    ("/Game/Characters/Meshes/SKM_Villager", "villager"),
]

# Animations export without a mesh (59 KB instead of 735 KB); three.js binds the clip
# to villager.glb's skeleton by bone name.
ANIMS = [
    ("/Game/Characters/Animations/A_Idle", "anim_idle"),
    ("/Game/Characters/Animations/A_Walk", "anim_walk"),
    ("/Game/Skillstorm/Characters/Animations/KayKit/A_KK_1H_Attack_Slice_Horizontal", "anim_attack"),
    ("/Game/Skillstorm/Characters/Animations/KayKit/A_KK_1H_Aiming", "anim_aim"),
]


def log(msg):
    unreal.log_warning("[gltf] {}".format(msg))


_dumped = [False]


def enum_value(enum_name, *candidates):
    """Pick the first enum member that exists, logging the real names once."""
    enum_type = getattr(unreal, enum_name, None)
    if enum_type is None:
        return None
    names = [n for n in dir(enum_type) if n.isupper()]
    if not _dumped[0]:
        log("{}: {}".format(enum_name, ", ".join(names)))
    for c in candidates:
        if hasattr(enum_type, c):
            return getattr(enum_type, c)
    return None


def make_options(preview_mesh):
    opts = unreal.GLTFExportOptions()
    tries = [
        ("export_uniform_scale", lambda: 0.01),          # Unreal cm -> glTF metres
        ("export_preview_mesh", lambda: preview_mesh),
        ("export_vertex_colors", lambda: True),
        ("export_vertex_skin_weights", lambda: True),
        ("bake_material_inputs", lambda: enum_value("GLTFMaterialBakeMode", "USE_MESH_DATA", "SIMPLE")),
        ("default_material_bake_size", lambda: enum_value(
            "GLTFMaterialBakeSize", "POT_1024", "POT1024", "POT_512", "POT512")),
        ("texture_image_format", lambda: enum_value("GLTFTextureImageFormat", "PNG")),
        ("export_texture_transforms", lambda: True),
    ]
    for key, make in tries:
        try:
            value = make()
            if value is None:
                log("option {}: no matching enum member, left at default".format(key))
                continue
            opts.set_editor_property(key, value)
        except Exception as exc:
            log("option {} not set: {}".format(key, exc))
    _dumped[0] = True
    return opts


def export(asset_path, name, preview_mesh=False):
    asset = unreal.load_asset(asset_path)
    if asset is None:
        log("MISSING {}".format(asset_path))
        return False
    target = os.path.join(OUT, name + ".glb")
    opts = make_options(preview_mesh)
    try:
        ok = unreal.GLTFExporter.export_to_gltf(asset, target, opts, set())
    except Exception as exc:
        log("FAILED {} -> {}".format(asset_path, exc))
        return False
    size = os.path.getsize(target) // 1024 if os.path.exists(target) else 0
    log("{} {} -> {} ({} KB)".format("OK  " if ok else "FAIL", asset_path, name + ".glb", size))
    return bool(ok)


def main():
    log("output: {}".format(OUT))
    done = 0
    total = 0
    for path, name in STATIC + SKELETAL:
        total += 1
        done += export(path, name, preview_mesh=False)
    for path, name in ANIMS:
        total += 1
        done += export(path, name, preview_mesh=False)
    log("exported {}/{}".format(done, total))
    for f in sorted(os.listdir(OUT)):
        log("  {} {} KB".format(f, os.path.getsize(os.path.join(OUT, f)) // 1024))


main()
