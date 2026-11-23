# Prometheus: the built-in character creators, the defaults and the look.
#   blender.exe -b --factory-startup --python tests/prometheus_humans_test.py
import os
import sys
import tempfile
import traceback

import addon_utils
import bpy
import numpy as np

fails = 0


def check(what, ok, detail=""):
    global fails
    print(("ok    " if ok else "FAIL  ") + what + (": " + str(detail) if detail != "" else ""))
    fails += 0 if ok else 1


def guarded(name, fn):
    try:
        fn()
    except Exception:
        check(name, False, traceback.format_exc().strip().splitlines()[-1])
        traceback.print_exc()


def objects_now():
    return set(bpy.data.objects)


# --- defaults --------------------------------------------------------------------
for mod in ("rigify", "charmorph", "mb_lab", "smplx_body", "pantomimus_link"):
    default, loaded = addon_utils.check(mod)
    check(f"{mod} on by default", loaded, f"default={default} loaded={loaded}")

ui = bpy.context.preferences.themes[0].user_interface
c = ui.wcol_tool.inner_sel
check("Atelier blue on selected tools", abs(c[0] - 0x00 / 255) < 0.02 and abs(c[1] - 0x7b / 255) < 0.02 and abs(c[2] - 0xb7 / 255) < 0.02,
      tuple(round(v, 3) for v in c))
check("square corners", ui.wcol_tool.roundness == 0.0, ui.wcol_tool.roundness)
check("no menu shadows", ui.menu_shadow_fac == 0.0, ui.menu_shadow_fac)
user = bpy.utils.resource_path('USER')
check("own settings folder", "Prometheus" in user and "Blender Foundation" not in user, user)


# --- MB-Lab ----------------------------------------------------------------------
def mb_lab():
    scn = bpy.context.scene
    import mb_lab   # its list is filled on demand (a dynamic enum), from the humanoid's types
    items = [i[0] for i in mb_lab.mblab_humanoid.humanoid_types]
    check("MB-Lab lists its characters", len(items) > 0, ", ".join(items[:4]))
    female = next((i for i in items if "female" in i.lower()), items[0])
    scn.mblab_character_name = female
    before = objects_now()
    r = bpy.ops.mbast.init_character()
    new = [o for o in objects_now() - before if o.type == 'MESH']
    check("MB-Lab makes a character", 'FINISHED' in r and new, f"{female}: {r}, meshes {[o.name for o in new]}")
    if new:
        check("MB-Lab body has its vertices", len(new[0].data.vertices) > 10000, len(new[0].data.vertices))


guarded("MB-Lab", mb_lab)


# --- CharMorph -------------------------------------------------------------------
def charmorph():
    bpy.ops.object.select_all(action='DESELECT') if bpy.context.mode == 'OBJECT' else None
    ui = bpy.context.window_manager.charmorph_ui
    from charmorph.lib import charlib
    names = list(charlib.library.chars.keys())
    check("CharMorph lists its characters", {"mb_female", "antonia", "reom"} <= set(names), ", ".join(names))
    for name in ("mb_female", "antonia"):
        ui.base_model = name
        before = objects_now()
        r = bpy.ops.charmorph.import_char()
        new = [o for o in objects_now() - before if o.type == 'MESH']
        check(f"CharMorph makes {name}", 'FINISHED' in r and new, f"{r}, meshes {[o.name for o in new]}")


guarded("CharMorph", charmorph)


# --- SMPL-X (a made-up model: the real ones can't be shipped) -----------------------
def smplx():
    d = tempfile.mkdtemp(prefix="smplx_test_")
    v = np.array([[0, 0, 0], [0, 1, 0], [0, 2, 0], [0.5, 1, 0]], float)
    sd = np.zeros((4, 3, 2))
    sd[:, 1, 0] = [0, 0.5, 1.0, 0.5]                # shape 0 makes it taller
    sd[3, 0, 1] = 0.2                                # "expression" 0 moves the side vertex
    jr = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]], float)
    w = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 1, 0]], float)
    kt = np.array([[-1, 0, 1], [0, 1, 2]])
    np.savez(os.path.join(d, "SMPLX_FEMALE.npz"), v_template=v, f=np.array([[0, 1, 3], [1, 2, 3]]),
             shapedirs=sd, J_regressor=jr, weights=w, kintree_table=kt)
    prefs = bpy.context.preferences.addons["smplx_body"].preferences
    prefs.model_folder = ""
    try:
        r = bpy.ops.smplx.add_body(gender='FEMALE')
        said = ""
    except RuntimeError as ex:      # in the background an operator's error report is raised
        r, said = {'CANCELLED'}, str(ex)
    check("SMPL-X without models says where to get them", r == {'CANCELLED'} and "smpl-x.is.tue.mpg.de" in said, said[:80])
    prefs.model_folder = d
    before = objects_now()
    r = bpy.ops.smplx.add_body(gender='FEMALE', shape_count=10, expression_count=10)
    new = objects_now() - before
    body = next((o for o in new if o.type == 'MESH'), None)
    rig = next((o for o in new if o.type == 'ARMATURE'), None)
    check("SMPL-X makes a body and a skeleton", 'FINISHED' in r and body and rig, r)
    if not body:
        return
    keys = [k.name for k in body.data.shape_keys.key_blocks]
    check("shape and expression sliders", "Shape 000" in keys and "Expression 000" in keys, keys)
    check("Y up becomes Z up", abs(body.data.vertices[2].co.z - 2.0) < 1e-5, tuple(body.data.vertices[2].co))
    body.data.shape_keys.key_blocks["Shape 000"].value = 1.0
    bpy.context.view_layer.objects.active = body
    bpy.ops.smplx.fit_skeleton()
    top = rig.data.bones[2].head_local.z
    check("the skeleton fits the shape", abs(top - 3.0) < 1e-4, round(top, 4))
    check("skin weights", len(body.vertex_groups) == 3, [g.name for g in body.vertex_groups])


guarded("SMPL-X", smplx)

print("All passed" if not fails else f"{fails} failed")
sys.exit(1 if fails else 0)
