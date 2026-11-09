# NEEDLE DROP — builder brief (read fully before touching anything)

Project root = the current working directory. The film spec is `docs/bible.md` (read it; it is long but it is the
spec). This file OVERRIDES the bible wherever they disagree.

## The client brief (why we care)
"Make something CRAZY. Clean as hell, high quality, really high res, great saturated colours, really surprise the
viewer, creative as hell." The quality bar is a top-tier Blender showcase / premium motion-design studio reel.
Every frame must look intentional, rich in detail, clean (no noise, no shimmer, no razor CG edges, no default-grey
anything), and boldly coloured in the NEEDLE DROP palette. Iterate until it looks expensive.

## Machine safety (the user explicitly asked: do not crash the laptop, do not conflict with their Blender jobs)
- NEVER run `blender.exe` directly. ALWAYS use `tools/brun.sh` (one pipeline Blender at a time via a lock, RAM gate,
  BelowNormal priority, RAM watchdog, yields to the user's own Blender jobs). Add `--render` for any job that renders.
  `tools/brun.sh --threads 8 --render -- <file.blend> --python tools/render_frames.py -- --frames 130,200 --pct 50 --out renders/tests/set_b/r1_`
  `tools/brun.sh --threads 6 -- --python scenes/set_b/build.py`   (builds & saves the .blend)
- The lock means other builders may be using Blender; brun simply waits. Do not try to bypass it.
- Never kill, inspect or touch processes you did not start. Never run two Blender jobs yourself at once.
- Keep each Blender process under ~10 GB RAM. Keep meshes sane (the bible's vertex budgets are maxima).
- Downloads are data only (Poly Haven via `tools/common.py`, audio files). Never execute downloaded files.
  For numpy work outside Blender use Blender's bundled Python with isolation:
  `"/e/experimentswithclaude/tools/blender/blender-5.2.2-windows-x64/5.2/python/bin/python.exe" -I script.py`
  (there is no system Python). Node.js and ffmpeg/ffprobe are on PATH.

## Layout (this overrides bible §4.1)
```
tools/common.py       render/colour/compositor helpers, Poly Haven downloader (ph_hdri, ph_texture, ph_model), world_hdri, pbr_material
tools/nd_lib.py       PALETTE (PAL, lin()), the signature marble (build_marble_field / ng_marble / marble_material), black_diamond, simple()
tools/brun.sh         safe Blender runner (see above)
tools/render_frames.py  render chosen frames of a .blend with overrides (--frames --pct --samples --nomb --out --skip-existing)
tools/contact.sh      contact sheet: tools/contact.sh out.png <cols> <tile_w> a.png b.png ...
tools/mix.js, tools/encode.sh   audio mix / final encode (audio stage + director only)
data/timing.json      event map + shot frame ranges (global frames 1..720). data/beats.json kicks/beats. data/bands.json (audio stage)
scenes/set_a/  scenes/set_b/  scenes/set_c/   each set's build scripts (yours). build.py must rebuild the .blend from scratch, deterministic.
blend/set_a.blend  blend/set_b.blend  blend/set_c.blend   outputs of build.py
blend/tonearm_asset.blend   collection "TonearmAsset" (set B writes it; set C appends it)
renders/tests/<set>/   your test renders (name them r<round>_<what>_<frame>.png)
renders/final/f_####.png   final frames (director only)
```
- Do NOT edit `tools/*` or another set's folder. If a shared helper is broken, work around it locally in your set folder
  and mention it in your report. (The director owns tools/.)
- Import shared code in scripts: `ROOT=os.getcwd(); sys.path.insert(0, os.path.join(ROOT,'tools')); import common as C, nd_lib as ND`
  Run Blender with the project root as cwd (brun does not change cwd).

## Decisions that override the bible
- **Marble:** the bible's noise-threshold NG_Marble is REPLACED by `nd_lib`'s banded paper-marbling field
  (`build_marble_field(tree, vector_socket, scale=...)` works in BOTH shader trees and Geometry Nodes trees and returns
  `m` (0..1 band), `raw` (continuous band coordinate: use e.g. sin(2*pi*raw) or a smooth ridge of it for HEIGHTS, never
  fract), `color`, `vein`). `ND.marble_material(name, scale, coord='Object', rough, coat, coat_rough, value_mul)` gives
  the glossy vinyl (defaults) or a matte sand variant (rough=0.85, coat=0). Keep ND.MARBLE_* constants unchanged.
- **Colour:** `C.setup_render(sc, res=(2560,1440), samples=48)` then `C.color(sc, 'AgX - Punchy')` (verified enum).
  `C.compositor(sc, bloom=..., bloom_threshold=..., dispersion=..., saturation=...)` builds the 5.x compositor
  (scene.compositing_node_group; Glare type is the menu input `gl.inputs['Type'].default_value='Bloom'`). You may build
  your own compositor tree for the set (vignette, mist tint, streaks) following that pattern.
- **Engine:** EEVEE (`'BLENDER_EEVEE'`), raytracing on. No volumetrics unless they are cheap and essential. No Cycles.
- **Final render:** 2560x1440, 24 fps, PNG 8-bit RGB is acceptable (16-bit optional). Store final settings IN the .blend
  (resolution 2560x1440 @100%, samples, motion blur, colour, compositor, camera animation over the set's global frame range,
  scene.frame_start/end = the set's range). Test renders use overrides (--pct 50 --samples 16) — never bake test settings into the blend.
- **Frames:** global numbering. Set A 1-120, Set B 121-288, Set C 289-708 (709-720 black, added at encode).
- **Speed budget at final settings:** aim <= 30 s/frame at 2560x1440 on this iGPU (measure one representative frame at 100%
  with brun --render near the end of your stage and report it).
- **Vision budget:** when viewing images, view at most ~1280 px wide (render at --pct 50, or use contact sheets). Do not view
  the same image twice. Keep your context for the work.
- **Fonts:** `C:/Windows/Fonts/` has system fonts (e.g. `ariblk.ttf` Arial Black, `impact.ttf`, `segoeuib.ttf`). Archivo Black
  may be downloaded from the google/fonts GitHub repo (OFL) into assets/fonts/ if you want it; otherwise use Arial Black.

## DIRECTOR NOTES (live — read these; they apply to every stage and every critique)
Updated 02:05 after looking at the first contact sheets:
- **Saturation is the brand.** The marble must read DEEP and RICH (see bench/test_marble2.png for the target colour depth:
  ultramarine, magenta, saffron, violet, night; crisp chalk veins), never pastel/washed pink-lilac. Causes of pastel:
  over-bright key on the glossy coat, bright grey/white environment reflections washing the vinyl, AgX desaturating
  over-exposed colours. Fixes: keep the marble in mid-tones (exposure/light strength), darker cove + dark-violet world so
  reflections are coloured not white, use strip-light streaks as deliberate accents only, compositor saturation ~1.1.
- **Readability first.** Every frame needs one clear focal point and a readable composition at a glance (thumbnail test:
  if a 320 px thumbnail is a blurry jumble, it fails). Motion blur must sell speed, not destroy the image: lower the shutter
  (e.g. 0.2-0.3) for fast close-to-surface flights, keep the camera far enough from walls that the frame isn't one smear.
- **Set A:** currently too dark and chaotic. The groove must read as a giant V canyon: one wall in raking saffron light,
  the other in violet shadow, glossy marble clearly visible on the walls, lands and dust boulders as scale cues, mist into
  depth. Lift exposure; slow the flight in the opening second so the viewer can read the world before the rush.
- **Set B:** good start. Fix pastel vinyl (above); the final capture frames must be saturated marble, not white streak glare.
  Marble on the record at mid shots is too fine/busy: use a larger scale on the record so swirls are bold and legible.

Updated 02:38 (after r8 of Set A, r2 of Set C):
- **Set A composition prescription (r8 still reads as chaos):** shoot it like a classic trench run. Camera roughly at
  land height or a bit below (top third of the V), centred on the groove axis, looking DOWN the groove so the V walls
  converge to a vanishing point with mist; horizon visible; the parallel neighbouring grooves visible as repeating V-cuts
  across the lands; dust boulders on the lands as scale cues. One wall lit saffron, the other violet shadow, marble bands
  clearly readable on the walls (scale the marble so a wall shows several bold bands, not one smear). Only dip deep into
  the V for the lint pass and the vault. Wide (18 mm) + moderate blur (shutter ~0.25). Spire must be a striking faceted
  black jewel with magenta/ultramarine specular glints (needs bright rim lights to reveal facets), not a black slab.
- **Set C:** f289 marble top-down is great (keep). The skim (f380-430) is drowned in orange mist: cut mist density hard
  near camera, keep atmosphere only at kilometre distances so the horizon fades but the foreground stays crisp and
  saturated. Close-range sand needs fine detail (wind ripples / sand normal) so it doesn't look like a smooth blob.
  Mesas are tiny on the horizon: make a few grand, closer ones frame the skim. Post-drop (f450+) must clearly show the
  concentric record ridges and spokes — that reveal is the money shot.

Updated 03:08 (after Set B r7, Set C r3):
- **Set B r7 is on track** (saturation fixed, capture ends on bold marble). Keep it; now polish: crisp label text, the
  hold shot's lighting/reflections, macro opening readability, and not over-blurring the last frames (some marble detail
  should be sharp at f288 for the match cut).
- **Set C S5 top-down (f590-620) reads as a flat vector diagram** (thin rings and spokes on violet). It must read as a
  2.4 km SCULPTED SAND record: tall ridges with long low-sun shadows giving strong relief, marble-coloured sand (saffron
  crests, magenta troughs, chalk crest lines), spokes as broad sculpted channels/halos, label mesa as a real 3D mesa with a
  shadow and strata edges, crater with depth, scattered scale cues (tiny quiver trees / boulders along the rim), gentle
  atmospheric haze at the edges. Think "aerial photo of a land-art installation", not a graphic.
- **Set C S6 giant needle (f640-708) reads as a toy** right in front of the camera. Colossal scale needs: camera FAR from
  the arm (hundreds of metres to a km), arm seen partly against the sky, backlit by the low sun with rim highlights, real
  aerial perspective (haze increasing with distance so the far end of the arm is lighter/bluer), slow majestic motion,
  dust skirt near contact, mesas/horizon for comparison. The arm should be recognisably the S2 arm (chrome S-curve,
  counterweight, vermilion cartridge, 4 coloured lead wires).

Updated 03:37 (Set A build stage ended — frames 1-63 STILL read as an orange/blue smear):
- **Set A is the HOOK of the film (first 2 seconds decide whether anyone keeps watching). Priority #1 of every Set A
  refine round: make frames 1-63 instantly readable and gorgeous.** If the current camera path/scale can't get there,
  REBUILD the S1 camera path (and adjust groove geometry/scale) from scratch — that is explicitly allowed.
  Target image for f1-40: a symmetrical vanishing-point view down a glossy marbled V-groove that stretches to the horizon
  under a deep violet sky with mist, the groove walls catching long bright specular streaks (vinyl is glossy: let the coat
  reflect a bright saffron/magenta sky gradient along the walls), neighbouring grooves visible as parallel V-cuts across
  the lands, lint fibre as a bold silhouette arching across the canyon ahead, dust boulders on the lands. Motion blur only
  on the near walls; the vanishing point stays sharp. Marble scale: each wall shows 3-6 bold, clearly shaped bands.
  The spire (f63-100) must look like a cut gemstone: faceted, with sharp bright specular edges/glints from rim lights.

Updated 06:08 (Set A adr2 sweep: f1-37 near-identical frames; lint band sits ON the horizon hiding the vanishing point):
- **Set A hook fix, concretely:** (1) the lint must NOT be visible at f1 — it should rise into view ahead around f25-35
  as a bold arch crossing the groove HIGH in frame (top third), get big fast, and whip overhead at the 1.9 s pass. (2) The
  vanishing point (centre of frame) must be clean: the groove floor line and both wall edges converging to a bright misty
  horizon. (3) Speed: at canyon scale (60 m wide) the camera needs ~60-120 m/s near the floor to feel fast; ease in from
  ~40 m/s so frame 1 is already moving (the film starts mid-motion). Visible parallax every frame. (4) Walls: fewer, bolder
  marble bands; a glossy coat that streaks the low sun along the walls; the far walls fade into violet mist.
  (5) Frames 61-97 (spire) are now good — keep them; consider adding a slow camera roll for energy.

Updated 07:10 (Set B finished, Set A refine 2 finishing — both now strong):
- **Set C match cut:** Set B's f288 shows BOLD, large marble swirls (renders/tests/set_b/r22_0288.png). Set C's f289 must
  continue that exact scale and composition (read data/handoff.json "S2_end"; if it doesn't line up, at least match the
  swirl scale/band width and colour balance of r22_0288 so the cut feels like the same surface). Compare the two side by
  side before finishing.
- The director will start rendering FINAL frames of sets A and B soon (chunked, through brun). Expect the Blender lock to
  be busier; keep your test renders small (--pct 25-50, few frames).

## Definition of done for a build stage
1. `scenes/<set>/build.py` rebuilds `blend/<set>.blend` from scratch without errors (headless, via brun).
2. Camera + all animation for the set's full frame range are in the blend, following the bible's shot list timings.
3. Key frames rendered at 50% and viewed; a contact sheet of ~8-12 frames across the range saved to renders/tests/<set>/.
4. A short report: what exists, what still looks weak (be honest and specific), measured s/frame at final settings.
