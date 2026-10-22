import bpy, inspect, sys
import numpy as np
print("BL", bpy.app.version_string, "numpy", np.__version__)
op = bpy.ops.export_scene.gltf
props = op.get_rna_type().properties
names = [p.identifier for p in props if p.identifier != 'rna_type']
want = [n for n in names if any(k in n for k in ('normal','color','material','format','draco','apply','selected','tangent','yup','image','attribute'))]
print("GLTF OPTS:", sorted(want))
for p in props:
    if p.identifier in ('export_vertex_color','export_all_vertex_colors','export_normals','export_draco_mesh_compression_enable','export_materials','export_image_format','export_tangents'):
        print("  ", p.identifier, getattr(p,'default',None), getattr(p,'enum_items',None) and [i.identifier for i in p.enum_items])
# addons / extensions available
try:
    import addon_utils
    mods = sorted(m.__name__ for m in addon_utils.modules())
    print("ADDONS with land/ant/terrain:", [m for m in mods if any(k in m.lower() for k in ('ant','land','terra'))])
except Exception as e:
    print("addon probe failed", e)
