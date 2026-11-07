"""Load each LapGym scene without rendering, reset it and run a few random steps."""
import importlib, os, sys, traceback, time

SCENES = {
    "reach": ("sofa_env.scenes.reach.reach_env", "ReachEnv"),
    "deflect_spheres": ("sofa_env.scenes.deflect_spheres.deflect_spheres_env", "DeflectSpheresEnv"),
    "search_for_point": ("sofa_env.scenes.search_for_point.search_for_point_env", "SearchForPointEnv"),
    "tissue_manipulation": ("sofa_env.scenes.tissue_manipulation.tissue_manipulation_env", "TissueManipulationEnv"),
    "pick_and_place": ("sofa_env.scenes.pick_and_place.pick_and_place_env", "PickAndPlaceEnv"),
    "grasp_lift_touch": ("sofa_env.scenes.grasp_lift_touch.grasp_lift_touch_env", "GraspLiftTouchEnv"),
    "rope_cutting": ("sofa_env.scenes.rope_cutting.rope_cutting_env", "RopeCuttingEnv"),
    "precision_cutting": ("sofa_env.scenes.precision_cutting.precision_cutting_env", "PrecisionCuttingEnv"),
    "tissue_dissection": ("sofa_env.scenes.tissue_dissection.tissue_dissection_env", "TissueDissectionEnv"),
    "thread_in_hole": ("sofa_env.scenes.thread_in_hole.thread_in_hole_env", "ThreadInHoleEnv"),
    "rope_threading": ("sofa_env.scenes.rope_threading.rope_threading_env", "RopeThreadingEnv"),
    "ligating_loop": ("sofa_env.scenes.ligating_loop.ligating_loop_env", "LigatingLoopEnv"),
    "tissue_retraction": ("sofa_env.scenes.tissue_retraction.tissue_retraction_env", "TissueRetractionEnv"),
    "bimanual_tissue_manipulation": ("sofa_env.scenes.bimanual_tissue_manipulation.bimanual_tissue_manipulation_env", "BimanualTissueManipulationEnv"),
}
from sofa_env.base import RenderMode

NEEDS_RENDER = {"grasp_lift_touch"}
names = sys.argv[1:] or list(SCENES)
for name in names:
    mod, cls = SCENES[name]
    t = time.time()
    try:
        m = importlib.import_module(mod)
        Env = getattr(m, cls)
        kwargs = {"render_mode": RenderMode.HEADLESS if name in NEEDS_RENDER else RenderMode.NONE}
        if hasattr(m, "ObservationType"):
            kwargs["observation_type"] = m.ObservationType.STATE
        env = Env(**kwargs)
        env.reset()
        for _ in range(10):
            env.step(env.action_space.sample())
        env.close()
        print(f"OK    {name} ({time.time()-t:.1f}s)", flush=True)
    except Exception as e:
        print(f"FAIL  {name}: {type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}", flush=True)
        traceback.print_exc(limit=3, file=open(f"/tmp/lapgym_{name}.err", "w"))

# SOFA's Python bindings segfault during interpreter shutdown (Py_FinalizeEx), after all the
# work is done. Exit without running that cleanup.
sys.stdout.flush()
sys.stderr.flush()
os._exit(0)
