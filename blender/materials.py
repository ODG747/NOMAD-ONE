# -*- coding: utf-8 -*-
"""
NOMAD ONE - Phase 2 : materiaux.

Principe : aucune surface uniforme. Chaque materiau porte au moins
  - une micro-rugosite procedurale (bump haute frequence)
  - une variation lente de rugosite (polissage inegal)
  - une usure sur les aretes convexes (Pointiness)
  - de la poussiere dans les creux concaves
Le caoutchouc ajoute des traces de doigts sur les faces tournees vers le haut.
"""
import bpy, math


# ----------------------------------------------------------------------
# petites aides
# ----------------------------------------------------------------------
def _mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m


class NT:
    """Enveloppe minimale autour d'un node_tree."""

    def __init__(self, tree):
        self.t = tree
        self.x = 0

    def n(self, kind, **kw):
        nd = self.t.nodes.new(kind)
        self.x += 190
        nd.location = (self.x, 0)
        for k, v in kw.items():
            if k == "op":
                nd.operation = v
            elif k == "blend":
                nd.blend_type = v
            elif k == "dim":
                nd.noise_dimensions = v
            elif hasattr(nd, k):
                setattr(nd, k, v)
        return nd

    def link(self, a, ai, b, bi):
        self.t.links.new(a.outputs[ai], b.inputs[bi])

    def val(self, nd, key, v):
        if key in nd.inputs:
            nd.inputs[key].default_value = v

    # -- briques reutilisables ------------------------------------------
    def math(self, op, a=None, b=None, clamp=False):
        nd = self.n('ShaderNodeMath', op=op, use_clamp=clamp)
        if isinstance(a, (int, float)):
            nd.inputs[0].default_value = a
        elif a is not None:
            self.t.links.new(a[0].outputs[a[1]], nd.inputs[0])
        if isinstance(b, (int, float)):
            nd.inputs[1].default_value = b
        elif b is not None:
            self.t.links.new(b[0].outputs[b[1]], nd.inputs[1])
        return nd

    def noise(self, coord, scale, detail=4.0, rough=0.5, dim='3D'):
        nd = self.n('ShaderNodeTexNoise', dim=dim)
        self.val(nd, 'Scale', scale)
        self.val(nd, 'Detail', detail)
        self.val(nd, 'Roughness', rough)
        if coord is not None:
            self.t.links.new(coord[0].outputs[coord[1]], nd.inputs['Vector'])
        return nd

    def ramp(self, src, stops, interp='LINEAR'):
        nd = self.n('ShaderNodeValToRGB')
        cr = nd.color_ramp
        cr.interpolation = interp
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        cr.elements[0].position, cr.elements[0].color = stops[0][0], stops[0][1]
        for pos, col in stops[1:]:
            cr.elements.new(pos).color = col
        if src is not None:
            self.t.links.new(src[0].outputs[src[1]], nd.inputs['Fac'])
        return nd

    def mixrgb(self, fac, c1, c2, blend='MIX'):
        nd = self.n('ShaderNodeMixRGB', blend=blend)
        if isinstance(fac, (int, float)):
            nd.inputs['Fac'].default_value = fac
        else:
            self.t.links.new(fac[0].outputs[fac[1]], nd.inputs['Fac'])
        for key, c in (('Color1', c1), ('Color2', c2)):
            if isinstance(c, tuple) and len(c) == 4 and isinstance(c[0], (int, float)):
                nd.inputs[key].default_value = c
            elif isinstance(c, (int, float)):
                nd.inputs[key].default_value = (c, c, c, 1.0)
            else:
                self.t.links.new(c[0].outputs[c[1]], nd.inputs[key])
        return nd

    def bump(self, height, strength, distance, normal=None):
        nd = self.n('ShaderNodeBump')
        nd.inputs['Strength'].default_value = strength
        nd.inputs['Distance'].default_value = distance
        self.t.links.new(height[0].outputs[height[1]], nd.inputs['Height'])
        if normal is not None:
            self.t.links.new(normal[0].outputs[normal[1]], nd.inputs['Normal'])
        return nd


def principled(nt, **kw):
    p = nt.n('ShaderNodeBsdfPrincipled')
    out = nt.n('ShaderNodeOutputMaterial')
    nt.link(p, 'BSDF', out, 'Surface')
    for k, v in kw.items():
        nt.val(p, k, v)
    return p


# ======================================================================
# 1. caoutchouc mat
# ======================================================================
def rubber(name="M_Rubber", base=(0.0170, 0.0225, 0.0680, 1.0), rough=0.815,
           wear=1.0, prints=1.0):
    m = _mat(name)
    nt = NT(m.node_tree)
    p = principled(nt, Metallic=0.0)
    tex = nt.n('ShaderNodeTexCoord')
    geo = nt.n('ShaderNodeNewGeometry')

    # --- micro-rugosite : deux octaves, echelle sub-millimetrique -----
    mic1 = nt.noise((tex, 'Object'), 5200.0, 4.0, 0.55)
    mic2 = nt.noise((tex, 'Object'), 21000.0, 2.0, 0.50)
    b2 = nt.bump((mic2, 'Fac'), 0.22, 0.00010)
    b1 = nt.bump((mic1, 'Fac'), 0.40, 0.00026, normal=(b2, 'Normal'))
    nt.link(b1, 'Normal', p, 'Normal')

    # --- usure des aretes convexes ------------------------------------
    wr = nt.ramp((geo, 'Pointiness'), [(0.515, (0, 0, 0, 1)), (0.585, (1, 1, 1, 1))])
    wmask = nt.noise((tex, 'Object'), 340.0, 3.0, 0.6)
    wmr = nt.ramp((wmask, 'Fac'), [(0.30, (0, 0, 0, 1)), (0.62, (1, 1, 1, 1))])
    wmul = nt.math('MULTIPLY', (wr, 'Color'), (wmr, 'Color'), clamp=True)
    wamt = nt.math('MULTIPLY', (wmul, 'Value'), 0.55 * wear, clamp=True)

    # --- poussiere dans les creux concaves ----------------------------
    dr = nt.ramp((geo, 'Pointiness'), [(0.400, (1, 1, 1, 1)), (0.487, (0, 0, 0, 1))])
    dmask = nt.noise((tex, 'Object'), 900.0, 4.0, 0.65)
    dmr = nt.ramp((dmask, 'Fac'), [(0.36, (0, 0, 0, 1)), (0.66, (1, 1, 1, 1))])
    dmul = nt.math('MULTIPLY', (dr, 'Color'), (dmr, 'Color'), clamp=True)
    damt = nt.math('MULTIPLY', (dmul, 'Value'), 0.50, clamp=True)

    # --- couleur : base -> usure (plus claire) -> poussiere (grise) ---
    c1 = nt.mixrgb((wamt, 'Value'), base, (0.062, 0.070, 0.115, 1.0))
    c2 = nt.mixrgb((damt, 'Value'), (c1, 'Color'), (0.105, 0.101, 0.092, 1.0))
    # inegalite lente du moulage : aucune plage de couleur parfaitement egale
    blot = nt.noise((tex, 'Object'), 24.0, 5.0, 0.62)
    blotf = nt.math('MULTIPLY', (blot, 'Fac'), 0.55, clamp=True)
    c3 = nt.mixrgb((blotf, 'Value'), (c2, 'Color'),
                   tuple(min(1.0, v * 1.34) for v in base[:3]) + (1.0,))
    nt.link(c3, 'Color', p, 'Base Color')

    # --- rugosite -----------------------------------------------------
    pol = nt.noise((tex, 'Object'), 195.0, 3.0, 0.5)          # polissage inegal
    polr = nt.ramp((pol, 'Fac'), [(0.30, (0, 0, 0, 1)), (0.70, (1, 1, 1, 1))])
    polv = nt.math('MULTIPLY_ADD', (polr, 'Color'), 0.085)
    polv.inputs[2].default_value = rough - 0.042

    # traces de doigts : taches lentes, uniquement vers le haut
    sep = nt.n('ShaderNodeSeparateXYZ')
    nt.link(geo, 'Normal', sep, 'Vector')
    upr = nt.ramp((sep, 'Z'), [(0.05, (0, 0, 0, 1)), (0.60, (1, 1, 1, 1))])
    fp = nt.noise((tex, 'Object'), 46.0, 7.0, 0.72)
    fpr = nt.ramp((fp, 'Fac'), [(0.470, (0, 0, 0, 1)), (0.610, (1, 1, 1, 1))])
    fpm = nt.math('MULTIPLY', (fpr, 'Color'), (upr, 'Color'), clamp=True)
    fpa = nt.math('MULTIPLY', (fpm, 'Value'), 0.170 * prints, clamp=True)
    r1 = nt.math('SUBTRACT', (polv, 'Value'), (fpa, 'Value'))       # gras -> plus lisse
    r2 = nt.math('MULTIPLY_ADD', (wamt, 'Value'), -0.190)           # arete polie
    r2.inputs[2].default_value = 0.0
    r3 = nt.math('ADD', (r1, 'Value'), (r2, 'Value'))
    r4 = nt.math('MULTIPLY_ADD', (damt, 'Value'), 0.130)            # poussiere -> mat
    r4.inputs[2].default_value = 0.0
    r5 = nt.math('ADD', (r3, 'Value'), (r4, 'Value'), clamp=True)
    nt.link(r5, 'Value', p, 'Roughness')
    nt.val(p, 'Specular IOR Level', 0.40)
    nt.val(p, 'IOR', 1.46)
    return m


# ======================================================================
# 2. grille perforee en metal brosse
# ======================================================================
def grille(name="M_Grille", pitch=0.0016, hole=0.00116,
           arc_len=0.17166, length=0.0960):
    """Trous en quinconce reellement traversants (alpha), avec chanfrein.
    La coque est solidifiee : les deux peaux partagent l'UV, donc les trous
    sont de vrais tubes qui laissent voir le chassis sombre au fond."""
    m = _mat(name)
    nt = NT(m.node_tree)
    p = principled(nt, Metallic=1.0)

    NX = max(1.0, round(arc_len / pitch))
    NY = max(1.0, round(length / (pitch * 0.8660254)))
    tex = nt.n('ShaderNodeTexCoord')
    mp = nt.n('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (NX, NY, 1.0)
    nt.link(tex, 'UV', mp, 'Vector')
    sep = nt.n('ShaderNodeSeparateXYZ')
    nt.link(mp, 'Vector', sep, 'Vector')

    # quinconce : une rangee sur deux decalee d'une demi-maille
    row = nt.math('FLOOR', (sep, 'Y'))
    odd = nt.math('MODULO', (row, 'Value'), 2.0)
    half = nt.math('MULTIPLY', (odd, 'Value'), 0.5)
    ush = nt.math('ADD', (sep, 'X'), (half, 'Value'))
    fu = nt.math('WRAP', (ush, 'Value'), 0.5)
    fu.inputs[2].default_value = -0.5
    fv0 = nt.math('WRAP', (sep, 'Y'), 0.5)
    fv0.inputs[2].default_value = -0.5
    fv = nt.math('MULTIPLY', (fv0, 'Value'), 1.1547005)   # maille hexagonale -> cercle
    comb = nt.n('ShaderNodeCombineXYZ')
    nt.link(fu, 'Value', comb, 'X')
    nt.link(fv, 'Value', comb, 'Y')
    dist = nt.n('ShaderNodeVectorMath', op='LENGTH')
    nt.link(comb, 'Vector', dist, 'Vector')

    hr = 0.5 * hole / pitch                                # rayon en mailles
    alpha = nt.ramp((dist, 'Value'),
                    [(max(0.0, hr - 0.030), (0, 0, 0, 1)), (hr + 0.030, (1, 1, 1, 1))])
    nt.link(alpha, 'Color', p, 'Alpha')

    # chanfrein sur le bord du trou
    chf = nt.ramp((dist, 'Value'),
                  [(hr, (0, 0, 0, 1)), (hr + 0.20, (1, 1, 1, 1))], interp='EASE')

    # brossage circonferentiel : bruit tres etire le long de U
    bmap = nt.n('ShaderNodeMapping')
    bmap.inputs['Scale'].default_value = (0.9, 240.0, 1.0)
    nt.link(tex, 'UV', bmap, 'Vector')
    br = nt.noise((bmap, 'Vector'), 42.0, 5.0, 0.62, dim='2D')
    smap = nt.n('ShaderNodeMapping')
    smap.inputs['Scale'].default_value = (2.2, 1500.0, 1.0)
    nt.link(tex, 'UV', smap, 'Vector')
    sc = nt.noise((smap, 'Vector'), 120.0, 3.0, 0.5, dim='2D')

    bb = nt.bump((br, 'Fac'), 0.16, 0.00008)
    bs = nt.bump((sc, 'Fac'), 0.10, 0.00004, normal=(bb, 'Normal'))
    bc = nt.bump((chf, 'Color'), 0.28, 0.00012, normal=(bs, 'Normal'))
    nt.link(bc, 'Normal', p, 'Normal')

    # couleur : aluminium anodise sombre, legerement sali dans les trous
    col = nt.mixrgb((br, 'Fac'), (0.132, 0.143, 0.166, 1.0), (0.196, 0.208, 0.234, 1.0))
    nt.link(col, 'Color', p, 'Base Color')
    rg = nt.mixrgb((br, 'Fac'), (0.26, 0.26, 0.26, 1), (0.40, 0.40, 0.40, 1))
    rg2 = nt.mixrgb((sc, 'Fac'), (rg, 'Color'), (0.30, 0.30, 0.30, 1))
    nt.link(rg2, 'Color', p, 'Roughness')
    nt.val(p, 'Anisotropic', 0.62)
    tg = nt.n('ShaderNodeTangent')
    tg.direction_type = 'UV_MAP'
    nt.link(tg, 'Tangent', p, 'Tangent')
    return m


# ======================================================================
# 3. metal brosse (mousqueton, coque du port)
# ======================================================================
def metal(name="M_Metal", base=(0.512, 0.532, 0.566, 1.0), rough=0.255, aniso=0.55):
    m = _mat(name)
    nt = NT(m.node_tree)
    p = principled(nt, Metallic=1.0)
    tex = nt.n('ShaderNodeTexCoord')
    geo = nt.n('ShaderNodeNewGeometry')

    stretch = nt.n('ShaderNodeMapping')
    stretch.inputs['Scale'].default_value = (1.0, 60.0, 60.0)
    nt.link(tex, 'Object', stretch, 'Vector')
    br = nt.noise((stretch, 'Vector'), 260.0, 5.0, 0.6)
    fine = nt.n('ShaderNodeMapping')
    fine.inputs['Scale'].default_value = (1.0, 300.0, 300.0)
    nt.link(tex, 'Object', fine, 'Vector')
    sc = nt.noise((fine, 'Vector'), 900.0, 4.0, 0.55)

    b1 = nt.bump((br, 'Fac'), 0.20, 0.00012)
    b2 = nt.bump((sc, 'Fac'), 0.13, 0.00005, normal=(b1, 'Normal'))
    nt.link(b2, 'Normal', p, 'Normal')

    wr = nt.ramp((geo, 'Pointiness'), [(0.520, (0, 0, 0, 1)), (0.600, (1, 1, 1, 1))])
    col = nt.mixrgb((wr, 'Color'), base, (0.640, 0.655, 0.680, 1.0))
    nt.link(col, 'Color', p, 'Base Color')

    r0 = nt.ramp((br, 'Fac'), [(0.25, (rough - 0.055,) * 3 + (1,)),
                               (0.75, (rough + 0.075,) * 3 + (1,))])
    r1 = nt.mixrgb((sc, 'Fac'), (r0, 'Color'), (rough + 0.02,) * 3 + (1,))
    nt.link(r1, 'Color', p, 'Roughness')
    nt.val(p, 'Anisotropic', aniso)
    tg = nt.n('ShaderNodeTangent')
    tg.direction_type = 'RADIAL'
    tg.axis = 'Z'
    nt.link(tg, 'Tangent', p, 'Tangent')
    return m


# ======================================================================
# 4. sangle en tissu tisse
# ======================================================================
def fabric(name="M_Fabric", base=(0.0195, 0.0250, 0.0585, 1.0), thread=0.00072):
    """Trame armure toile : chaine et trame alternees, relief reel."""
    m = _mat(name)
    nt = NT(m.node_tree)
    p = principled(nt, Metallic=0.0)
    tex = nt.n('ShaderNodeTexCoord')
    mp = nt.n('ShaderNodeMapping')
    k = 1.0 / thread
    mp.inputs['Scale'].default_value = (k, k, 1.0)
    nt.link(tex, 'UV', mp, 'Vector')
    sep = nt.n('ShaderNodeSeparateXYZ')
    nt.link(mp, 'Vector', sep, 'Vector')

    # profil arrondi de chaque fil
    def thread_profile(chan):
        w = nt.math('WRAP', (sep, chan), 0.5)
        w.inputs[2].default_value = -0.5
        a = nt.math('ABSOLUTE', (w, 'Value'))
        s = nt.math('MULTIPLY', (a, 'Value'), 2.0)
        c = nt.math('SUBTRACT', 1.0, (s, 'Value'), clamp=True)
        return nt.math('POWER', (c, 'Value'), 0.55)

    warp = thread_profile('X')
    weft = thread_profile('Y')
    # armure toile : dessus/dessous alterne
    fx = nt.math('FLOOR', (sep, 'X'))
    fy = nt.math('FLOOR', (sep, 'Y'))
    fs = nt.math('ADD', (fx, 'Value'), (fy, 'Value'))
    chk = nt.math('MODULO', (fs, 'Value'), 2.0)
    hi = nt.math('MULTIPLY_ADD', (warp, 'Value'), 0.62)
    hi.inputs[2].default_value = 0.0
    lo = nt.math('MULTIPLY_ADD', (weft, 'Value'), 0.62)
    lo.inputs[2].default_value = 0.0
    top = nt.mixrgb((chk, 'Value'), (hi, 'Value'), (lo, 'Value'))
    both = nt.math('MAXIMUM', (warp, 'Value'), (weft, 'Value'))
    h = nt.math('ADD', (top, 'Color'), (both, 'Value'), clamp=True)

    fuzz = nt.noise((tex, 'Object'), 9000.0, 3.0, 0.6)
    bf = nt.bump((fuzz, 'Fac'), 0.28, 0.00007)
    bw = nt.bump((h, 'Value'), 1.0, 0.00030, normal=(bf, 'Normal'))
    nt.link(bw, 'Normal', p, 'Normal')

    shade = nt.mixrgb((h, 'Value'), (0.0088, 0.0110, 0.0250, 1.0), base)
    dye = nt.noise((tex, 'Object'), 130.0, 4.0, 0.55)
    dyef = nt.math('MULTIPLY', (dye, 'Fac'), 0.35, clamp=True)
    col = nt.mixrgb((dyef, 'Value'), (shade, 'Color'), (0.0300, 0.0365, 0.0790, 1.0))
    nt.link(col, 'Color', p, 'Base Color')

    rg = nt.mixrgb((h, 'Value'), (0.93, 0.93, 0.93, 1), (0.79, 0.79, 0.79, 1))
    nt.link(rg, 'Color', p, 'Roughness')
    nt.val(p, 'Sheen Weight', 0.42)
    nt.val(p, 'Sheen Roughness', 0.30)
    nt.val(p, 'Specular IOR Level', 0.30)
    return m


# ======================================================================
# 5. materiaux simples
# ======================================================================
def plastic(name, base, rough=0.42, metallic=0.0, micro=6000.0):
    m = _mat(name)
    nt = NT(m.node_tree)
    p = principled(nt, Metallic=metallic)
    tex = nt.n('ShaderNodeTexCoord')
    mic = nt.noise((tex, 'Object'), micro, 3.0, 0.5)
    nt.link(nt.bump((mic, 'Fac'), 0.20, 0.00010), 'Normal', p, 'Normal')
    var = nt.noise((tex, 'Object'), 220.0, 3.0, 0.5)
    rg = nt.ramp((var, 'Fac'), [(0.28, (rough - 0.05,) * 3 + (1,)),
                                (0.72, (rough + 0.05,) * 3 + (1,))])
    nt.link(rg, 'Color', p, 'Roughness')
    nt.val(p, 'Base Color', base)
    return m


def led(name="M_LED", color=(0.010, 0.760, 0.600, 1.0), strength=14.0):
    m = _mat(name)
    nt = NT(m.node_tree)
    p = principled(nt, Metallic=0.0, Roughness=0.09, IOR=1.52)
    nt.val(p, 'Base Color', (0.03, 0.10, 0.09, 1.0))
    nt.val(p, 'Emission Color', color)
    nt.val(p, 'Emission Strength', strength)
    return m


def cone(name="M_Cone"):
    m = _mat(name)
    nt = NT(m.node_tree)
    p = principled(nt, Metallic=0.0, Roughness=0.90)
    tex = nt.n('ShaderNodeTexCoord')
    fib = nt.noise((tex, 'Object'), 2600.0, 5.0, 0.68)
    nt.link(nt.bump((fib, 'Fac'), 0.42, 0.00018), 'Normal', p, 'Normal')
    col = nt.mixrgb((fib, 'Fac'), (0.0130, 0.0140, 0.0180, 1.0),
                    (0.0330, 0.0345, 0.0400, 1.0))
    nt.link(col, 'Color', p, 'Base Color')
    return m


# ======================================================================
def assign(ob_name, mat, slot_clear=True):
    ob = bpy.data.objects.get(ob_name)
    if not ob:
        return None
    if slot_clear:
        ob.data.materials.clear()
    ob.data.materials.append(mat)
    return ob


def build_all():
    rub = rubber("M_Rubber")
    rub_in = rubber("M_Rubber_Inner", base=(0.0021, 0.0025, 0.0052, 1.0),
                    rough=0.88, wear=0.25, prints=0.0)
    rub_btn = rubber("M_Rubber_Btn", base=(0.0245, 0.0310, 0.0810, 1.0),
                     rough=0.60, wear=1.6, prints=2.0)
    gri = grille("M_Grille")
    met = metal("M_Metal")
    met_d = metal("M_Metal_Dark", base=(0.290, 0.302, 0.325, 1.0), rough=0.30, aniso=0.35)
    fab = fabric("M_Fabric")
    blk = plastic("M_Black", (0.0075, 0.0080, 0.0098, 1.0), 0.40)
    gold = plastic("M_Gold", (0.560, 0.420, 0.150, 1.0), 0.28, metallic=1.0)
    cel = plastic("M_Cell", (0.0330, 0.1050, 0.1260, 1.0), 0.35, metallic=0.85)
    pcb = plastic("M_PCB", (0.0125, 0.0470, 0.0250, 1.0), 0.46)
    lamp = led()
    cn = cone()

    pairs = [("Body_Core", rub_in), ("Grille", gri), ("Base_Pad", rub),
             ("Cap_L", rub), ("Cap_R", rub), ("Button_A", rub_btn),
             ("Button_B", rub_btn), ("Port_USBC", met_d), ("Port_Tongue", blk),
             ("LED", lamp), ("Strap", fab), ("Carabiner", met),
             ("Driver", cn), ("Battery", cel), ("PCB", pcb)]
    done = []
    for nm, mt in pairs:
        if assign(nm, mt):
            done.append(nm)
    return done
