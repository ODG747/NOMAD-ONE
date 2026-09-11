# -*- coding: utf-8 -*-
"""
NOMAD ONE - Phase 1 : modelisation.

CARTE DES LIAISONS (metres, X = axe long, Z = haut)
  Body_Core   [-0.0508 .. +0.0508]  coque interne, r = rb(x)
  Grille      [-0.0480 .. +0.0480]  peau exterieure r = rb(x)+0.0009, angle +-142.5 deg
  Base_Pad    [-0.0495 .. +0.0495]  meme peau, angle 143.2 .. 216.8 deg  (jeu 0.7 deg = 0.43 mm)
  Cap_L       [-0.0748 .. -0.0502]  recouvre Body_Core de 0.0006 en X
  Cap_R       [+0.0502 .. +0.0750]  recouvre Body_Core de 0.0006 en X
    -> rainure visible de 2.2 mm entre Grille et chaque embout, fond 1 mm plus bas
  Button_A/B  bases enfoncees de 0.0007 dans la peau superieure
  Port_USBC   creuse dans la face plate de Cap_R (profondeur 2.6 mm)
  LED         lentille sur la face de Cap_R, 0.3 mm en saillie
  Logo        grave 0.25 mm dans la face de Cap_R
  Strap       ancree dans Body_Core en x=+0.043 et x=+0.060, penetration >= 0.0025
  Carabiner   anneau traversant l'ouverture de la sangle en (0.051, 0, 0.0415)
  Driver / Battery / PCB : internes, dans la coque
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector

_HERE = os.path.dirname(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else None
_DIR = globals().get("NOMAD_DIR") or _HERE or r"E:\Autres\NOMAD-ONE\blender"
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)
import nomad_lib
import importlib
importlib.reload(nomad_lib)
from nomad_lib import (lathe, sweep, new_obj, circle_section, rect_section, arc_pts,
                       catmull, scale_z, flatten_bottom, translate, bevel, solidify,
                       smooth, bounds, overlap, recalc, flip, orient_radial, TAU)

# ----------------------------------------------------------------------
# constantes de forme
# ----------------------------------------------------------------------
R = 0.035            # rayon horizontal nominal (diametre 70 mm)
ZK = 0.90            # section elliptique : rayon vertical a 90 %
Z_FLAT = -0.0303     # hauteur du meplat inferieur
SKIN = 0.0009        # epaisseur de la peau exterieure au-dessus du chassis
X_BODY = 0.0508      # demi-longueur du chassis
X_GRIL = 0.0480      # demi-longueur de la grille
X_PAD = 0.0495
X_CAP = 0.0502       # debut des embouts
X_TIP = 0.0750       # extremite droite
TH_PAD = math.radians(143.2)   # bord du patin (mesure depuis le sommet)
TH_GRI = math.radians(142.5)   # bord de la grille
SEG = 256

LOGO_TEXT = "NOMAD ONE"


def rb(x):
    """Rayon du corps : tres leger galbe, plus plein au centre."""
    return R * (1.0 + 0.012 * math.cos(math.pi * max(-0.0505, min(0.0505, x)) / 0.101))


def prof_body(x0, x1, off, n=40):
    return [(x0 + (x1 - x0) * i / n, rb(x0 + (x1 - x0) * i / n) + off) for i in range(n + 1)]


X_SH = 0.0642        # depart de l'epaulement de l'embout droit
R_FACE = 0.0152      # rayon de la face plate qui porte le port et le logo


def cap_shoulder(sign, n=18):
    """Epaulement en quart d'ellipse, tangent au barillet et a la face plate."""
    out = []
    r0 = 0.03536
    for i in range(n + 1):
        t = (i / n) * math.pi / 2
        out.append((sign * (X_SH + (X_TIP - X_SH) * math.sin(t)),
                    R_FACE + (r0 - R_FACE) * math.cos(t)))
    return out


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.images):
        for d in list(blk):
            if d.users == 0:
                blk.remove(d)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def get_coll(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def shape(ob, flat=True):
    """Section elliptique puis meplat."""
    scale_z(ob, ZK)
    if flat:
        flatten_bottom(ob, Z_FLAT)
    ob.data.update()


def lathe_z(name, profile, seg=96, coll=None, uv=False):
    """Lathe dont l'axe de revolution est Z (permutation x,y,z -> y,z,x)."""
    ob = lathe(name, profile, seg=seg, coll=coll, uv=uv)
    for v in ob.data.vertices:
        x, y, z = v.co
        v.co = Vector((y, z, x))
    ob.data.update()
    return ob


def apply_mods(ob):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.ops.object.select_all(action='DESELECT')


def join(target, others, name=None):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    for o in others:
        o.select_set(True)
    bpy.ops.object.join()
    bpy.ops.object.select_all(action='DESELECT')
    if name:
        target.name = name
        target.data.name = name
    return target


def boolean_cut(target, cutter):
    m = target.modifiers.new("Cut", 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = cutter
    m.solver = 'EXACT'
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.data.objects.remove(cutter, do_unlink=True)


# enveloppe interne du chassis (Body_Core solidifie de 1.2 mm)
IN_RX = 0.0342
IN_RZ = 0.0308
IN_ZMIN = -0.0291
IN_XMAX = 0.0496


def inside_shell(name):
    """Nombre de sommets sortant de l'enveloppe interne. Doit valoir 0 pour
    tout organe interne : la boite englobante ne suffit pas a le voir."""
    ob = bpy.data.objects.get(name)
    if not ob:
        return -1, 0
    bad, worst = 0, 0.0
    for v in ob.data.vertices:
        p = ob.matrix_world @ v.co
        z = max(p.z, IN_ZMIN)
        k = (p.y / IN_RX) ** 2 + (z / IN_RZ) ** 2
        if k > 1.0 or abs(p.x) > IN_XMAX:
            bad += 1
            worst = max(worst, k)
    return bad, len(ob.data.vertices)


def rounded_slot_solid(name, cx, half_y, half_z, x0, x1, r, coll=None, n=8):
    """Prisme a section rectangle-arrondi (dans YZ), etendu de x0 a x1."""
    sec = rect_section(half_y, half_z, r, n)
    verts, faces = [], []
    m = len(sec)
    for x in (x0, x1):
        for (a, b) in sec:
            verts.append((x, cx[0] + a, cx[1] + b))
    for k in range(m):
        k2 = (k + 1) % m
        faces.append((k, k2, m + k2, m + k))
    faces.append(tuple(range(m - 1, -1, -1)))
    faces.append(tuple(m + k for k in range(m)))
    return new_obj(name, verts, faces, coll)


# ======================================================================
def build():
    clear_scene()
    C = get_coll("NOMAD_ONE")
    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection.children[C.name]
    log = []

    # ---------------- 1. chassis interne ------------------------------
    prof = [(-X_BODY, 0.0)] + prof_body(-X_BODY, X_BODY, 0.0, 48) + [(X_BODY, 0.0)]
    core = lathe("Body_Core", prof, seg=SEG, coll=C)
    recalc(core)
    shape(core)
    solidify(core, 0.0012)
    apply_mods(core)
    smooth(core, 50)

    # ---------------- 2. grille perforee ------------------------------
    gril = lathe("Grille", prof_body(-X_GRIL, X_GRIL, SKIN, 40), seg=SEG,
                 th0=-TH_GRI, th1=TH_GRI, uv=True, coll=C)
    orient_radial(gril, "x")
    shape(gril, flat=False)
    solidify(gril, 0.0007)
    apply_mods(gril)
    smooth(gril, 50)

    # ---------------- 3. patin inferieur (meplat) ---------------------
    pad = lathe("Base_Pad", prof_body(-X_PAD, X_PAD, SKIN, 40), seg=SEG,
                th0=TH_PAD, th1=TAU - TH_PAD, uv=True, coll=C)
    orient_radial(pad, "x")
    shape(pad)
    solidify(pad, 0.0014)
    bevel(pad, 0.0004, 3, 34)
    apply_mods(pad)
    smooth(pad, 46)

    # ---------------- 4. embouts --------------------------------------
    pl = ([(-X_CAP, 0.0)] +
          [(-x, r) for (x, r) in [(X_CAP, 0.03600), (0.0540, 0.03608),
                                  (0.0590, 0.03600), (0.0630, 0.03560)]] +
          [(-(0.0630 + 0.0118 * math.sin(i / 18 * math.pi / 2)),
            0.03560 * math.cos(i / 18 * math.pi / 2)) for i in range(1, 19)])
    capL = lathe("Cap_L", pl, seg=SEG, coll=C)
    recalc(capL)
    shape(capL)
    bevel(capL, 0.0004, 3, 30)
    apply_mods(capL)
    smooth(capL, 46, flat_pred=lambda p: p.normal.x > 0.995)

    pr = ([(X_CAP, 0.0), (X_CAP, 0.03600), (0.0545, 0.03610),
           (0.0600, 0.03596), (X_SH, 0.03536)] + cap_shoulder(1, 18) +
          [(X_TIP, 0.0)])
    capR = lathe("Cap_R", pr, seg=SEG, coll=C)
    recalc(capR)
    shape(capR)

    # port USB-C : creusement de la face plate
    cut = rounded_slot_solid("cut_usb", (0.0, 0.0), 0.0052, 0.0015,
                             0.0724, 0.0790, 0.0014, C)
    boolean_cut(capR, cut)

    # logo grave
    bpy.ops.object.text_add(location=(0, 0, 0))
    txt = bpy.context.object
    txt.data.body = LOGO_TEXT
    txt.data.align_x = 'CENTER'
    txt.data.align_y = 'CENTER'
    txt.data.size = 0.0023
    txt.data.space_character = 1.05
    txt.data.extrude = 0.0010
    bpy.ops.object.convert(target='MESH')
    txt = bpy.context.object
    for v in txt.data.vertices:                      # local (x,y,z) -> monde (z,x,y)
        a, b, c = v.co
        v.co = Vector((c + 0.07472, a, b + 0.00880))
    txt.data.update()
    boolean_cut(capR, txt)

    bevel(capR, 0.00035, 3, 30)
    apply_mods(capR)
    smooth(capR, 44, flat_pred=lambda p: p.normal.x > 0.995 or p.normal.x < -0.995)

    # ---------------- 5. port USB-C (interieur metallique) ------------
    shell = rounded_slot_solid("Port_USBC", (0.0, 0.0), 0.00505, 0.00138,
                               0.0722, 0.07505, 0.0013, C)
    port = shell
    recalc(port)
    bevel(port, 0.00018, 2, 30)
    apply_mods(port)
    smooth(port, 40)
    tongue = rounded_slot_solid("Port_Tongue", (0.0, 0.0), 0.0033, 0.00042,
                                0.0726, 0.0745, 0.0004, C)
    recalc(tongue)
    bevel(tongue, 0.00012, 2, 30)
    apply_mods(tongue)
    smooth(tongue, 40)

    # ---------------- 6. LED d'etat -----------------------------------
    led = lathe("LED", [(0.07455, 0.0), (0.07455, 0.00115), (0.07495, 0.00115),
                        (0.07525, 0.00098), (0.07540, 0.00060), (0.07543, 0.0)],
                seg=48, coll=C)
    recalc(led)
    translate(led, (0.0, 0.0, -0.00900))
    smooth(led, 50)

    # ---------------- 7. boutons --------------------------------------
    btn_prof = [(0.00000, 0.0), (0.00000, 0.00510), (0.00042, 0.00505),
                (0.00050, 0.00440), (0.00160, 0.00440), (0.00196, 0.00420),
                (0.00214, 0.00360), (0.00222, 0.00250), (0.00224, 0.0)]
    btns = []
    for nm, bx in (("Button_A", -0.0132), ("Button_B", 0.0132)):
        b = lathe_z(nm, btn_prof, seg=72, coll=C)
        recalc(b)
        top = (rb(bx) + SKIN) * ZK
        translate(b, (bx, 0.0, top - 0.00070))
        bevel(b, 0.00016, 2, 30)
        apply_mods(b)
        smooth(b, 40)
        btns.append(b)

    # ---------------- 8. sangle ---------------------------------------
    spath = catmull([(0.0433, 0, 0.0170), (0.0430, 0, 0.0290), (0.0437, 0, 0.0378),
                     (0.0466, 0, 0.0455), (0.0520, 0, 0.0500), (0.0578, 0, 0.0497),
                     (0.0612, 0, 0.0430), (0.0616, 0, 0.0345), (0.0600, 0, 0.0280),
                     (0.0592, 0, 0.0160)], 80)
    strap = sweep("Strap", spath, rect_section(0.00072, 0.0055, 0.00055, 3),
                  coll=C, uv=True)
    recalc(strap)
    bevel(strap, 0.00025, 2, 34)
    apply_mods(strap)
    smooth(strap, 40)

    # ---------------- 9. mousqueton -----------------------------------
    tilt = math.radians(55.0)
    w = Vector((math.sin(tilt), 0.0, math.cos(tilt)))
    yv = Vector((0.0, 1.0, 0.0))
    Pc = Vector((0.0512, 0.0, 0.0408))          # point qui traverse la sangle
    rq, rp = 0.0128, 0.0094
    Cc = Pc + w * rq

    def ring_pt(phi):
        return tuple(Cc + yv * (rp * math.sin(phi)) + w * (-rq * math.cos(phi)))

    frame_pts = [ring_pt(math.radians(a)) for a in
                 [i * (310.0 / 47) + 25.0 for i in range(48)]]
    frame = sweep("carab_frame", frame_pts, circle_section(0.00160, 12), coll=C)
    gate_pts = catmull([ring_pt(math.radians(25.0)),
                        tuple(Vector(ring_pt(math.radians(90.0))) - w * 0.0004),
                        ring_pt(math.radians(335.0))], 24)
    gate = sweep("carab_gate", gate_pts, circle_section(0.00125, 10), coll=C)
    carab = join(frame, [gate], "Carabiner")
    recalc(carab)
    bevel(carab, 0.00022, 2, 40)
    apply_mods(carab)
    smooth(carab, 40)

    # ---------------- 10. organes internes ----------------------------
    # haut-parleur de 43 mm : doit tenir sous la peau elliptique du chassis
    DK = 0.855
    drv_prof = [(0.00000, 0.0), (0.00060, 0.01120), (0.00640, 0.01120),
                (0.00640, 0.00520), (0.00720, 0.00520), (0.01440, 0.02060),
                (0.01550, 0.02220), (0.01520, 0.02360), (0.01410, 0.02430),
                (0.01390, 0.02510), (0.01300, 0.02540)]
    drv_prof = [(a, r * DK) for (a, r) in drv_prof]
    drv = lathe_z("Driver", drv_prof, seg=96, coll=C)
    cap_prof = [(0.00700, 0.0), (0.00790, 0.00380), (0.00840, 0.00500), (0.00860, 0.00530)]
    dust = lathe_z("drv_dust", [(a, r * DK) for (a, r) in cap_prof], seg=96, coll=C)
    drv = join(drv, [dust], "Driver")
    orient_radial(drv, "z")
    solidify(drv, 0.00075)
    apply_mods(drv)
    translate(drv, (-0.0220, 0.0, 0.0045))
    smooth(drv, 44)

    bat_prof = ([(-0.0325, 0.0), (-0.0325, 0.0080), (-0.0322, 0.0089), (-0.0316, 0.0091)] +
                [(0.0316, 0.0091), (0.0322, 0.0089), (0.0325, 0.0080), (0.0325, 0.0044),
                 (0.0328, 0.0040), (0.0328, 0.0)])
    bat = lathe("Battery", bat_prof, seg=64, coll=C)
    recalc(bat)
    translate(bat, (0.0158, 0.0, -0.0098))
    smooth(bat, 44)

    pcb = rounded_slot_solid("PCB", (0.0, -0.0250), 0.0104, 0.00080,
                             -0.0288, 0.0288, 0.0022, C)
    recalc(pcb)
    bevel(pcb, 0.00020, 2, 30)
    apply_mods(pcb)
    smooth(pcb, 40)

    # ---------------- controles ---------------------------------------
    for nm in ("Body_Core", "Grille", "Base_Pad", "Cap_L", "Cap_R", "Port_USBC",
               "Port_Tongue", "LED", "Button_A", "Button_B", "Strap", "Carabiner",
               "Driver", "Battery", "PCB"):
        b = bounds(nm)
        log.append("%-11s X[%+.4f %+.4f] Y[%+.4f %+.4f] Z[%+.4f %+.4f]  v=%d f=%d"
                   % (nm, b['x'][0], b['x'][1], b['y'][0], b['y'][1],
                      b['z'][0], b['z'][1], b['verts'], b['faces']))

    checks = [("Cap_L", "Body_Core", 'x'), ("Cap_R", "Body_Core", 'x'),
              ("Grille", "Body_Core", 'z'), ("Base_Pad", "Body_Core", 'z'),
              ("Button_A", "Grille", 'z'), ("Strap", "Body_Core", 'z'),
              ("Port_USBC", "Cap_R", 'x'), ("LED", "Cap_R", 'x')]
    for a, b_, ax in checks:
        log.append("  joint %-10s <-> %-10s [%s] = %+.4f m" % (a, b_, ax, overlap(a, b_, ax)))

    for nm in ("Driver", "Battery", "PCB"):
        bad, tot_v = inside_shell(nm)
        log.append("  enveloppe %-8s : %d / %d sommets hors du chassis%s"
                   % (nm, bad, tot_v, "" if bad == 0 else "   <<< DEBORDE"))

    tot = bounds("Cap_L")
    allb = [bounds(o.name) for o in C.objects]
    log.append("ENCOMBREMENT  L=%.4f  l=%.4f  h=%.4f" % (
        max(b['x'][1] for b in allb) - min(b['x'][0] for b in allb),
        max(b['y'][1] for b in allb) - min(b['y'][0] for b in allb),
        max(b['z'][1] for b in allb) - min(b['z'][0] for b in allb)))
    log.append("TOTAL faces = %d" % sum(b['faces'] for b in allb))
    return log
