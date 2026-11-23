# SPDX-FileCopyrightText: 2026 Cursed Entertainment
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
SMPL-X bodies in Prometheus.

The SMPL, SMPL-H and SMPL-X body models are free for non-commercial use only,
so Prometheus does not ship them. Each user registers at https://smpl-x.is.tue.mpg.de
(or https://smpl.is.tue.mpg.de), downloads the .npz model files and points this
add-on at that folder. This add-on's own code is GPL and contains none of the models' data.
"""

bl_info = {
    "name": "SMPL-X Bodies",
    "author": "Cursed Entertainment",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "3D Viewport > Sidebar > Humans",
    "description": "Load SMPL, SMPL-H and SMPL-X body models (.npz you download yourself) "
                   "with shape and expression sliders and a fitted skeleton",
    "support": 'OFFICIAL',
    "category": "Add Mesh",
}

import os

import bpy
import numpy as np
from bpy.props import EnumProperty, FloatProperty, IntProperty, StringProperty
from mathutils import Vector

# --- joint names ---------------------------------------------------------------

_BODY = [
    "pelvis", "left_hip", "right_hip", "spine1", "left_knee", "right_knee", "spine2",
    "left_ankle", "right_ankle", "spine3", "left_foot", "right_foot", "neck",
    "left_collar", "right_collar", "head", "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow", "left_wrist", "right_wrist",
]
_FINGERS = ["index", "middle", "pinky", "ring", "thumb"]


def _hand(side):
    return [f"{side}_{f}{i}" for f in _FINGERS for i in (1, 2, 3)]


JOINT_NAMES = {
    24: _BODY + ["left_hand", "right_hand"],                       # SMPL
    52: _BODY + _hand("left") + _hand("right"),                    # SMPL-H
    55: _BODY + ["jaw", "left_eye", "right_eye"] + _hand("left") + _hand("right"),  # SMPL-X
}

GENDERS = [
    ('NEUTRAL', "Neutral", ""),
    ('FEMALE', "Female", ""),
    ('MALE', "Male", ""),
]

# Models are Y-up in metres; Blender is Z-up.
def _to_blender(a):
    a = np.asarray(a, dtype=np.float64)
    return np.stack([a[..., 0], -a[..., 2], a[..., 1]], axis=-1)


# --- model files ---------------------------------------------------------------

_cache = {}


def _prefs(context):
    return context.preferences.addons[__package__].preferences


def find_model(folder, gender):
    """Find the .npz for a gender in the user's folder (searching sub-folders too)."""
    if not folder or not os.path.isdir(folder):
        return None
    want = gender.lower()
    found = []
    for root, _dirs, files in os.walk(folder):
        for f in files:
            lf = f.lower()
            if lf.endswith(".npz") and want in lf:
                found.append(os.path.join(root, f))
    # Prefer SMPL-X, then SMPL-H, then SMPL.
    found.sort(key=lambda p: (0 if "smplx" in p.lower() else 1 if "smplh" in p.lower() else 2, p))
    return found[0] if found else None


def load_model(path):
    if path in _cache:
        return _cache[path]
    d = np.load(path, allow_pickle=True)
    m = {
        "v": np.asarray(d["v_template"], dtype=np.float64),
        "f": np.asarray(d["f"], dtype=np.int64),
        "shapedirs": np.asarray(d["shapedirs"], dtype=np.float64),
        "J_regressor": np.asarray(d["J_regressor"].item().toarray()
                                  if d["J_regressor"].dtype == object else d["J_regressor"],
                                  dtype=np.float64),
        "weights": np.asarray(d["weights"], dtype=np.float64),
        "parents": np.asarray(d["kintree_table"], dtype=np.int64)[0],
    }
    m["parents"][0] = -1
    total = m["shapedirs"].shape[2]
    # SMPL-X keeps shape and expression in one array: 300 + 100 (2020) or 10 + 10 (v1.0).
    if "smplx" in os.path.basename(path).lower() or m["v"].shape[0] == 10475:
        m["n_shape"] = 300 if total >= 400 else total // 2
    else:
        m["n_shape"] = total
    m["n_expr"] = total - m["n_shape"]
    _cache[path] = m
    return m


# --- building ------------------------------------------------------------------

def _shaped_vertices(m, betas, exprs):
    v = m["v"].copy()
    nb = len(betas)
    if nb:
        v += m["shapedirs"][:, :, :nb] @ np.asarray(betas)
    ne = len(exprs)
    if ne:
        s = m["n_shape"]
        v += m["shapedirs"][:, :, s:s + ne] @ np.asarray(exprs)
    return v


def _joints(m, verts):
    return m["J_regressor"] @ verts


def build_body(context, path, gender, n_shape, n_expr):
    m = load_model(path)
    n_shape = min(n_shape, m["n_shape"])
    n_expr = min(n_expr, m["n_expr"])
    kind = {6890: "SMPL", 10475: "SMPL-X"}.get(m["v"].shape[0], "SMPL")
    if m["weights"].shape[1] == 52:
        kind = "SMPL-H"
    name = f"{kind} {gender.title()}"

    verts = _to_blender(m["v"])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts.tolist(), [], m["f"].tolist())
    mesh.shade_smooth()
    mesh.update()

    body = bpy.data.objects.new(name, mesh)
    body["smplx_model"] = path
    body["smplx_shape_count"] = n_shape
    body["smplx_expr_count"] = n_expr

    # Shape and expression sliders as shape keys.
    body.shape_key_add(name="Basis", from_mix=False)
    for i in range(n_shape):
        k = body.shape_key_add(name=f"Shape {i:03d}", from_mix=False)
        k.slider_min, k.slider_max = -5.0, 5.0
        k.data.foreach_set("co", _to_blender(m["v"] + m["shapedirs"][:, :, i]).ravel())
    s = m["n_shape"]
    for i in range(n_expr):
        k = body.shape_key_add(name=f"Expression {i:03d}", from_mix=False)
        k.slider_min, k.slider_max = -5.0, 5.0
        k.data.foreach_set("co", _to_blender(m["v"] + m["shapedirs"][:, :, s + i]).ravel())

    # Skeleton.
    arm_data = bpy.data.armatures.new(name + " Skeleton")
    rig = bpy.data.objects.new(name + " Skeleton", arm_data)
    coll = context.collection
    coll.objects.link(rig)
    coll.objects.link(body)
    rig.location = context.scene.cursor.location
    body.parent = rig

    names = _joint_names(m)
    context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    _place_bones(arm_data, m, _to_blender(_joints(m, m["v"])), names, create=True)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Skin weights.
    w = m["weights"]
    for j, jn in enumerate(names):
        idx = np.nonzero(w[:, j] > 1e-6)[0]
        if not len(idx):
            continue
        vg = body.vertex_groups.new(name=jn)
        for vi in idx:
            vg.add([int(vi)], float(w[vi, j]), 'REPLACE')
    mod = body.modifiers.new("Skeleton", 'ARMATURE')
    mod.object = rig

    for o in context.selected_objects:
        o.select_set(False)
    body.select_set(True)
    context.view_layer.objects.active = body
    return body


def _joint_names(m):
    n = m["weights"].shape[1]
    return JOINT_NAMES.get(n, [f"joint_{i:02d}" for i in range(n)])


def _place_bones(arm_data, m, joints, names, create):
    parents = m["parents"]
    children = {}
    for j, p in enumerate(parents):
        if p >= 0:
            children.setdefault(int(p), []).append(j)
    bones = []
    for j, jn in enumerate(names):
        b = arm_data.edit_bones.new(jn) if create else arm_data.edit_bones[jn]
        bones.append(b)
    for j, b in enumerate(bones):
        head = Vector(joints[j])
        kids = children.get(j, [])
        if len(kids) == 1:
            tail = Vector(joints[kids[0]])
        elif kids:
            tail = sum((Vector(joints[k]) for k in kids), Vector()) / len(kids)
        else:
            p = parents[j]
            direction = (head - Vector(joints[p])) if p >= 0 else Vector((0, 0, 1))
            tail = head + direction.normalized() * 0.03
        if (tail - head).length < 1e-4:
            tail = head + Vector((0, 0, 0.03))
        b.head, b.tail = head, tail
        if create and parents[j] >= 0:
            b.parent = bones[parents[j]]


def fit_skeleton(context, body):
    """Move the joints to match the body's current shape and expression sliders."""
    rig = body.parent
    if rig is None or rig.type != 'ARMATURE':
        return False
    m = load_model(body["smplx_model"])
    keys = body.data.shape_keys.key_blocks if body.data.shape_keys else {}
    betas = [keys[f"Shape {i:03d}"].value for i in range(body["smplx_shape_count"])]
    exprs = [keys[f"Expression {i:03d}"].value for i in range(body["smplx_expr_count"])]
    joints = _to_blender(_joints(m, _shaped_vertices(m, betas, exprs)))
    prev = context.view_layer.objects.active
    context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    _place_bones(rig.data, m, joints, _joint_names(m), create=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    context.view_layer.objects.active = prev
    return True


def _body_of(obj):
    if obj is None:
        return None
    if "smplx_model" in obj:
        return obj
    if obj.type == 'ARMATURE':
        for c in obj.children:
            if "smplx_model" in c:
                return c
    return None


# --- operators -----------------------------------------------------------------

class SMPLX_OT_add_body(bpy.types.Operator):
    """Add an SMPL-X (or SMPL / SMPL-H) body from the model files you downloaded"""
    bl_idname = "smplx.add_body"
    bl_label = "Add SMPL-X Body"
    bl_options = {'REGISTER', 'UNDO'}

    gender: EnumProperty(name="Body", items=GENDERS, default='FEMALE')
    shape_count: IntProperty(name="Shape Sliders", default=10, min=0, max=300)
    expression_count: IntProperty(name="Expression Sliders", default=10, min=0, max=100)

    def execute(self, context):
        folder = _prefs(context).model_folder
        path = find_model(bpy.path.abspath(folder), self.gender)
        if not path:
            self.report({'ERROR'}, "No model file found. Download the SMPL-X models (.npz) from "
                        "smpl-x.is.tue.mpg.de and set their folder in Preferences > Add-ons > SMPL-X Bodies")
            return {'CANCELLED'}
        try:
            build_body(context, path, self.gender, self.shape_count, self.expression_count)
        except Exception as ex:  # A bad or old-format file (e.g. sparse arrays needing SciPy).
            self.report({'ERROR'}, f"Couldn't read {os.path.basename(path)}: {ex}")
            return {'CANCELLED'}
        return {'FINISHED'}


class SMPLX_OT_fit_skeleton(bpy.types.Operator):
    """Move the skeleton's joints to fit the body's current shape"""
    bl_idname = "smplx.fit_skeleton"
    bl_label = "Fit Skeleton to Shape"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _body_of(context.active_object) is not None

    def execute(self, context):
        if not fit_skeleton(context, _body_of(context.active_object)):
            self.report({'ERROR'}, "This body has no skeleton")
            return {'CANCELLED'}
        return {'FINISHED'}


class SMPLX_OT_reset(bpy.types.Operator):
    """Set every shape or expression slider back to zero"""
    bl_idname = "smplx.reset"
    bl_label = "Reset Sliders"
    bl_options = {'REGISTER', 'UNDO'}

    which: EnumProperty(items=[('SHAPE', "Shape", ""), ('EXPRESSION', "Expression", "")])

    @classmethod
    def poll(cls, context):
        return _body_of(context.active_object) is not None

    def execute(self, context):
        body = _body_of(context.active_object)
        prefix = "Shape " if self.which == 'SHAPE' else "Expression "
        for k in body.data.shape_keys.key_blocks:
            if k.name.startswith(prefix):
                k.value = 0.0
        if self.which == 'SHAPE':
            fit_skeleton(context, body)
        return {'FINISHED'}


class SMPLX_OT_random_shape(bpy.types.Operator):
    """Give the body a random, natural-looking shape"""
    bl_idname = "smplx.random_shape"
    bl_label = "Random Shape"
    bl_options = {'REGISTER', 'UNDO'}

    strength: FloatProperty(name="Strength", default=1.0, min=0.0, max=3.0)

    @classmethod
    def poll(cls, context):
        return _body_of(context.active_object) is not None

    def execute(self, context):
        body = _body_of(context.active_object)
        rng = np.random.default_rng()
        for k in body.data.shape_keys.key_blocks:
            if k.name.startswith("Shape "):
                k.value = float(np.clip(rng.normal(0.0, self.strength), -5.0, 5.0))
        fit_skeleton(context, body)
        return {'FINISHED'}


# --- UI ------------------------------------------------------------------------

class SMPLX_PT_panel(bpy.types.Panel):
    bl_label = "SMPL-X Body"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Humans"

    def draw(self, context):
        layout = self.layout
        if not _prefs(context).model_folder:
            col = layout.column(align=True)
            col.label(text="SMPL-X models aren't included", icon='INFO')
            col.label(text="(free for non-commercial use only).")
            col.operator("wm.url_open", text="Download from smpl-x.is.tue.mpg.de").url = \
                "https://smpl-x.is.tue.mpg.de"
            col.prop(_prefs(context), "model_folder", text="")
            return
        layout.operator("smplx.add_body", icon='OUTLINER_OB_ARMATURE')

        body = _body_of(context.active_object)
        if body is None or not body.data.shape_keys:
            return
        keys = body.data.shape_keys.key_blocks

        box = layout.box()
        row = box.row()
        row.label(text="Shape")
        row.operator("smplx.random_shape", text="", icon='FILE_REFRESH')
        row.operator("smplx.reset", text="", icon='LOOP_BACK').which = 'SHAPE'
        col = box.column(align=True)
        for i in range(body["smplx_shape_count"]):
            col.prop(keys[f"Shape {i:03d}"], "value", text=f"Shape {i + 1}", slider=True)
        box.operator("smplx.fit_skeleton", icon='ARMATURE_DATA')

        if body["smplx_expr_count"]:
            box = layout.box()
            row = box.row()
            row.label(text="Expression")
            row.operator("smplx.reset", text="", icon='LOOP_BACK').which = 'EXPRESSION'
            col = box.column(align=True)
            for i in range(body["smplx_expr_count"]):
                col.prop(keys[f"Expression {i:03d}"], "value", text=f"Expression {i + 1}", slider=True)


class SMPLXPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    model_folder: StringProperty(
        name="Model Folder",
        description="Folder holding the SMPL-X / SMPL-H / SMPL .npz files you downloaded",
        subtype='DIR_PATH',
    )

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "model_folder")
        col.label(text="The SMPL-X models are free for non-commercial use only, so they aren't included.")
        col.operator("wm.url_open", text="Get them at smpl-x.is.tue.mpg.de").url = "https://smpl-x.is.tue.mpg.de"


def _menu_add(self, context):
    self.layout.operator("smplx.add_body", text="SMPL-X Body", icon='OUTLINER_OB_ARMATURE')


classes = (
    SMPLXPreferences,
    SMPLX_OT_add_body,
    SMPLX_OT_fit_skeleton,
    SMPLX_OT_reset,
    SMPLX_OT_random_shape,
    SMPLX_PT_panel,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_MT_add.append(_menu_add)


def unregister():
    bpy.types.VIEW3D_MT_add.remove(_menu_add)
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
