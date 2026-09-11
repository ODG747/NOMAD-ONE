# -*- coding: utf-8 -*-
"""
NOMAD ONE - Phase 3 : production des rendus.

Utilisable dans Blender interactif ou, mieux, en tache de fond :
    blender --background --python render_jobs.py -- --job turntable
    blender --background --python render_jobs.py -- --job exploded
    blender --background --python render_jobs.py -- --job slide5

La scene est entierement reconstruite depuis les scripts (5 s) : aucun
fichier .blend n'est necessaire et le resultat est reproductible.
"""
import bpy, sys, os, math, importlib
from mathutils import Vector

DIR = os.path.dirname(os.path.abspath(__file__))
if DIR not in sys.path:
    sys.path.insert(0, DIR)
OUT = os.path.join(DIR, "renders")

SAMPLES = 900
RES = (1600, 1200)
THRESH = 0.0035

PARTS = ["Body_Core", "Grille", "Base_Pad", "Cap_L", "Cap_R", "Port_USBC",
         "Port_Tongue", "LED", "Button_A", "Button_B", "Strap", "Carabiner",
         "Driver", "Battery", "PCB"]

# ecartement de la vue eclatee, en metres (ajuste ensuite pour tenir dans le cadre)
EXPLODE = {
    "Body_Core":   (0.000,  0.000,  0.000),
    "Cap_L":       (-0.038, 0.000,  0.002),
    "Cap_R":       (0.040,  0.000,  0.002),
    "Port_USBC":   (0.062,  0.000,  0.002),
    "Port_Tongue": (0.070,  0.000,  0.002),
    "LED":         (0.052, -0.006,  0.002),
    "Grille":      (0.000,  0.000,  0.034),
    "Button_A":    (-0.006, 0.000,  0.048),
    "Button_B":    (0.006,  0.000,  0.048),
    "Strap":       (0.014,  0.014,  0.040),
    "Carabiner":   (0.026,  0.024,  0.046),
    "Base_Pad":    (0.000,  0.000, -0.032),
    "Driver":      (-0.014, -0.046, 0.010),
    "Battery":     (0.006, -0.026, -0.024),
    "PCB":         (0.000,  0.024, -0.040),
}


# ----------------------------------------------------------------------
def build_scene(transparent=True):
    import nomad_lib, studio, materials
    for m in (nomad_lib, studio, materials):
        importlib.reload(m)
    src = open(os.path.join(DIR, "build_model.py"), encoding="utf-8").read()
    ns = {"NOMAD_DIR": DIR, "__name__": "nomad_build"}
    exec(compile(src, "build_model.py", "exec"), ns)
    ns["build"]()
    materials.build_all()
    studio.build_stage(transparent=transparent)
    studio.setup_render(engine='CYCLES', samples=SAMPLES, res=RES,
                        transparent=transparent)
    bpy.context.scene.cycles.adaptive_threshold = THRESH
    return studio


def ndc_extent(names):
    """Plus grande coordonnee ecran normalisee atteinte par ces objets.
    1.0 = bord du cadre. Sert a garantir que rien ne sort de l'image."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    cam = sc.camera
    worst = 0.0
    for n in names:
        ob = bpy.data.objects.get(n)
        if not ob or ob.hide_render:
            continue
        mw = ob.matrix_world
        for corner in ob.bound_box:          # boite englobante : majorant sur
            c = world_to_camera_view(sc, cam, mw @ Vector(corner))
            worst = max(worst, abs(c.x - 0.5) * 2.0, abs(c.y - 0.5) * 2.0)
    return worst


def out_dir(sub):
    d = os.path.join(OUT, sub)
    os.makedirs(d, exist_ok=True)
    return d


SKIP_EXISTING = True
MIN_BYTES = 300000        # en-deca, l'image vient d'un test basse resolution


def render_to(path):
    """Rend l'image, sauf si elle existe deja en pleine resolution : le lot
    peut donc etre relance apres une interruption et reprendre ou il en etait."""
    if SKIP_EXISTING and os.path.exists(path) and os.path.getsize(path) >= MIN_BYTES:
        print("[NOMAD] deja fait : %s" % os.path.basename(path))
        return
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ----------------------------------------------------------------------
def job_turntable(n=72):
    build_scene(transparent=True)
    d = out_dir("turntable")
    piv = bpy.data.objects.new("Turn", None)
    bpy.context.scene.collection.objects.link(piv)
    for nm in PARTS:
        ob = bpy.data.objects.get(nm)
        if ob:
            ob.parent = piv
            ob.matrix_parent_inverse = piv.matrix_world.inverted()

    # verification de cadrage sur tout le tour avant de rendre quoi que ce soit
    worst = 0.0
    for i in range(n):
        piv.rotation_euler = (0.0, 0.0, 2 * math.pi * i / n)
        bpy.context.view_layer.update()
        worst = max(worst, ndc_extent(PARTS))
    print("[NOMAD] turntable : occupation max du cadre = %.3f" % worst)
    if worst > 0.97:
        raise RuntimeError("le sujet sort du cadre (%.3f) : reculer la camera" % worst)

    for i in range(n):
        piv.rotation_euler = (0.0, 0.0, 2 * math.pi * i / n)
        bpy.context.view_layer.update()
        render_to(os.path.join(d, "turn_%03d.png" % i))
        print("[NOMAD] turntable %d/%d" % (i + 1, n))
    return d


def job_exploded(n=40):
    studio = build_scene(transparent=True)
    d = out_dir("exploded")
    # pieces en vol : pas de sol, donc pas d'ombre portee incoherente
    g = bpy.data.objects.get("Ground")
    if g:
        g.hide_render = True

    base = {nm: bpy.data.objects[nm].location.copy()
            for nm in PARTS if nm in bpy.data.objects}

    def place(k):
        for nm, b in base.items():
            dx, dy, dz = EXPLODE.get(nm, (0, 0, 0))
            bpy.data.objects[nm].location = b + Vector((dx * k, dy * k, dz * k))
        bpy.context.view_layer.update()

    # ajustement automatique de l'ecartement pour rester dans le cadre
    k = 1.0
    for _ in range(8):
        place(k)
        e = ndc_extent(PARTS)
        if e <= 0.94:
            break
        k *= 0.94 / e
    print("[NOMAD] eclatee : facteur d'ecartement retenu = %.3f (cadre %.3f)"
          % (k, ndc_extent(PARTS)))

    for i in range(n):
        place(k * (i / (n - 1)))
        render_to(os.path.join(d, "expl_%03d.png" % i))
        print("[NOMAD] eclatee %d/%d" % (i + 1, n))
    return d


def job_slide5():
    import studio, phone
    importlib.reload(phone)
    build_scene(transparent=True)
    d = out_dir("slide5")
    phone.build_slide5(studio)
    e = ndc_extent(PARTS + ["Phone_Body", "Phone_Screen", "Cable", "Plug"])
    print("[NOMAD] slide5 : occupation du cadre = %.3f" % e)
    render_to(os.path.join(d, "slide5.png"))
    return d


def job_ambience(which):
    import scenes
    importlib.reload(scenes)
    build_scene(transparent=False)
    d = out_dir("ambience")
    scenes.build(which)
    render_to(os.path.join(d, "%s.png" % which))
    return d


JOBS = {
    "turntable": job_turntable,
    "exploded": job_exploded,
    "slide5": job_slide5,
    "rock": lambda: job_ambience("rock"),
    "backpack": lambda: job_ambience("backpack"),
    "tent": lambda: job_ambience("tent"),
}


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    job = None
    for i, a in enumerate(argv):
        if a == "--job" and i + 1 < len(argv):
            job = argv[i + 1]
    if job not in JOBS:
        print("[NOMAD] usage : --job " + "|".join(JOBS))
        sys.exit(2)
    import time
    t = time.time()
    p = JOBS[job]()
    print("[NOMAD] %s termine en %.1f min -> %s" % (job, (time.time() - t) / 60.0, p))
