# -*- coding: utf-8 -*-
"""
NOMAD ONE - Phase 2 : plateau de prise de vue produit.

Reproduit un vrai shooting :
  - key light   : grande softbox de trois quarts (haut-gauche-avant)
  - fill        : reflecteur froid de l'autre cote, faible
  - rim         : bande etroite derriere, detache la silhouette
  - environment : degrade de studio (murs sombres, plafond clair)
  - sol         : shadow catcher -> ombre conservee dans l'alpha
Camera longue focale (100 mm) a 0.80 m : perspective compressee de catalogue.
"""
import bpy, math
from mathutils import Matrix, Vector

RES_X, RES_Y = 1600, 1200
TARGET = Vector((0.004, 0.0, 0.006))
Z_GROUND = -0.0303


# ----------------------------------------------------------------------
def look_at(pos, target):
    pos, target = Vector(pos), Vector(target)
    z = (pos - target).normalized()
    up = Vector((0.0, 0.0, 1.0))
    if abs(z.dot(up)) > 0.999:
        up = Vector((0.0, 1.0, 0.0))
    x = up.cross(z).normalized()
    y = z.cross(x)
    return Matrix(((x.x, y.x, z.x, pos.x),
                   (x.y, y.y, z.y, pos.y),
                   (x.z, y.z, z.z, pos.z),
                   (0.0, 0.0, 0.0, 1.0)))


def polar(dist, az_deg, elev_deg, target=TARGET):
    """az mesure depuis -Y (face) vers +X ; elev depuis l'horizontale."""
    a, e = math.radians(az_deg), math.radians(elev_deg)
    return Vector(target) + Vector((dist * math.sin(a) * math.cos(e),
                                    -dist * math.cos(a) * math.cos(e),
                                    dist * math.sin(e)))


def purge(*names):
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)


# ----------------------------------------------------------------------
def make_camera(name="Cam", dist=0.80, az=40.0, elev=13.0, focal=100.0,
                target=TARGET, fstop=9.0, focus_shift=-0.030):
    purge(name)
    cd = bpy.data.cameras.new(name)
    cd.lens = focal
    cd.sensor_width = 36.0
    cd.clip_start = 0.005
    cd.clip_end = 50.0
    cam = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(cam)
    pos = polar(dist, az, elev, target)
    cam.matrix_world = look_at(pos, target)
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    # nettete sur l'avant de l'objet : on rapproche le plan de mise au point
    cd.dof.focus_distance = max(0.05, (pos - Vector(target)).length + focus_shift)
    cd.dof.aperture_blades = 7
    bpy.context.scene.camera = cam
    return cam


def make_area(name, dist, az, elev, size, power, color, ratio=1.0, spread=180.0,
              target=TARGET):
    purge(name)
    ld = bpy.data.lights.new(name, 'AREA')
    ld.shape = 'RECTANGLE'
    ld.size = size
    ld.size_y = size * ratio
    ld.energy = power
    ld.color = color
    ld.spread = math.radians(spread)
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = look_at(polar(dist, az, elev, target), target)
    return ob


LIGHT_SCALE = 1.0     # facteur global d'exposition du plateau


def studio_lights(scale=None):
    """Cle en softbox de trois quarts, fill froid, rim etroite, nappe haute.
    Puissances calibrees pour un sujet de 15 cm a ~0.7 m."""
    k = LIGHT_SCALE if scale is None else scale
    key = make_area("Key_Softbox", 0.66, -42.0, 35.0, 0.60, 7.8 * k,
                    (1.0, 0.970, 0.934), ratio=1.30)
    fill = make_area("Fill_Cool", 0.62, 68.0, 8.0, 0.58, 2.30 * k,
                     (0.735, 0.845, 1.0), ratio=1.6)
    rim = make_area("Rim_Strip", 0.55, 152.0, 26.0, 0.44, 4.6 * k,
                    (0.890, 0.962, 1.0), ratio=0.10)
    top = make_area("Top_Sweep", 0.90, 10.0, 78.0, 1.10, 0.85 * k,
                    (0.960, 0.972, 1.0), ratio=0.75)
    return key, fill, rim, top


# ----------------------------------------------------------------------
def world_studio(strength=0.20):
    """Environnement de studio procedural : sol sombre, plafond clair,
    une bande laterale plus vive qui se lit dans les reflets du metal."""
    w = bpy.data.worlds.get("Studio") or bpy.data.worlds.new("Studio")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    n = nt.nodes.new
    tex = n('ShaderNodeTexCoord')
    sep = n('ShaderNodeSeparateXYZ')
    # hauteur -> degrade
    ramp = n('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'EASE'
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (0.012, 0.014, 0.022, 1)
    ramp.color_ramp.elements[1].position = 0.92
    ramp.color_ramp.elements[1].color = (0.150, 0.166, 0.205, 1)
    m = ramp.color_ramp.elements.new(0.62)
    m.color = (0.045, 0.052, 0.070, 1)
    # bande laterale (le "mur" eclaire du studio)
    band = n('ShaderNodeTexGradient')
    bmap = n('ShaderNodeMapping')
    bmap.inputs['Rotation'].default_value = (0.0, 0.0, math.radians(-58.0))
    bramp = n('ShaderNodeValToRGB')
    bramp.color_ramp.elements[0].position = 0.46
    bramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    bramp.color_ramp.elements[1].position = 0.72
    bramp.color_ramp.elements[1].color = (0.34, 0.38, 0.45, 1)
    add = n('ShaderNodeMixRGB')
    add.blend_type = 'ADD'
    add.inputs['Fac'].default_value = 1.0
    bg = n('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = strength
    out = n('ShaderNodeOutputWorld')
    L = nt.links.new
    L(tex.outputs['Generated'], sep.inputs['Vector'])
    L(sep.outputs['Z'], ramp.inputs['Fac'])
    L(tex.outputs['Generated'], bmap.inputs['Vector'])
    L(bmap.outputs['Vector'], band.inputs['Vector'])
    L(band.outputs['Fac'], bramp.inputs['Fac'])
    L(ramp.outputs['Color'], add.inputs['Color1'])
    L(bramp.outputs['Color'], add.inputs['Color2'])
    L(add.outputs['Color'], bg.inputs['Color'])
    L(bg.outputs['Background'], out.inputs['Surface'])
    return w


def ground(shadow_catcher=True, size=3.0):
    purge("Ground")
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0.0, 0.0, Z_GROUND))
    g = bpy.context.object
    g.name = "Ground"
    mat = bpy.data.materials.get("M_Ground") or bpy.data.materials.new("M_Ground")
    mat.use_nodes = True
    p = mat.node_tree.nodes.get("Principled BSDF")
    if p:
        p.inputs['Base Color'].default_value = (0.055, 0.058, 0.068, 1)
        p.inputs['Roughness'].default_value = 0.34
        if 'Specular IOR Level' in p.inputs:
            p.inputs['Specular IOR Level'].default_value = 0.45
    g.data.materials.clear()
    g.data.materials.append(mat)
    g.is_shadow_catcher = shadow_catcher
    g.visible_diffuse = not shadow_catcher
    return g


# ----------------------------------------------------------------------
def setup_render(engine='CYCLES', samples=512, res=(RES_X, RES_Y),
                 transparent=True, denoise=True, gpu=True):
    sc = bpy.context.scene
    sc.render.engine = engine
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    sc.render.image_settings.color_depth = '8'
    sc.render.image_settings.compression = 15
    sc.render.filter_size = 1.35

    # tone mapping filmique
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium Contrast'
    except Exception:
        try:
            sc.view_settings.look = 'Medium Contrast'
        except Exception:
            pass
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0

    if engine == 'CYCLES':
        cy = sc.cycles

        def st(attr, v):
            if hasattr(cy, attr):
                try:
                    setattr(cy, attr, v)
                except Exception:
                    pass

        st('feature_set', 'SUPPORTED')
        st('device', 'GPU' if gpu else 'CPU')
        st('samples', samples)
        st('use_adaptive_sampling', True)
        st('adaptive_threshold', 0.006)
        st('adaptive_min_samples', 0)
        st('use_denoising', denoise)
        st('denoiser', 'OPENIMAGEDENOISE')
        st('denoising_input_passes', 'RGB_ALBEDO_NORMAL')
        st('denoising_prefilter', 'ACCURATE')
        st('denoising_quality', 'HIGH')
        st('max_bounces', 12)
        st('diffuse_bounces', 4)
        st('glossy_bounces', 8)
        st('transmission_bounces', 8)
        st('transparent_max_bounces', 16)
        st('caustics_reflective', True)
        st('caustics_refractive', False)
        st('blur_glossy', 0.6)
        st('use_light_tree', True)
        st('sample_clamp_indirect', 8.0)
        st('film_exposure', 1.0)
        st('use_fast_gi', False)
        st('use_auto_tile', True)
        st('tile_size', 2048)
        enable_gpu()
    return sc


def enable_gpu():
    """Active HIP (Radeon) dans les preferences Cycles."""
    prefs = bpy.context.preferences.addons.get("cycles")
    if not prefs:
        return "cycles addon absent"
    cp = prefs.preferences
    chosen = None
    for t in ("HIP", "OPTIX", "CUDA", "ONEAPI", "METAL"):
        try:
            if cp.get_devices_for_type(t):
                cp.compute_device_type = t
                chosen = t
                break
        except Exception:
            continue
    if not chosen:
        return "aucun GPU"
    cp.get_devices()
    for d in cp.devices:
        d.use = (d.type == chosen)
    return chosen


def build_stage(transparent=True):
    world_studio()
    studio_lights()
    ground(shadow_catcher=transparent)
    return make_camera()
