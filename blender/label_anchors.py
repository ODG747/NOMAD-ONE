# -*- coding: utf-8 -*-
"""
Position ecran (0..1) de chaque piece dans la derniere image de la vue eclatee.
Sert a relier les etiquettes de la slide 4 aux bonnes pieces.

    blender --background --factory-startup --python label_anchors.py
"""
import bpy, os, sys, json
from mathutils import Vector

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)
import render_jobs as rj
from bpy_extras.object_utils import world_to_camera_view

rj.build_scene(transparent=True)
g = bpy.data.objects.get("Ground")
if g:
    g.hide_render = True
base = {n: bpy.data.objects[n].location.copy() for n in rj.PARTS if n in bpy.data.objects}


def place(k):
    for n, b in base.items():
        dx, dy, dz = rj.EXPLODE.get(n, (0, 0, 0))
        bpy.data.objects[n].location = b + Vector((dx * k, dy * k, dz * k))
    bpy.context.view_layer.update()


k = 1.0                                   # meme ajustement que job_exploded
for _ in range(8):
    place(k)
    e = rj.ndc_extent(rj.PARTS)
    if e <= 0.94:
        break
    k *= 0.94 / e
place(k)

sc, cam = bpy.context.scene, bpy.context.scene.camera


def center(names):
    pts = []
    for n in names:
        ob = bpy.data.objects[n]
        pts += [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return sum(pts, Vector()) / len(pts)


want = {"bat": ["Battery"], "driv": ["Driver"], "body": ["Body_Core"],
        "gril": ["Grille"], "btn": ["Button_A", "Button_B"], "carab": ["Carabiner"]}
out = {}
for key, names in want.items():
    c = world_to_camera_view(sc, cam, center(names))
    out[key] = [round(c.x, 4), round(1.0 - c.y, 4)]    # y vers le bas, comme l'ecran
print("ANCHORS " + json.dumps(out))
