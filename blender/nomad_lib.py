# -*- coding: utf-8 -*-
"""
NOMAD ONE - bibliotheque de construction geometrique.
Tout est en metres, a l'echelle reelle (enceinte de 15 cm).
Axe long = X. Haut = +Z. Profondeur = Y.
Convention angulaire des lathes : point(x, r, th) = (x, r*sin(th), r*cos(th))
donc th = 0 -> sommet (+Z), th = pi -> dessous (-Z).
"""
import bpy, bmesh, math
from mathutils import Vector

TAU = math.pi * 2.0


# ----------------------------------------------------------------------
# creation d'objets
# ----------------------------------------------------------------------
def new_obj(name, verts, faces, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate(verbose=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.collection).objects.link(ob)
    return ob


def lathe(name, profile, seg=192, th0=0.0, th1=TAU, uv=False, coll=None):
    """Revolution d'un profil [(x, r), ...] autour de l'axe X.

    th0/th1 en radians. Arc complet -> surface refermee.
    Un point de profil de rayon nul devient un pole unique.
    uv=True cree une UV map (u = angle normalise, v = x normalise).
    """
    full = (th1 - th0) >= TAU - 1e-6
    ncol = seg if full else seg + 1
    dth = (th1 - th0) / seg

    verts, rows = [], []
    for (x, r) in profile:
        if r <= 1e-9:
            verts.append((x, 0.0, 0.0))
            rows.append(('pole', len(verts) - 1))
        else:
            start = len(verts)
            for c in range(ncol):
                th = th0 + dth * c
                verts.append((x, r * math.sin(th), r * math.cos(th)))
            rows.append(('ring', start))

    xs = [p[0] for p in profile]
    x0, x1 = min(xs), max(xs)
    xspan = (x1 - x0) or 1.0

    def ridx(start, c):
        return start + (c % ncol if full else c)

    faces, uvs = [], []
    for i in range(len(profile) - 1):
        ka, ia = rows[i]
        kb, ib = rows[i + 1]
        for c in range(seg):
            if ka == 'pole' and kb == 'ring':
                f = (ia, ridx(ib, c + 1), ridx(ib, c))
            elif ka == 'ring' and kb == 'pole':
                f = (ridx(ia, c), ridx(ia, c + 1), ib)
            elif ka == 'ring' and kb == 'ring':
                f = (ridx(ia, c), ridx(ia, c + 1), ridx(ib, c + 1), ridx(ib, c))
            else:
                continue
            faces.append(f)
            if uv:
                u0, u1 = c / seg, (c + 1) / seg
                va = (profile[i][0] - x0) / xspan
                vb = (profile[i + 1][0] - x0) / xspan
                if len(f) == 3:
                    if ka == 'pole':
                        uvs.append([((u0 + u1) / 2, va), (u1, vb), (u0, vb)])
                    else:
                        uvs.append([(u0, va), (u1, va), ((u0 + u1) / 2, vb)])
                else:
                    uvs.append([(u0, va), (u1, va), (u1, vb), (u0, vb)])

    ob = new_obj(name, verts, faces, coll)
    if uv:
        me = ob.data
        lay = me.uv_layers.new(name="UVMap")
        for pi, poly in enumerate(me.polygons):
            pair = uvs[pi]
            for k in range(poly.loop_total):
                lay.data[poly.loop_start + k].uv = pair[k]
    return ob


# ----------------------------------------------------------------------
# balayages (sangle, mousqueton, cable)
# ----------------------------------------------------------------------
def _frames(pts, closed):
    """Reperes a rotation minimale le long d'une polyligne."""
    n = len(pts)
    tans = []
    for i in range(n):
        if closed:
            a, b = pts[(i - 1) % n], pts[(i + 1) % n]
        else:
            a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        t = Vector(b) - Vector(a)
        if t.length < 1e-9:
            t = Vector((1.0, 0.0, 0.0))
        tans.append(t.normalized())
    up = Vector((0.0, 0.0, 1.0))
    if abs(tans[0].dot(up)) > 0.95:
        up = Vector((1.0, 0.0, 0.0))
    nrm = (up - tans[0] * up.dot(tans[0])).normalized()
    frames = []
    for i, t in enumerate(tans):
        if i:
            nrm = nrm - t * nrm.dot(t)
            nrm = nrm.normalized() if nrm.length > 1e-9 else t.orthogonal().normalized()
        frames.append((t, nrm, t.cross(nrm).normalized()))
    return frames


def sweep(name, pts, section, closed=False, coll=None, uv=False):
    """Balaye une section 2D [(a, b), ...] le long de pts.
    uv=True : u = abscisse curviligne (metres), v = position dans la section."""
    fr = _frames(pts, closed)
    m = len(section)
    verts = []
    for i, p in enumerate(pts):
        t, nv, bv = fr[i]
        P = Vector(p)
        for (a, b) in section:
            verts.append(tuple(P + nv * a + bv * b))
    faces = []
    rng = range(len(pts)) if closed else range(len(pts) - 1)
    for i in rng:
        j = (i + 1) % len(pts)
        for k in range(m):
            k2 = (k + 1) % m
            faces.append((i * m + k, i * m + k2, j * m + k2, j * m + k))
    if not closed:
        faces.append(tuple(range(m - 1, -1, -1)))
        base = (len(pts) - 1) * m
        faces.append(tuple(base + k for k in range(m)))
    ob = new_obj(name, verts, faces, coll)
    if uv:
        arc = [0.0]
        for i in range(1, len(pts)):
            arc.append(arc[-1] + (Vector(pts[i]) - Vector(pts[i - 1])).length)
        per = [0.0]
        for k in range(1, m + 1):
            a0, b0 = section[k - 1]
            a1, b1 = section[k % m]
            per.append(per[-1] + math.hypot(a1 - a0, b1 - b0))
        lay = ob.data.uv_layers.new(name="UVMap")
        for poly in ob.data.polygons:
            for li in poly.loop_indices:
                vi = ob.data.loops[li].vertex_index
                i, k = divmod(vi, m)
                lay.data[li].uv = (arc[min(i, len(arc) - 1)], per[k])
    return ob


def circle_section(r, n=14):
    return [(r * math.cos(TAU * i / n), r * math.sin(TAU * i / n)) for i in range(n)]


def rect_section(ha, hb, r=0.0, n=3):
    """Rectangle 2ha x 2hb a coins arrondis de rayon r."""
    if r <= 1e-6:
        return [(-ha, -hb), (ha, -hb), (ha, hb), (-ha, hb)]
    pts, ia, ib = [], ha - r, hb - r
    for (cx, cy, a0) in ((ia, -ib, -math.pi / 2), (ia, ib, 0.0),
                         (-ia, ib, math.pi / 2), (-ia, -ib, math.pi)):
        for i in range(n + 1):
            a = a0 + (math.pi / 2) * i / n
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def arc_pts(center, radius, plane, a0, a1, n, squash=1.0):
    """Arc dans le plan defini par deux axes, ex. plane=('y','z')."""
    ax = {'x': Vector((1.0, 0, 0)), 'y': Vector((0, 1.0, 0)), 'z': Vector((0, 0, 1.0))}
    u, v = ax[plane[0]], ax[plane[1]]
    C = Vector(center)
    out = []
    for i in range(n):
        a = a0 + (a1 - a0) * (i / (n - 1) if n > 1 else 0.0)
        out.append(tuple(C + u * (radius * math.cos(a)) + v * (radius * squash * math.sin(a))))
    return out


def catmull(pts, n):
    """Echantillonne une spline de Catmull-Rom ouverte."""
    P = [Vector(p) for p in pts]
    P = [P[0] + (P[0] - P[1])] + P + [P[-1] + (P[-1] - P[-2])]
    out = []
    segs = len(P) - 3
    for i in range(n):
        u = i / (n - 1) * segs
        k = min(int(u), segs - 1)
        t = u - k
        p0, p1, p2, p3 = P[k], P[k + 1], P[k + 2], P[k + 3]
        out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t +
                                (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t +
                                (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)))
    return out


# ----------------------------------------------------------------------
# deformations
# ----------------------------------------------------------------------
def scale_z(ob, k):
    for v in ob.data.vertices:
        v.co.z *= k


def flatten_bottom(ob, z):
    """Rabat la face inferieure : cree le meplat."""
    for v in ob.data.vertices:
        if v.co.z < z:
            v.co.z = z


def translate(ob, d):
    d = Vector(d)
    for v in ob.data.vertices:
        v.co += d


# ----------------------------------------------------------------------
# modificateurs / finition
# ----------------------------------------------------------------------
def bevel(ob, width=0.0004, seg=3, angle=32.0, harden=False):
    m = ob.modifiers.new("Bevel", 'BEVEL')
    m.width = width
    m.segments = seg
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    m.harden_normals = harden
    m.use_clamp_overlap = True
    m.miter_outer = 'MITER_ARC'
    return m


def solidify(ob, thickness, offset=-1.0):
    m = ob.modifiers.new("Solidify", 'SOLIDIFY')
    m.thickness = thickness
    m.offset = offset
    m.use_even_offset = True
    m.use_quality_normals = True
    return m


def smooth(ob, angle=40.0, flat_pred=None):
    """Lissage par angle, calcule directement sur le maillage (aretes vives
    marquees a la main) : pas de modificateur, pas de normales custom, donc
    aucun risque de striage sur les surfaces courbes.
    flat_pred(polygon) -> True force une face en ombrage plat."""
    me = ob.data
    if me.has_custom_normals:
        try:
            me.attributes.remove(me.attributes["custom_normal"])
        except Exception:
            pass
    lim = math.radians(angle)
    bm = bmesh.new()
    bm.from_mesh(me)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        e.smooth = (len(e.link_faces) != 2) or (e.calc_face_angle(0.0) <= lim)
    bm.to_mesh(me)
    bm.free()
    if flat_pred is not None:
        for poly in me.polygons:
            if flat_pred(poly):
                poly.use_smooth = False
    me.update()
    return ob


def bounds(name):
    ob = bpy.data.objects[name]
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    vs = [ob.matrix_world @ v.co for v in me.vertices]
    b = {'x': (min(v.x for v in vs), max(v.x for v in vs)),
         'y': (min(v.y for v in vs), max(v.y for v in vs)),
         'z': (min(v.z for v in vs), max(v.z for v in vs)),
         'verts': len(me.vertices), 'faces': len(me.polygons)}
    ev.to_mesh_clear()
    return b


def overlap(a, b, axis='x'):
    ba, bb = bounds(a), bounds(b)
    return min(ba[axis][1], bb[axis][1]) - max(ba[axis][0], bb[axis][0])


# ----------------------------------------------------------------------
# normales
# ----------------------------------------------------------------------
def recalc(ob):
    """Recalcule les normales vers l'exterieur (maillage ferme)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def flip(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def orient_radial(ob, axis='x'):
    """Oriente une coque ouverte : normales vers l'exterieur de l'axe donne."""
    me = ob.data
    me.update()
    idx = {'x': 0, 'y': 1, 'z': 2}[axis]
    votes = 0.0
    for p in me.polygons:
        c = p.center
        rad = Vector(c)
        rad[idx] = 0.0
        if rad.length < 1e-7:
            rad = Vector((0.0, 0.0, 0.0))
            rad[idx] = 1.0 if c[idx] >= 0 else -1.0
        votes += p.normal.dot(rad.normalized()) * p.area
    if votes < 0:
        flip(ob)
    return ob
