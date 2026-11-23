# Pantomimus Link for Blender (and Prometheus): your webcam motion capture, live on an armature.
#
# Pantomimus (Atelier's webcam motion capture) streams the solved skeleton on 127.0.0.1:47811, one JSON line a frame:
#   {"type":"skeleton","name":...,"bones":[{"name","parent","head":[x,y,z],"tail":[x,y,z]}...]}   when we connect
#   {"type":"pose","time":t,"bones":[[qw,qx,qy,qz, hx,hy,hz]...],"contact":[l,r],"face":[52]}     each frame
# ("face": ARKit's blendshapes, when the face is tracked; their names come as the skeleton's "faceNames")
# Metres, Y up, the body facing +Z; each bone's turn from its rest in the world's axes, and its head's place.
#
# Install: Edit > Preferences > Add-ons > Install from Disk, pick this file. Then 3D Viewport > Sidebar (N) > Pantomimus.
# In Pantomimus, turn on Live link (Settings > Live link). Connect, and either let it build its own armature or pick
# yours (bones matched by name: use Pantomimus' Mixamo naming for Mixamo rigs). Record keys the action while you move.
#
# SPDX-License-Identifier: MIT
# Farica☆Kimora © Cursed Entertainment

bl_info = {
    "name": "Pantomimus Link",
    "author": "Cursed Entertainment",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "3D Viewport > Sidebar > Pantomimus",
    "description": "Live webcam motion capture from Pantomimus onto an armature, and record it",
    "category": "Animation",
}

import json
import socket

import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from mathutils import Matrix, Quaternion, Vector

# Pantomimus is Y-up; Blender is Z-up: (x, y, z) -> (x, -z, y), a proper turn about X.
def _vec(v, scale=1.0):
    return Vector((v[0], -v[2], v[1])) * scale


def _quat(w, x, y, z):
    return Quaternion((w, x, -z, y))


class _Stream:
    """The connection: a socket read without blocking, split into lines."""
    sock = None
    buf = b""
    skeleton = None        # the last skeleton message
    pose = None            # the last pose message
    frames = 0
    status = "Not connected"

    @classmethod
    def connect(cls, host, port):
        cls.close()
        try:
            s = socket.create_connection((host, port), timeout=2.0)
        except OSError as ex:
            cls.status = f"Can't reach Pantomimus on {host}:{port} ({ex.strerror or ex}). Turn on its live link."
            return False
        s.setblocking(False)
        cls.sock, cls.buf, cls.skeleton, cls.pose, cls.frames = s, b"", None, None, 0
        cls.status = "Connected: waiting for the skeleton"
        return True

    @classmethod
    def close(cls):
        if cls.sock:
            try:
                cls.sock.close()
            except OSError:
                pass
        cls.sock = None
        cls.status = "Not connected"

    @classmethod
    def read(cls):
        """Read what has come; keep only the newest pose (a slow frame skips poses, it never lags)."""
        if not cls.sock:
            return False
        got = False
        while True:
            try:
                data = cls.sock.recv(1 << 16)
            except BlockingIOError:
                break
            except OSError as ex:
                cls.close()
                cls.status = f"Pantomimus closed the link ({ex})"
                return got
            if not data:
                cls.close()
                cls.status = "Pantomimus closed the link"
                return got
            cls.buf += data
        while b"\n" in cls.buf:
            line, cls.buf = cls.buf.split(b"\n", 1)
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get("type") == "skeleton":
                cls.skeleton = msg
                got = True
            elif msg.get("type") == "pose":
                cls.pose = msg
                cls.frames += 1
                got = True
        return got


# --- building and posing ---------------------------------------------------------

def build_armature(context, skel, scale):
    """An armature of the streamed skeleton, at the 3D cursor."""
    name = "Pantomimus " + (skel.get("name") or "Skeleton")
    data = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, data)
    context.collection.objects.link(obj)
    obj.location = context.scene.cursor.location
    obj.show_in_front = True
    prev = context.view_layer.objects.active
    for o in context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bones = []
    for b in skel["bones"]:
        eb = data.edit_bones.new(b["name"])
        eb.head = _vec(b["head"], scale)
        eb.tail = _vec(b["tail"], scale)
        if (eb.tail - eb.head).length < 1e-4:
            eb.tail = eb.head + Vector((0, 0, 0.02))
        bones.append(eb)
    for b, eb in zip(skel["bones"], bones):
        if b["parent"] >= 0:
            eb.parent = bones[b["parent"]]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    if prev and prev != obj:
        prev.select_set(False)
    return obj


def apply_pose(obj, skel, pose, scale, root_motion):
    """Turn each bone of obj that has a streamed bone of its name as Pantomimus' bone turned.

    The stream gives each bone's turn from its rest in world axes. A bone's posed armature-space matrix is that turn
    times its rest orientation, placed at its parent's posed end (or, for the root, where Pantomimus puts it). From
    that, the pose basis Blender keeps. The armature's own bone lengths stay, so any rig of matching names works.
    """
    names = {b["name"]: i for i, b in enumerate(skel["bones"])}
    frame = pose["bones"]
    posed = {}
    order = _parents_first(obj.data.bones)
    for bone in order:
        pb = obj.pose.bones[bone.name]
        i = names.get(bone.name)
        rest = bone.matrix_local
        rest_rot = rest.to_3x3().to_4x4()
        if bone.parent is None or bone.parent.name not in posed:
            parent_posed = None
            rel = rest
        else:
            parent_posed = posed[bone.parent.name]
            rel = bone.parent.matrix_local.inverted() @ rest
        if i is None:
            # no streamed bone of this name: it follows its parent at rest
            desired = (parent_posed @ rel) if parent_posed is not None else rest
        else:
            q = frame[i]
            turn = _quat(q[0], q[1], q[2], q[3]).to_matrix().to_4x4()
            if parent_posed is None:
                head = _vec(q[4:7], scale) if root_motion else rest.translation.copy()
            else:
                head = (parent_posed @ rel).translation
            desired = Matrix.Translation(head) @ turn @ rest_rot
        posed[bone.name] = desired
        base = (parent_posed @ rel) if parent_posed is not None else rest
        pb.rotation_mode = 'QUATERNION'
        basis = base.inverted() @ desired
        loc, rot, _sc = basis.decompose()
        pb.rotation_quaternion = rot
        pb.location = loc if (parent_posed is None and root_motion) else Vector()


def _parents_first(bones):
    out = []
    def walk(b):
        out.append(b)
        for c in b.children:
            walk(c)
    for b in bones:
        if b.parent is None:
            walk(b)
    return out


def key_pose(obj, frame):
    for pb in obj.pose.bones:
        pb.keyframe_insert("rotation_quaternion", frame=frame, group=pb.name)
        if pb.parent is None:
            pb.keyframe_insert("location", frame=frame, group=pb.name)


# --- the face: ARKit's blendshapes onto shape keys ----------------------------------

def face_meshes(st):
    """The meshes the face drives: the one picked, else every mesh under the armature that has shape keys."""
    if st.face_mesh is not None:
        return [st.face_mesh]
    out = []
    if st.target is not None:
        stack = list(st.target.children)
        while stack:
            o = stack.pop()
            stack.extend(o.children)
            if o.type == 'MESH' and o.data.shape_keys:
                out.append(o)
    return out


def apply_face(meshes, names, weights, strength):
    """Each weight onto the shape key of its name (capitals don't matter); how many keys took one."""
    by = {n.lower(): w for n, w in zip(names, weights)}
    n = 0
    for m in meshes:
        if not m.data.shape_keys:
            continue
        for k in m.data.shape_keys.key_blocks:
            w = by.get(k.name.lower())
            if w is not None:
                k.value = max(0.0, min(1.0, w * strength))
                n += 1
    return n


def key_face(meshes, names, frame):
    wanted = {n.lower() for n in names}
    for m in meshes:
        if m.data.shape_keys:
            for k in m.data.shape_keys.key_blocks:
                if k.name.lower() in wanted:
                    k.keyframe_insert("value", frame=frame)


# --- the timer ---------------------------------------------------------------------

def _tick():
    s = bpy.context.scene
    st = s.pantomimus
    if not _Stream.sock:
        return None
    got = _Stream.read()
    if _Stream.skeleton and st.target is None and st.build_own:
        st.target = build_armature(bpy.context, _Stream.skeleton, st.scale)
    if got and _Stream.skeleton and _Stream.pose and st.target and st.target.type == 'ARMATURE':
        apply_pose(st.target, _Stream.skeleton, _Stream.pose, st.scale, st.root_motion)
        _Stream.status = f"Live: {_Stream.frames} frames"
        face = _Stream.pose.get("face")
        names = _Stream.skeleton.get("faceNames")
        meshes = face_meshes(st) if (st.drive_face and face and names) else []
        if meshes:
            keys = apply_face(meshes, names, face, st.face_strength)
            _Stream.status += f", face on {keys} shape keys"
        if st.recording:
            f = s.frame_current
            key_pose(st.target, f)
            if meshes:
                key_face(meshes, names, f)
            s.frame_set(f + 1)
        for area in bpy.context.screen.areas if bpy.context.screen else []:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    if not _Stream.sock:
        st.recording = False
        return None
    return 1.0 / max(1, st.rate)


# --- operators and UI --------------------------------------------------------------

class PANTOMIMUS_OT_connect(bpy.types.Operator):
    """Connect to Pantomimus' live link"""
    bl_idname = "pantomimus.connect"
    bl_label = "Connect"

    def execute(self, context):
        st = context.scene.pantomimus
        if not _Stream.connect(st.host, st.port):
            self.report({'ERROR'}, _Stream.status)
            return {'CANCELLED'}
        if not bpy.app.timers.is_registered(_tick):
            bpy.app.timers.register(_tick, first_interval=0.05)
        return {'FINISHED'}


class PANTOMIMUS_OT_disconnect(bpy.types.Operator):
    """Stop the live link"""
    bl_idname = "pantomimus.disconnect"
    bl_label = "Disconnect"

    def execute(self, context):
        context.scene.pantomimus.recording = False
        _Stream.close()
        if bpy.app.timers.is_registered(_tick):
            bpy.app.timers.unregister(_tick)
        return {'FINISHED'}


class PANTOMIMUS_OT_build(bpy.types.Operator):
    """Make an armature of Pantomimus' skeleton and drive it"""
    bl_idname = "pantomimus.build"
    bl_label = "Make Armature"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _Stream.skeleton is not None

    def execute(self, context):
        st = context.scene.pantomimus
        st.target = build_armature(context, _Stream.skeleton, st.scale)
        return {'FINISHED'}


class PANTOMIMUS_OT_rest(bpy.types.Operator):
    """Put the armature back in its rest pose"""
    bl_idname = "pantomimus.rest"
    bl_label = "Rest Pose"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        t = context.scene.pantomimus.target
        return t is not None and t.type == 'ARMATURE'

    def execute(self, context):
        for pb in context.scene.pantomimus.target.pose.bones:
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = Quaternion()
            pb.location = Vector()
        return {'FINISHED'}


def _armature_poll(_self, obj):
    return obj.type == 'ARMATURE'


class PantomimusSettings(bpy.types.PropertyGroup):
    host: StringProperty(name="Host", default="127.0.0.1")
    port: IntProperty(name="Port", default=47811, min=1, max=65535)
    target: PointerProperty(name="Armature", type=bpy.types.Object, poll=_armature_poll,
                            description="The armature to drive (bones matched by name); empty: make one")
    build_own: BoolProperty(name="Make an armature if none is picked", default=True)
    scale: FloatProperty(name="Scale", default=1.0, min=0.01, max=100.0, soft_max=10.0,
                         description="Pantomimus works in metres; scale for rigs in other units")
    root_motion: BoolProperty(name="Root motion", default=True,
                              description="Move the root as you move; off keeps it in place")
    rate: IntProperty(name="Rate", default=60, min=1, max=120, subtype='NONE', description="Updates a second")
    drive_face: BoolProperty(name="Drive the face", default=True,
                             description="ARKit's blendshapes from Pantomimus onto shape keys of the same names")
    face_mesh: PointerProperty(name="Face", type=bpy.types.Object, poll=lambda _s, o: o.type == 'MESH',
                               description="The mesh whose shape keys the face drives; empty: every mesh under the armature")
    face_strength: FloatProperty(name="Expression", default=1.0, min=0.0, max=2.0, description="Every blendshape times this")
    recording: BoolProperty(name="Record", default=False,
                            description="Key every pose that comes, one frame each, from the current frame")


class PANTOMIMUS_PT_panel(bpy.types.Panel):
    bl_label = "Pantomimus"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Pantomimus"

    def draw(self, context):
        st = context.scene.pantomimus
        layout = self.layout
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(st, "host", text="")
        row.prop(st, "port", text="")
        if _Stream.sock:
            col.operator("pantomimus.disconnect", icon='CANCEL')
        else:
            col.operator("pantomimus.connect", icon='LINKED')
        layout.label(text=_Stream.status)

        box = layout.box()
        box.prop(st, "target")
        if st.target is None:
            box.prop(st, "build_own")
            box.operator("pantomimus.build", icon='ARMATURE_DATA')
        box.prop(st, "scale", slider=True)
        box.prop(st, "rate", slider=True)
        box.prop(st, "root_motion")
        box.operator("pantomimus.rest", icon='LOOP_BACK')

        box = layout.box()
        box.prop(st, "drive_face")
        if st.drive_face:
            box.prop(st, "face_mesh")
            box.prop(st, "face_strength", slider=True)

        row = layout.row()
        row.enabled = _Stream.sock is not None and st.target is not None
        row.prop(st, "recording", toggle=True, icon='REC')


classes = (
    PantomimusSettings,
    PANTOMIMUS_OT_connect,
    PANTOMIMUS_OT_disconnect,
    PANTOMIMUS_OT_build,
    PANTOMIMUS_OT_rest,
    PANTOMIMUS_PT_panel,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.pantomimus = PointerProperty(type=PantomimusSettings)


def unregister():
    _Stream.close()
    if bpy.app.timers.is_registered(_tick):
        bpy.app.timers.unregister(_tick)
    del bpy.types.Scene.pantomimus
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
