# -*- coding: utf-8 -*-
"""
NOMAD ONE - plan de la slide 5 : l'enceinte de trois quarts, port USB-C bien
visible, un smartphone a cote, relie par un cable. Le telephone affiche un
ecran de charge (vraie geometrie emissive, aucune texture externe).
"""
import bpy, math, sys, os
from mathutils import Vector

DIR = os.path.dirname(os.path.abspath(__file__))
if DIR not in sys.path:
    sys.path.insert(0, DIR)
from nomad_lib import (new_obj, sweep, rect_section, circle_section, catmull,
                       bevel, smooth, recalc)
import materials

# telephone : 71.5 x 146.5 x 7.9 mm
PH_W, PH_H, PH_T = 0.0715, 0.1465, 0.0079
Z_GROUND = -0.0303
YAW = math.radians(-24.0)                      # orientation a plat sur le sol
CENTER = Vector((0.1300, -0.0545, Z_GROUND + PH_T / 2.0 + 0.0002))

U = Vector((math.cos(YAW), math.sin(YAW), 0.0))        # axe long du telephone
V = Vector((-math.sin(YAW), math.cos(YAW), 0.0))       # axe court
W = Vector((0.0, 0.0, 1.0))                            # epaisseur
# reperes de LECTURE de l'ecran, vus depuis la camera de la slide 5 :
# le telephone est a plat, la droite de l'ecran suit +V et le haut suit -U.
S_R, S_U = V, -U


def prism(name, center, u, v, w, hu, hv, hw, r=0.0, n=6, coll=None):
    """Prisme a section rectangle-arrondi, dans une base quelconque."""
    sec = rect_section(hu, hv, r, n)
    m = len(sec)
    verts = []
    for s in (-hw, hw):
        for (a, b) in sec:
            verts.append(tuple(Vector(center) + u * a + v * b + w * s))
    faces = []
    for k in range(m):
        faces.append((k, (k + 1) % m, m + (k + 1) % m, m + k))
    faces.append(tuple(range(m - 1, -1, -1)))
    faces.append(tuple(m + k for k in range(m)))
    ob = new_obj(name, verts, faces, coll)
    return recalc(ob)


def plane(name, center, u, v, hu, hv, coll=None):
    c = Vector(center)
    verts = [tuple(c - u * hu - v * hv), tuple(c + u * hu - v * hv),
             tuple(c + u * hu + v * hv), tuple(c - u * hu + v * hv)]
    return new_obj(name, verts, [(0, 1, 2, 3)], coll)


def _text(body, size, center, u, v, mat, name, bold=False, coll=None):
    bpy.ops.object.text_add(location=(0, 0, 0))
    t = bpy.context.object
    t.data.body = body
    t.data.align_x = 'CENTER'
    t.data.align_y = 'CENTER'
    t.data.size = size
    t.data.extrude = 0.00004
    bpy.ops.object.convert(target='MESH')
    t = bpy.context.object
    t.name = name
    c = Vector(center)
    for vt in t.data.vertices:                 # local (x, y, z) -> u, v, w
        a, b, h = vt.co
        vt.co = c + u * a + v * b + W * h
    t.data.update()
    t.data.materials.clear()
    t.data.materials.append(mat)
    if coll and t.name not in coll.objects:
        for c2 in list(t.users_collection):
            c2.objects.unlink(t)
        coll.objects.link(t)
    return t


def screen_materials():
    glass = materials.plastic("M_Phone_Glass", (0.0035, 0.0038, 0.0050, 1.0),
                              0.075, micro=14000.0)
    frame = materials.metal("M_Phone_Frame", base=(0.330, 0.345, 0.372, 1.0),
                            rough=0.24, aniso=0.35)
    scr = materials.plastic("M_Phone_Screen", (0.0055, 0.0090, 0.0125, 1.0), 0.10)
    p = scr.node_tree.nodes.get("Principled BSDF") or \
        next(n for n in scr.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Emission Color'].default_value = (0.0075, 0.0290, 0.0295, 1.0)
    p.inputs['Emission Strength'].default_value = 1.0
    ink = bpy.data.materials.get("M_Screen_Ink") or bpy.data.materials.new("M_Screen_Ink")
    ink.use_nodes = True
    nt = ink.node_tree
    nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (0.760, 0.960, 0.905, 1.0)
    e.inputs['Strength'].default_value = 3.2
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(e.outputs['Emission'], o.inputs['Surface'])
    mint = bpy.data.materials.get("M_Screen_Mint") or bpy.data.materials.new("M_Screen_Mint")
    mint.use_nodes = True
    nt = mint.node_tree
    nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (0.010, 0.760, 0.600, 1.0)
    e.inputs['Strength'].default_value = 3.8
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(e.outputs['Emission'], o.inputs['Surface'])
    return glass, frame, scr, ink, mint


def build_phone(coll=None):
    glass, frame, scr, ink, mint = screen_materials()
    body = prism("Phone_Body", CENTER, U, V, W, PH_H / 2, PH_W / 2, PH_T / 2,
                 r=0.0092, n=8, coll=coll)
    bevel(body, 0.00045, 3, 30)
    body.data.materials.append(frame)
    smooth(body, 34)

    top = CENTER + W * (PH_T / 2 + 0.00015)
    gl = plane("Phone_Glass", top, U, V, PH_H / 2 - 0.0022, PH_W / 2 - 0.0022, coll)
    gl.data.materials.append(glass)

    sp = top + W * 0.00010
    sc = plane("Phone_Screen", sp, U, V, PH_H / 2 - 0.0034, PH_W / 2 - 0.0034, coll)
    sc.data.materials.append(scr)

    Z0 = PH_T / 2.0
    dark = bpy.data.materials.get("M_Screen_Dark") or bpy.data.materials.new("M_Screen_Dark")
    dark.use_nodes = True
    nt = dark.node_tree
    nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (0.010, 0.024, 0.026, 1.0)
    e.inputs['Strength'].default_value = 0.45
    nt.links.new(e.outputs['Emission'],
                 nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])

    # icone de batterie, couchee dans le sens de lecture de l'ecran
    b0 = CENTER + S_U * 0.0205
    shell = plane("Bat_Shell", b0 + W * (Z0 + 0.00027), S_R, S_U, 0.0150, 0.0072, coll)
    shell.data.materials.append(ink)
    inner = plane("Bat_Inner", b0 + W * (Z0 + 0.00040), S_R, S_U, 0.0134, 0.0058, coll)
    inner.data.materials.append(dark)
    fill = plane("Bat_Fill", b0 + S_R * (-0.0134 + 0.0091) + W * (Z0 + 0.00052),
                 S_R, S_U, 0.0091, 0.0047, coll)
    fill.data.materials.append(mint)
    nub = plane("Bat_Nub", b0 + S_R * 0.0164 + W * (Z0 + 0.00027),
                S_R, S_U, 0.0016, 0.0028, coll)
    nub.data.materials.append(ink)

    _text("68 %", 0.0135, CENTER + S_U * (-0.0060) + W * (Z0 + 0.00030),
          S_R, S_U, ink, "Scr_Pct", coll=coll)
    _text("EN CHARGE", 0.0046, CENTER + S_U * (-0.0262) + W * (Z0 + 0.00030),
          S_R, S_U, mint, "Scr_Lbl", coll=coll)
    return body


def build_cable(coll=None):
    """Cable du port USB-C de l'enceinte vers le bas du telephone."""
    # Le port d'un telephone est sur son bord BAS, ici le bord +U, tourne vers
    # la camera. Le cable descend de l'enceinte, longe le telephone au sol
    # cote +V, puis revient se brancher par le bas : il ne passe plus sur l'ecran.
    port = Vector((0.0876, 0.0, 0.0))
    zg = Z_GROUND + 0.0014                          # cable pose au sol
    zp = CENTER.z                                   # hauteur du port

    def ph(u, v, z):                                # repere du telephone -> monde
        p = CENTER + U * u + V * v
        return Vector((p.x, p.y, z))

    plug_c = PH_H / 2 + 0.0052                      # centre de la fiche, hors du bord
    pts = catmull([
        port,
        port + Vector((0.014, -0.003, -0.007)),
        ph(-0.068, 0.050, zg + 0.004),
        ph(0.000, 0.054, zg),
        ph(0.070, 0.052, zg),
        ph(0.104, 0.026, zg),
        ph(plug_c + 0.018, 0.004, zp),
        ph(plug_c + 0.0062, 0.0, zp),
    ], 110)
    cab = sweep("Cable", pts, circle_section(0.00135, 12), coll=coll)
    recalc(cab)
    smooth(cab, 40)
    rub = materials.plastic("M_Cable", (0.0060, 0.0068, 0.0105, 1.0), 0.52,
                            micro=9000.0)
    cab.data.materials.append(rub)

    plug = prism("Plug", ph(plug_c, 0.0, zp), U, V, W,
                 0.0062, 0.0056, 0.0021, r=0.0011, n=6, coll=coll)
    bevel(plug, 0.00020, 2, 30)
    smooth(plug, 34)
    met = bpy.data.materials.get("M_Metal_Dark") or materials.metal("M_Metal_Dark")
    plug.data.materials.append(met)

    sx = Vector((1.0, 0.0, 0.0))
    plug2 = prism("Plug_Speaker", Vector((0.0812, 0.0, 0.0)), sx,
                  Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0)),
                  0.0068, 0.0052, 0.0024, r=0.0011, n=6, coll=coll)
    bevel(plug2, 0.00020, 2, 30)
    smooth(plug2, 34)
    plug2.data.materials.append(met)
    return cab


def build_slide5(studio):
    """Compose le plan : camera plus haute et plus a droite pour degager la
    face qui porte le port USB-C, et le telephone dans le meme plan net."""
    coll = bpy.data.collections.get("NOMAD_ONE") or bpy.context.scene.collection
    build_phone(coll)
    build_cable(coll)
    target = (0.070, -0.026, -0.008)
    # az plus ouvert : la face qui porte le port USB-C se presente de face.
    # f/14 et mise au point a mi-scene : enceinte ET ecran restent lisibles.
    cam = studio.make_camera("Cam", dist=0.70, az=63.0, elev=21.0, focal=76.0,
                             target=target, fstop=14.0, focus_shift=0.0)
    # un peu de lumiere cote telephone, sinon l'ecran est seul a s'y voir
    studio.make_area("Fill_Phone", 0.55, 96.0, 22.0, 0.45, 1.5,
                     (0.80, 0.88, 1.0), ratio=1.2, target=target)
    return cam
