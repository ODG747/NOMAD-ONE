# -*- coding: utf-8 -*-
"""
NOMAD ONE - decors d'ambiance (fond opaque, slides 2 et 7).

  rock     : posee sur un rocher, en altitude
  backpack : accrochee par son mousqueton a une sangle de sac a dos
  tent     : posee sur le tapis de sol, sous la toile d'une tente

Chaque decor remplace entierement l'eclairage de studio. Tout est procedural :
relief genere par bruit, materiaux en noeuds, aucun fichier externe.
"""
import bpy, math, sys, os
from mathutils import Vector, noise

DIR = os.path.dirname(os.path.abspath(__file__))
if DIR not in sys.path:
    sys.path.insert(0, DIR)
from nomad_lib import (new_obj, smooth, recalc, bevel, sweep,
                       rect_section, catmull)
import materials, studio

Z_GROUND = -0.0303
PARTS = ["Body_Core", "Grille", "Base_Pad", "Cap_L", "Cap_R", "Port_USBC",
         "Port_Tongue", "LED", "Button_A", "Button_B", "Strap", "Carabiner",
         "Driver", "Battery", "PCB"]


# ----------------------------------------------------------------------
def clear_stage():
    """Enleve le plateau de studio : lumieres, sol, monde."""
    for n in ("Key_Softbox", "Fill_Cool", "Rim_Strip", "Top_Sweep",
              "Fill_Phone", "Ground"):
        ob = bpy.data.objects.get(n)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)


def pivot_model(name="Pose", pitch=0.0, yaw=0.0, offset=(0, 0, 0)):
    """Repose l'enceinte entiere via un pivot unique (pas d'Euler par piece)."""
    piv = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(piv)
    piv.rotation_mode = 'YXZ'
    piv.rotation_euler = (0.0, pitch, yaw)
    piv.location = offset
    for nm in PARTS:
        ob = bpy.data.objects.get(nm)
        if ob:
            ob.parent = piv
            ob.matrix_parent_inverse = piv.matrix_world.inverted()
    bpy.context.view_layer.update()
    return piv


def terrain(name, size, res, height, seed=0.0, flat_at=None, flat_r=0.0,
            z0=Z_GROUND, octaves=5, coll=None):
    """Grille deformee par turbulence. flat_at/flat_r menagent une zone plane
    (l'enceinte a un meplat : elle doit poser franchement, pas leviter)."""
    verts, faces = [], []
    step = size / res
    for j in range(res + 1):
        for i in range(res + 1):
            x = -size / 2 + i * step
            y = -size / 2 + j * step
            v = Vector((x * 3.1 + seed, y * 3.1 + seed, seed * 0.7))
            h = noise.turbulence(v, octaves, False) * height
            h += noise.turbulence(v * 6.5, 3, True) * height * 0.22
            if flat_at is not None:
                d = math.hypot(x - flat_at[0], y - flat_at[1])
                k = min(1.0, max(0.0, (d - flat_r) / max(1e-6, flat_r * 1.7)))
                h *= k * k * (3 - 2 * k)
            verts.append((x, y, z0 + h))
    for j in range(res):
        for i in range(res):
            a = j * (res + 1) + i
            faces.append((a, a + 1, a + res + 2, a + res + 1))
    ob = new_obj(name, verts, faces, coll)
    recalc(ob)
    smooth(ob, 60)
    return ob


def sky(top, horizon, ground, strength=1.0, sun_dir=None, sun_col=None,
        sun_size=0.6):
    """Monde en degrade ciel/horizon/sol + halo solaire optionnel."""
    w = bpy.data.worlds.get("Ambience") or bpy.data.worlds.new("Ambience")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    n, L = nt.nodes.new, nt.links.new
    tex = n('ShaderNodeTexCoord')
    sep = n('ShaderNodeSeparateXYZ')
    ramp = n('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.interpolation = 'EASE'
    cr.elements[0].position = 0.32
    cr.elements[0].color = tuple(ground) + (1,)
    cr.elements[1].position = 0.98
    cr.elements[1].color = tuple(top) + (1,)
    cr.elements.new(0.505).color = tuple(horizon) + (1,)
    bg = n('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = strength
    out = n('ShaderNodeOutputWorld')
    L(tex.outputs['Generated'], sep.inputs['Vector'])
    L(sep.outputs['Z'], ramp.inputs['Fac'])
    L(ramp.outputs['Color'], bg.inputs['Color'])
    L(bg.outputs['Background'], out.inputs['Surface'])
    return w


def sun(name, az, elev, power, color, angle_deg=0.9):
    ob = bpy.data.objects.get(name)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy = power
    ld.color = color
    ld.angle = math.radians(angle_deg)
    o = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(o)
    o.matrix_world = studio.look_at(studio.polar(4.0, az, elev, (0, 0, 0)), (0, 0, 0))
    return o


# ----------------------------------------------------------------------
# materiaux de decor
# ----------------------------------------------------------------------
def mat_granite():
    m = materials._mat("M_Granite")
    nt = materials.NT(m.node_tree)
    p = materials.principled(nt, Metallic=0.0)
    tex = nt.n('ShaderNodeTexCoord')
    geo = nt.n('ShaderNodeNewGeometry')
    grain = nt.n('ShaderNodeTexVoronoi')
    grain.voronoi_dimensions = '3D'
    nt.val(grain, 'Scale', 900.0)
    nt.link(tex, 'Object', grain, 'Vector')
    blotch = nt.noise((tex, 'Object'), 26.0, 6.0, 0.62)
    crack = nt.noise((tex, 'Object'), 130.0, 8.0, 0.75)
    base = nt.mixrgb((grain, 'Distance'), (0.086, 0.083, 0.078, 1.0),
                     (0.168, 0.163, 0.152, 1.0))
    base2 = nt.mixrgb((blotch, 'Fac'), (base, 'Color'), (0.052, 0.051, 0.049, 1.0))
    lich = nt.noise((tex, 'Object'), 42.0, 7.0, 0.70)
    lr = nt.ramp((lich, 'Fac'), [(0.545, (0, 0, 0, 1)), (0.610, (1, 1, 1, 1))])
    base3 = nt.mixrgb((lr, 'Color'), (base2, 'Color'), (0.118, 0.126, 0.062, 1.0))
    dark = nt.ramp((geo, 'Pointiness'), [(0.40, (0, 0, 0, 1)), (0.50, (1, 1, 1, 1))])
    base4 = nt.mixrgb((dark, 'Color'), (0.030, 0.029, 0.028, 1.0), (base3, 'Color'))
    nt.link(base4, 'Color', p, 'Base Color')
    b1 = nt.bump((grain, 'Distance'), 0.45, 0.0012)
    b2 = nt.bump((crack, 'Fac'), 0.60, 0.0035, normal=(b1, 'Normal'))
    nt.link(b2, 'Normal', p, 'Normal')
    rg = nt.mixrgb((blotch, 'Fac'), (0.78, 0.78, 0.78, 1), (0.94, 0.94, 0.94, 1))
    nt.link(rg, 'Color', p, 'Roughness')
    return m


def mat_nylon(name, base, scale=1400.0, sheen=0.55, rip_div=11.0,
              rip_str=0.30, rip_dist=0.00090):
    """Toile technique : ripstop fin, un peu satine."""
    m = materials._mat(name)
    nt = materials.NT(m.node_tree)
    p = materials.principled(nt, Metallic=0.0)
    tex = nt.n('ShaderNodeTexCoord')
    wv = nt.n('ShaderNodeTexWave')
    wv.wave_type = 'BANDS'
    wv.bands_direction = 'X'
    wv.wave_profile = 'SIN'
    nt.val(wv, 'Scale', scale)
    nt.link(tex, 'Object', wv, 'Vector')
    wv2 = nt.n('ShaderNodeTexWave')
    wv2.wave_type = 'BANDS'
    wv2.bands_direction = 'Y'
    wv2.wave_profile = 'SIN'
    nt.val(wv2, 'Scale', scale)
    nt.link(tex, 'Object', wv2, 'Vector')
    weave = nt.math('MAXIMUM', (wv, 'Fac'), (wv2, 'Fac'))
    rip = nt.n('ShaderNodeTexWave')
    rip.wave_type = 'BANDS'
    rip.bands_direction = 'DIAGONAL'
    nt.val(rip, 'Scale', scale / rip_div)
    nt.link(tex, 'Object', rip, 'Vector')
    fuzz = nt.noise((tex, 'Object'), 5200.0, 3.0, 0.6)
    b1 = nt.bump((fuzz, 'Fac'), 0.22, 0.00018)
    b2 = nt.bump((weave, 'Value'), 0.55, 0.00050, normal=(b1, 'Normal'))
    b3 = nt.bump((rip, 'Fac'), rip_str, rip_dist, normal=(b2, 'Normal'))
    nt.link(b3, 'Normal', p, 'Normal')
    fade = nt.noise((tex, 'Object'), 14.0, 5.0, 0.6)
    col = nt.mixrgb((weave, 'Value'), tuple(v * 0.55 for v in base[:3]) + (1.0,), base)
    col2 = nt.mixrgb((fade, 'Fac'), (col, 'Color'),
                     tuple(min(1.0, v * 1.30) for v in base[:3]) + (1.0,))
    nt.link(col2, 'Color', p, 'Base Color')
    nt.val(p, 'Roughness', 0.80)
    nt.val(p, 'Sheen Weight', sheen)
    nt.val(p, 'Sheen Roughness', 0.28)
    return m


def mat_tentwall():
    """Toile fine retro-eclairee : la lumiere du dehors la traverse."""
    m = materials._mat("M_TentWall")
    nt = materials.NT(m.node_tree)
    tex = nt.n('ShaderNodeTexCoord')
    weave = nt.noise((tex, 'Object'), 2600.0, 3.0, 0.55)
    grain = nt.noise((tex, 'Object'), 150.0, 6.0, 0.62)   # trame lisible de loin
    blotch = nt.noise((tex, 'Object'), 11.0, 5.0, 0.62)
    diff = nt.n('ShaderNodeBsdfDiffuse')
    trans = nt.n('ShaderNodeBsdfTranslucent')
    col = nt.mixrgb((blotch, 'Fac'), (0.262, 0.224, 0.132, 1.0),
                    (0.395, 0.342, 0.208, 1.0))
    colg = nt.mixrgb((grain, 'Fac'), (col, 'Color'), (0.196, 0.166, 0.098, 1.0))
    col2 = nt.mixrgb((weave, 'Fac'), (colg, 'Color'),
                     (0.228, 0.194, 0.116, 1.0))
    nt.t.links.new(col2.outputs['Color'], diff.inputs['Color'])
    nt.t.links.new(col2.outputs['Color'], trans.inputs['Color'])
    # arceaux : deux bandes sombres qui trahissent la structure de la tente
    sep = nt.n('ShaderNodeSeparateXYZ')
    nt.link(tex, 'Object', sep, 'Vector')
    ax = nt.math('ABSOLUTE', (sep, 'X'))
    off = nt.math('SUBTRACT', (ax, 'Value'), 0.30)
    da = nt.math('ABSOLUTE', (off, 'Value'))
    pole = nt.ramp((da, 'Value'), [(0.007, (1, 1, 1, 1)), (0.016, (0, 0, 0, 1))])
    col3 = nt.mixrgb((pole, 'Color'), (col2, 'Color'), (0.030, 0.026, 0.018, 1.0))
    # fermeture eclair : une bande claire verticale, cote porte
    zo = nt.math('SUBTRACT', (sep, 'X'), 0.62)
    zd = nt.math('ABSOLUTE', (zo, 'Value'))
    zip_ = nt.ramp((zd, 'Value'), [(0.004, (1, 1, 1, 1)), (0.010, (0, 0, 0, 1))])
    col3 = nt.mixrgb((zip_, 'Color'), (col3, 'Color'), (0.105, 0.092, 0.062, 1.0))
    nt.t.links.new(col3.outputs['Color'], diff.inputs['Color'])
    nt.t.links.new(col3.outputs['Color'], trans.inputs['Color'])

    mix = nt.n('ShaderNodeMixShader')
    mix.inputs['Fac'].default_value = 0.62
    nt.t.links.new(diff.outputs['BSDF'], mix.inputs[1])
    nt.t.links.new(trans.outputs['BSDF'], mix.inputs[2])
    out = nt.n('ShaderNodeOutputMaterial')
    nt.t.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    return m


# ----------------------------------------------------------------------
# les trois decors
# ----------------------------------------------------------------------
def scene_rock():
    clear_stage()
    coll = bpy.context.scene.collection
    rock = terrain("Rock", 1.30, 260, 0.052, seed=3.7,
                   flat_at=(0.0, 0.0), flat_r=0.070, coll=coll)
    rock.data.materials.append(mat_granite())
    # arriere-plan : crete lointaine, totalement hors du plan net
    ridge = terrain("Ridge", 120.0, 110, 11.0, seed=19.0, z0=-13.0, octaves=4, coll=coll)
    ridge.location = (0.0, 42.0, 0.0)
    far = materials.plastic("M_FarRidge", (0.196, 0.238, 0.305, 1.0), 0.95)
    ridge.data.materials.append(far)
    sky((0.048, 0.135, 0.330), (0.520, 0.605, 0.700), (0.105, 0.110, 0.118),
        strength=1.6)
    sun("Sun", az=-58.0, elev=27.0, power=5.4, color=(1.0, 0.918, 0.808),
        angle_deg=0.75)
    return studio.make_camera("Cam", dist=0.52, az=36.0, elev=11.0, focal=72.0,
                              target=(0.004, 0.0, 0.004), fstop=5.0,
                              focus_shift=-0.020)


def scene_backpack():
    clear_stage()
    coll = bpy.context.scene.collection
    # l'enceinte pend par son mousqueton : bascule d'un bloc, un seul pivot
    piv = pivot_model(pitch=math.radians(-58.0), yaw=math.radians(14.0),
                      offset=(0.0, 0.0, 0.086))
    # centre du trou du mousqueton, calcule depuis le modele puis transporte
    Pc = Vector((0.0512, 0.0, 0.0408))
    w = Vector((math.sin(math.radians(55.0)), 0.0, math.cos(math.radians(55.0))))
    hole = piv.matrix_world @ (Pc + w * 0.0128)

    # panneau du sac : mur vertical froisse, derriere le sujet
    PY = hole.y + 0.150
    panel = terrain("Pack", 1.10, 170, 0.026, seed=8.3, z0=0.0, octaves=4, coll=coll)
    for v in panel.data.vertices:
        x, y, z = v.co
        v.co = Vector((x, PY - z, y * 0.78 + hole.z - 0.030))
    panel.data.update(); recalc(panel); smooth(panel, 60)
    panel.data.materials.append(mat_nylon("M_Pack", (0.0335, 0.0405, 0.0590, 1.0),
                                          rip_div=16.0, rip_str=0.20,
                                          rip_dist=0.00055))

    # sangle : boucle de cordon qui traverse reellement le mousqueton
    path = catmull([
        (hole.x - 0.090, PY - 0.012, hole.z + 0.190),
        (hole.x - 0.042, hole.y + 0.020, hole.z + 0.062),
        (hole.x - 0.016, hole.y + 0.001, hole.z + 0.004),
        (hole.x + 0.016, hole.y - 0.001, hole.z + 0.004),
        (hole.x + 0.042, hole.y + 0.020, hole.z + 0.062),
        (hole.x + 0.090, PY - 0.012, hole.z + 0.190),
    ], 72)
    band = sweep("PackStrap", path, rect_section(0.00075, 0.0046, 0.0004, 3), coll=coll)
    recalc(band); smooth(band, 40)
    band.data.materials.append(mat_nylon("M_PackStrap", (0.0120, 0.0150, 0.0245, 1.0),
                                         scale=2600.0, sheen=0.35))

    sky((0.118, 0.186, 0.325), (0.470, 0.520, 0.585), (0.140, 0.135, 0.120),
        strength=1.5)
    sun("Sun", az=-40.0, elev=34.0, power=4.6, color=(1.0, 0.938, 0.858),
        angle_deg=2.4)
    return studio.make_camera("Cam", dist=0.74, az=20.0, elev=6.0, focal=76.0,
                              target=(hole.x + 0.004, 0.0, hole.z - 0.062),
                              fstop=4.0, focus_shift=-0.030)


def scene_tent():
    clear_stage()
    coll = bpy.context.scene.collection
    floor = terrain("TentFloor", 1.60, 220, 0.0090, seed=5.5,
                    flat_at=(0.0, 0.0), flat_r=0.070, coll=coll)
    floor.data.materials.append(mat_nylon("M_TentFloor", (0.0395, 0.0350, 0.0270, 1.0),
                                          scale=2100.0, sheen=0.22,
                                          rip_div=26.0, rip_str=0.10,
                                          rip_dist=0.00030))
    # paroi : demi-tunnel autour de la scene, camera a l'interieur
    R, NU, NV = 0.74, 88, 50
    wv, wf = [], []
    for j in range(NV + 1):
        a = math.pi * 1.26 * (j / NV) - math.pi * 0.13
        for i in range(NU + 1):
            x = -2.40 + 4.80 * i / NU
            wr = noise.turbulence(Vector((x * 4.4, a * 2.6, 2.1)), 4, False) * 0.030
            r = R * (1.0 - 0.17 * math.sin(max(0.0, a))) - wr
            wv.append((x, r * math.cos(a), Z_GROUND + r * math.sin(a)))
    for j in range(NV):
        for i in range(NU):
            k = j * (NU + 1) + i
            wf.append((k, k + 1, k + NU + 2, k + NU + 1))
    wall = new_obj("TentWall", wv, wf, coll)
    recalc(wall); smooth(wall, 60)
    wall.data.materials.append(mat_tentwall())
    # le jour, dehors : deux sources placees au-dela de la toile
    # le jour vient d'au-dessus : toute la toile doit s'allumer, pas un secteur
    studio.make_area("Outside", 1.55, 8.0, 70.0, 2.40, 300.0,
                     (1.0, 0.968, 0.905), ratio=1.0, target=(0, 0, 0))
    studio.make_area("SideGlow", 1.30, -66.0, 22.0, 1.40, 150.0,
                     (0.90, 0.945, 1.0), ratio=1.0, target=(0, 0, 0))
    studio.make_area("Door", 1.05, 52.0, 7.0, 0.34, 7.0,
                     (1.0, 0.930, 0.845), ratio=1.6, target=(0, 0, 0))
    sky((0.038, 0.042, 0.048), (0.062, 0.066, 0.070), (0.026, 0.026, 0.028),
        strength=0.75)
    return studio.make_camera("Cam", dist=0.44, az=42.0, elev=8.0, focal=56.0,
                              target=(0.004, 0.0, 0.006), fstop=4.5,
                              focus_shift=-0.014)


BUILDERS = {"rock": scene_rock, "backpack": scene_backpack, "tent": scene_tent}


def build(which):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900   # fond 16:9
    sc.render.film_transparent = False
    sc.render.image_settings.color_mode = 'RGB'
    return BUILDERS[which]()
