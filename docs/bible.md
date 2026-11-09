# NEEDLE DROP: Production Bible (v1, locked)

**Deliverable:** 30.0 s, 720 frames at 24 fps, 16:9. Rendered at 2560×1440 in EEVEE (Blender 5.2.2, headless). Delivered as a 2560×1440 native master plus a 3840×2160 Lanczos upscale, with 48 kHz stereo audio.
**Units:** 1 Blender unit (BU) = 1 m in every set. Each set is built at its own physical scale and they are never mixed in one file.
**Frame convention:** frame *n* covers the time from (n−1)/24 s to n/24 s. Frame numbers are global (1–720) in every .blend and every output file.

---

## 1. Title, logline, why it surprises

### NEEDLE DROP

**Logline.** We race down a glossy marbled canyon that turns out to be the groove of a spinning record. The camera pulls back to show a vermilion turntable, then gets caught by the spinning vinyl and is swallowed by its swirls. It comes out over a desert of the same marbled colours. On the music's drop, that desert reorganises itself into a two-kilometre record, and a chrome tonearm the size of a mountain lowers its needle onto it. The crackle of that needle is the crackle that opened the film. It is records all the way down.

**The idea behind it.** Every surprise is the same object, a record, seen at a new scale: microscopic (the groove), human (the turntable), and geological (the desert). The film's only typography sits on the two labels: SIDE A on the turntable, SIDE B on the desert.

**Why it surprises (timecodes):**
1. **3.4–6.0 s: the canyon is a groove.** A faceted black crystal spire 140 m tall appears around a bend and the camera climbs its face. In one continuous pull-back the spire becomes a diamond stylus riding a marbled record on a turntable. The parallel canyons were grooves, the boulders were dust, and the "cable" overhead was a lint fibre.
2. **10.0–12.0 s: the turntable eats the camera.** The camera dives at the spinning record and gets caught by its rotation. The whole studio wheels around the frame until the marbled vinyl fills the screen, motionless.
3. **12.0 s: match cut.** The same swirls, now a thousand times larger, are a desert seen from 380 m up. Dunes of magenta, ultramarine, saffron and chalk sand.
4. **17.5–19.2 s: the desert hears the music.** Every kick sends a ring of hopping sand outward. Then everything stops: grains hang in the air for half a beat of silence. On the drop, a shockwave of leaping sand races out of the centre at 880 m/s, passes over the lens, and leaves behind perfect concentric ridges and radial spokes.
5. **21.5–26.0 s: it is a record.** The crane rises to 1.75 km and looks straight down: grooves, a saffron label mesa lettered NEEDLE DROP / SIDE B, and a crater for the spindle hole. The 2.4 km disc starts to turn.
6. **25.6–29.5 s: the needle.** An S-shaped shadow sweeps across the rings before we see what casts it. The camera tilts up into the low sun: the tonearm from shot 2, now 1.9 km long and backlit, lowers its diamond onto the outer groove. Dust bursts, we cut to black on the needle-drop crackle that opened the film, and it loops.

### Changes from the pitch (judges' weaknesses → fixes)

| Weakness raised | Fix in this bible |
|---|---|
| Six unrelated sets, too much scope for one night | **3 sets** (Groove, Turntable, Desert). The tonearm is built once and reused at 8000× scale. Wire, EQ city, speaker cone and RCA jack are all cut. |
| Clichés (Tron wire tunnel, EQ-bar city, speaker-cone slam) | Removed. The music-reactive showpiece is now physical cymatics in sand (kick rings, a drop shockwave, ring pulses by frequency band), which nobody has seen as a skyline. |
| Box city looks procedural | No city at all. |
| Waveform walls read as wobbly candy | The walls are perfectly planar 45° facets. The music bends the whole V cross-section sideways like a rigid winding canyon (as a real cutting lathe does) and never makes the surface wobble. Kicks become crisp "chatter notches" that flash past the lens exactly on each kick. |
| Raytraced refraction on the diamond looks wrong in EEVEE | **No refraction anywhere in the film.** The diamond is a black, faceted, high-index dielectric whose facing ratio drives an ultramarine-to-magenta specular tint. |
| Moiré from fine rings seen from altitude | Ring pitch 40 m, about 39 px at 1.75 km. Every repeating feature is at least 6 px on screen. Micro-normals fade out by camera distance. Fine detail never relies on texture tiling. |
| Funky house pulls the tone toward "music promo" | The music is hybrid cinematic breakbeat with orchestral and brass hits at 120 BPM: groove energy with trailer weight. |
| Relentless pace, no held frame (judge 3) | Three deliberate holds: the turntable orbit (7.5–10.0 s), the top-down marble at 12.0–12.75 s, and the top-down record (24.5–26.75 s). Plus half a beat of total silence before the drop. |
| Every transition is the same occluder wipe | Four different transitions: one hidden occluder cut (chrome), one rotation-locked match cut (marble), one hard reverse-angle smash cut on the drop, and one hard cut to black. Shots 4–6 are a single 12-second continuous take. |
| Waveform cleverness invisible at speed | It is made visible: chatter notches pass the lens on the real kicks, sand rings fire on the real kicks, and ring crests pulse by real band energy. |
| Music on the critical path | Music is build step 1. All timing comes from `timing.json`, derived from the final music edit, so a retime is a data change. |

**Ideas grafted from the other concepts:**
- From RANGE: lens and depth of field as the scale switch (deep focus and mist read as kilometres, shallow DOF reads as millimetres).
- From FLIPSIDE: per-vertex arrival time with a spring-overshoot response, and stable point sets.
- From ONESIDE: locking the camera to the hero so the world rotates around it (the co-rotation dive).
- From THE DAWN WORKS: one control file, silence before the hit, and a quiet button after the final hit.
- From NEEDLE DROP's own judges: data-locked motion, `handoff.json`, shadow-before-giant, and the loop on the same sound file.
- From RANGE: pitching small foley down to make it sound colossal.

---

## 2. Look bible

### 2.1 Palette (hex is law)

| Name | Hex | Used for |
|---|---|---|
| Groove Magenta | `#FF1F8E` | Vinyl marbling, sand troughs, rim light S1/S2, spoke halos |
| Saffron Pop | `#FFB30F` | Record labels, sand crests, dust, tint of the warm key. **Never metallic.** |
| Ultramarine Drive | `#2236FF` | Vinyl marbling, slipmat, spoke cores, rim light |
| Electric Violet | `#7B2BFF` | Marble transitions |
| Vermilion Lacquer | `#FF3A1C` | Turntable plinth, cartridge body, strobe lamp, mesa strata (rock variant `#D9452A`) |
| Night Violet | `#1B0A3F` | S1 world, label ink, crater interior, deepest shadows |
| Anodised Violet | `#2B1660` | Headshell, tonearm base, plinth top plate |
| Apricot Haze | `#FF9A5A` | Desert horizon, mist tint. Outer (non-record) desert sand `#E8895A` |
| Chalk | `#F6EFE3` | Marble veins, crest lines, vinyl dust, lint |
| Plum Strata | `#6B1F5C` | Mesa strata bands |
| Cream Strata | `#F3DFC1` | Mesa strata bands |
| Sky ramp | `#24127A` (zenith) → `#3646F0` (30°) → `#9A6BEA` (10°) → `#FF9A5A` (horizon) → `#FFC48A` (below horizon) | Desert world |
| Black Diamond | `#0B0A14` | Stylus |
| Chrome / aluminium | neutral `#E6E6EC` / `#C9CBD3` | Tonearm, cantilever, platter, spindle |

**Hard rules:**
- Every frame has 2–3 dominant palette colours plus one accent.
- **Never interpolate Saffron directly to Ultramarine**: the midpoint is a muddy grey-teal. Route the transition through Magenta (spokes are a magenta halo with an ultramarine core).
- Banned: any hue between 160° and 200° with saturation above 0.25 (teal or cyan), any metallic yellow (gold), water, palms, architecture, doors.
- The only metals are neutral chrome, aluminium, and violet anodised metal.

### 2.2 Lighting per shot

| Shot | Key | Fill / rim | World / atmosphere | Mood |
|---|---|---|---|---|
| S1 Groove | Sun lamp, elevation 7°, angle 0.5°, colour `#FFB347`, strength 6. It rakes along the groove from camera-left-behind: one wall grazing-lit, the other in violet shadow. | Magenta spot (`#FF1F8E`, 40° cone) from the far end of the groove, back-rimming facets. Ultramarine area light high-right at 15%. | World Night Violet `#1B0A3F` at 0.4. Mist start 40 m, depth 900 m, composited toward `#3B1670`. | A giant alien canyon at blue hour. Hard light and long shadows read as kilometres. |
| S2 Turntable | Soft square area 0.6 m, `#FFC46A`, 60 W, front-left high | Two strip areas 1.6×0.06 m, 5600 K, 40 W each, sliding 0.3 m across the shot so streaks travel on the chrome (plus matching emissive planes hidden from camera so they show in reflections). Magenta spot rim (30 W) back-right low. Ultramarine area fill 10 W right. Strobe lamp: vermilion emissive window strength 30 plus a 0.5 W point light. | HDRI `studio_small_09` (2K) at 0.35, reflections and ambient only. The camera sees the cove: an emission gradient from Night Violet (floor) to Ultramarine (1.2 m) to violet (top). | Premium product shoot. Shallow DOF reads as small. |
| S3–S6 Desert | Sun lamp, elevation **9°**, angle 0.6°, colour `#FFC890`, strength 5. Comes from +Y (screen-up in the top-down). | Sky world provides an ultramarine fill, so shadows read blue-violet. No other lights except a 2 W point light inside the touchdown dust (S6). | Procedural gradient sky (camera and lighting). Mist start = 0.8 × camera altitude (keyed), depth 6000 m, composited toward Apricot at up to 25%. | Golden-hour epic. Long shadows carve every ridge. |

### 2.3 Materials

**Shared node groups (in `nd_lib.py`)**

**`NG_Marble(Vector, Scale, Warp=2.2)`** is the signature pattern, used for the vinyl, the groove walls and the pre-drop desert.
- Step 1: `p = Vector*Scale`.
- Step 2: `n1 = Noise3D(p, scale 1.0, detail 2, rough 0.5)` colour output, then `q = p + (n1−0.5)*Warp`.
- Step 3: `n2 = Noise3D(q, 1.7, detail 3, rough 0.55)`, then `q2 = q + (n2−0.5)*Warp*0.6`.
- Step 4: `m = Noise3D(q2, 2.3, detail 5, rough 0.6, distortion 0.25).Fac`.
- Linear colour ramp on `m`: 0.00 `#1B0A3F`, 0.20 `#2236FF`, 0.38 `#7B2BFF`, 0.52 `#FF1F8E`, 0.66 `#FF1F8E`, 0.74 `#FFB30F`, 0.80 `#FF1F8E`, 1.00 `#2236FF`.
- Veins: `vein = (1−|2·fract(3m)−1|)^40`, mixed to Chalk at 0.8.
- Outputs: Color, m, vein.

**`NG_FadeByDistance(near, far)`**: Camera Data → View Distance → map range 1→0. Used to fade every micro-normal so nothing shimmers at distance.

**Shader table**

| Material | Recipe |
|---|---|
| `M_Vinyl` (S1 walls, S2 record) | Base from NG_Marble. Roughness 0.08–0.15 (noise breakup). Coat 1.0, coat roughness 0.03. Subsurface 0.15, radius tinted magenta. S2 adds anisotropy 0.8 with the Tangent node in Radial-Z mode (concentric groove sheen). A groove normal from a radial Wave texture (0.1 mm pitch) × FadeByDistance(0.005, 0.03 m). S1 adds lathe striations: a Wave texture banded along the groove, 0.4 m pitch, bump 0.02, × FadeByDistance(10, 80). |
| `M_BlackDiamond` | Base `#0B0A14`, metallic 0, IOR 2.42, roughness 0.015. Specular Tint = ramp(Layer Weight Facing): facing `#2236FF` → grazing `#FF1F8E`. Flat shading. Bevel 1 segment with harden normals. No transmission. |
| `M_Chrome` | Metallic 1, base `#E6E6EC`, roughness 0.06 with micro-scratch noise (0.04–0.09). In the giant S6 version, roughness +0.03. |
| `M_BrushedAlu` (platter, cantilever) | Metallic 1, base `#C9CBD3`, roughness 0.18, anisotropy 0.6 (radial tangent on the platter, axial on the cantilever). |
| `M_VermilionLacquer` | Base `#FF3A1C`, roughness 0.32, coat 1.0, coat roughness 0.04. Orange-peel coat normal: noise 1500/m, strength 0.03. |
| `M_AnodisedViolet` | Base `#2B1660`, metallic 1, roughness 0.35, fine brushed bump. |
| `M_Felt` (slipmat) | Base `#2236FF`, roughness 1, sheen 1.0 (sheen roughness 0.3, tint `#9AA6FF`), fibre noise bump 0.2. |
| `M_LabelPaper` / `M_Ink` | Paper: `#FFB30F`, roughness 0.62, fibre bump (noise 4000/m, 0.05). Ink: `#1B0A3F`, roughness 0.3. |
| `M_LeadWire_[4]` | Glossy plastic in Magenta, Saffron, Ultramarine and Vermilion. Roughness 0.25, coat 0.5. |
| `M_Cove` | Emission gradient by Z (see 2.2), strength 0.6, plus faint noise (±0.5%) to prevent banding. |
| `M_Lint` | Base `#E9E0F0`, roughness 0.7, sheen 1.0 (weight 0.8). |
| `M_VinylDust` | Moon-rock normal and roughness maps only. Base `#CFC6DA` × the rock's AO. Sheen 0.4. |
| `M_Sand` (RecordDisc, RecordPatch) | See below. |
| `M_OuterSand` | Base `#E8895A` with ±4% value noise. Same normal stack as `M_Sand`. Roughness 0.9. |
| `M_Mesa` | Strata ramp on (world Z + 6·noise(xy/80 m)): bands 4–15 m thick in `#D9452A` / `#F3DFC1` / `#6B1F5C` / `#D9452A`. Normal and roughness from Poly Haven `rock_face_03` (box projection, 6 m tile, blend 0.2). Tops use `sandstone_cracks` normal. Colour × AO. |
| `M_DustSprite` | Mix(Transparent, Mix(Principled diffuse, Translucent 0.4)). Base mixes Saffron and Chalk by noise. Alpha = radial gradient² × noise × age fade. Blend mode dithered. **Shadows off.** |
| `M_Grain` | Icosphere grain. Roughness 0.5 (no sparkle). Colour picked from the palette by ID hash. |
| World (desert) | Texture Coordinate Generated (ray direction) → Z → the sky ramp. Plus a sun glow: pow(dot(dir, sun), 64) × Apricot. One shader for both camera and lighting. |

**`M_Sand` in detail.** Colour = mix(pre, post, `morph` attribute).
- **pre:** NG_Marble(R·p·k + o), value × 0.85, saturation × 0.9 (so it reads as sand albedo).
- **post:** computed analytically per pixel from object-space r and θ:
  1. Trough Magenta → crest Saffron by smoothstep(0.35, 0.75, crest).
  2. Chalk crest line where crest > 0.92.
  3. Spoke = magenta halo (3 m) with an ultramarine core.
  4. Label zone (r < 240): Saffron. Crater (r < 25): Night Violet. Trench walls: mesa strata.
- Roughness 0.88, sheen 0.25.
- Normal stack:
  - Poly Haven `sand_02` normal, 1 m tile, × FadeByDistance(0, 60).
  - Wind ripples: Wave bands at 0.35 m, distortion 2, direction warped by noise, × FadeByDistance(0, 120).
  - Poly Haven `aerial_sand` normal, 40 m tile, × FadeByDistance(60, 600) × a noise mask to break up tiling.
- Trough grains are 10% darker (natural sorting).

### 2.4 Poly Haven assets (slugs checked against the API on 2026-11-09)

- **HDRI:** `studio_small_09` (2K). Fallback `studio_kontrast_03`. S2 only.
- **Models (download the glTF versions, not .blend):**
  - `moon_rock_01` … `moon_rock_07`: vinyl-dust boulders in S1, decimated to ≤ 8k triangles (heroes 20k).
  - `namaqualand_boulder_02` … `_06`: pre-drop desert boulders that sink as the front passes.
  - `quiver_tree_01`, `quiver_tree_02`, `dead_quiver_trunk`: rim scale cues in S3. Leaves hue-shifted to 245° at saturation 0.5 (violet-blue, never teal). Bark multiplied toward chalk-apricot.
- **Textures (2K, normal and roughness only; their colour maps are discarded):** `sand_02`, `aerial_sand`, `rock_face_03`, `sandstone_cracks`.
- **Font:** Archivo Black (OFL), from the `google/fonts` GitHub repository. Do not use the ⅓ glyph; write "33 1/3".

### 2.5 Colour management

- View transform AgX, look **Punchy**. The enum string is probed: `'AgX - Punchy'` or `'Punchy'`.
- Display sRGB.
- Exposure per set: S1 −0.3, S2 0.0, S3–S6 +0.2. Adjust from test renders.
- Compositor Hue/Saturation: saturation 1.06.
- Output 16-bit PNG, colour already transformed (display-referred). The encode is tagged BT.709.

### 2.6 Post (compositor, per set)

Node chain: Render Layers → mist tint mix → **Glare (Bloom)** → **Glare (Streaks)** (S2 and S6 only) → **Lens Distortion** → Hue/Saturation → vignette → Composite.

- **Mist tint mix** (S1 and Desert): factor = Mist pass × 0.25 (S1 × 0.35) toward the set's mist colour.
- **Glare (Bloom):** threshold 1.2. Mix 0.12 (0.18 in S2).
- **Glare (Streaks):** 4 streaks, threshold 6, fade 0.85, mix 0.10. S2 chrome and the S6 touchdown glint only.
- **Lens Distortion:** distortion 0, dispersion 0.004 (S1 0.006). This is the only chromatic aberration.
- **Vignette:** Ellipse Mask 0.9×0.9, blur 25% of width, multiply so the corners sit at 0.88.
- **Grain** is added at encode time (ffmpeg `noise=alls=3:allf=t+u`), never in the 16-bit masters. No sharpening, except a mild unsharp mask on the 4K upscale.

### 2.7 Lens and scale grammar (the rule every shot obeys)

- **Kilometres** = wide lens, **DOF off**, mist, a hard low sun, heavy slow motion. Applies to S1 and S3–S6.
- **Millimetres** = shallow DOF (f/2.8–4), soft studio light, smooth pull-backs. Applies to S2.
- Lenses: S1 18 mm. S2 28→40→28 mm. S3 28→24 mm. S4 20 mm. S5 20→24 mm. S6 24→35 mm.
- Motion-blur shutter 0.5 everywhere except S2, which uses 0.25 so the label stays legible.

---

## 3. Shot list (30.0 s = 720 frames; frames 709–720 are black, added in the encode)

| # | Name | Time (s) | Frames | Set | Lens / DOF | Transition out |
|---|---|---|---|---|---|---|
| S1 | THE GROOVE | 0.000–5.000 | 1–120 | A | 18 mm / off | Hidden cut on the chrome cantilever (occluder whip) |
| S2 | THE MACHINE | 5.000–12.000 | 121–288 | B | 28→40→28 mm / f2.8→f8 | Rotation-locked match cut on marble, hard cut on the 12.0 downbeat |
| S3 | MARBLE DESERT | 12.000–18.000 | 289–432 | C | 28→24 mm / off | Hard reverse-angle smash cut on the drop |
| S4 | THE DROP | 18.000–21.500 | 433–516 | C | 20 mm / off | No cut (continuous take) |
| S5 | SIDE B | 21.500–26.000 | 517–624 | C | 20→24 mm / off | No cut (continuous take) |
| S6 | NEEDLE | 26.000–30.000 | 625–708 picture, 709–720 black | C | 24→35 mm / off | Hard cut to black at 29.5; the loop returns to S1 |

Sum: 120 + 168 + 144 + 84 + 108 + 96 = 720 frames, 30.000 s.

At 120 BPM, 1 beat = 12 frames and 1 bar = 48 frames. Downbeats fall on frames 1, 49, **97 (4.0)**, **145 (6.0)**, 193, **241 (10.0)**, **289 (12.0)**, 337, 385, **433 (18.0 DROP)**, 481, 529, **577 (24.0)**, **625 (26.0)**, 673. The touchdown at **29.0 s (f697)** is on beat 3 of bar 15.

### S1 THE GROOVE: 0.000–5.000 (f1–120)

- **Frames 1–6:** fade up from black (ffmpeg). The film starts mid-motion.
- **Camera:** 18 mm, DOF off, motion blur 0.5. The camera is inside a 90° V-canyon (60 m wide, 30 m deep) of glossy marbled vinyl, with the saffron sun raking along it. It starts 6 m above the floor at 12 m/s and eases to 30 m/s by 3.0 s. It follows the groove centreline as it meanders, banking up to ±8° with the curvature.
  - **1.9 s (f46):** dips 3 m to pass under the lint fibre, 4 m thick and made of 24 twisted strands, sagging across the canyon.
  - **2.6 s (f63):** around a bend, the black diamond spire appears far ahead (140 m tall, silhouetted, with facet glints).
  - **2.0–3.5 s:** rises from 8 m to 22 m, so the parallel canyons and boulder-strewn lands come into view.
  - **3.4–4.0 s:** decelerates as the spire fills the frame.
  - **4.0 s (f97, downbeat):** pitches up 70° and climbs the facet face at 6–10 m standoff (about 160 m/s vertical, heavy blur).
  - **4.75 s (f115):** crests the top and tips down along the brushed-aluminium cantilever, still rising. The cantilever slides under and fills the frame with a saffron reflection whip by f120.
- **What moves:** the camera only. The set is static, and the music is cut into it: the meander follows the real low-band envelope, and chatter notches are placed so the camera passes one exactly on every detected kick.
- **Sound sync:** crackle at 0.0, muffled (low-passed) music, a whoosh at the lint pass, a pitched-down crystal and metal swell into the vault.
- **Out:** hidden cut. Both sides of the cut are bright brushed metal with the camera rising, and screen-space motion is matched via `handoff.json`.

### S2 THE MACHINE: 5.000–12.000 (f121–288)

- **Camera:**
  - **5.00 (f121):** 28 mm, f/2.8, 1.6 mm above the real 0.5 mm cantilever, looking down 70° toward the stylus. Roll matches S1's last frame.
  - **5.00–7.50:** exponential pull-back from 1.6 mm to 0.45 m while swinging to a high three-quarter view (elevation 28°, azimuth 35° front-left). Focal length 28→40 mm; f-stop f/2.8→f/4. Focus tracks an empty on the headshell.
  - **6.00 (f145, downbeat):** stylus, cartridge and headshell become recognisable. The music's low-pass filter snaps open.
  - **7.50–10.00 (f181–240): THE HOLD.** A slow 25° orbit around the spindle axis at 40 mm. Strip lights slide streaks along the chrome arm, the strobe dots hang frozen on the spinning platter, and the motion-blurred label shows the "NEEDLE DROP" ring text.
  - **9.00 (f217):** 12-frame focus rack from the headshell to the label.
  - **10.00–11.75 (f241–282): THE CAPTURE.** The camera is parented to `SpinRig`, an empty on the spindle whose angular velocity ramps from 0 to 200°/s (33⅓ rpm) by 11.4 s. Locally it dives from (r = 0.20 m, h = 0.18 m) to (r = 0.068 m, h = 0.003 m), ending looking straight down. Focal length 40→28 mm; f-stop f/4→f/8. Focus is locked to the vinyl surface. The studio, arm and plinth wheel around the frame edges until the record fills the view.
  - **11.75–12.00 (f283–288):** marble filigree fills the frame, perfectly still relative to the camera.
- **What moves:**
  - Platter, slipmat, record and label rotate at the true 200°/s.
  - The four strobe rows rotate at their aliased rates (row N = 216 appears frozen). Strip lights slide.
  - The arm is static (it is playing). The pitch LED and strobe lamp are lit.
- **Out:** hard match cut on the 12.0 downbeat (f289). The marble colours and composition continue exactly, and the image is motionless across the cut.

### S3 MARBLE DESERT: 12.000–18.000 (f289–432)

- **Camera:**
  - **12.00–12.75 (f289–306):** 28 mm, top-down at 380 m altitude above (r = 880 m, bearing 0°). The frame is 488 m wide, and the marble swirl matches S2's last frame. Near-static drift of 1 m/s. Low-sun dune shadows slowly reveal relief: it is a landscape.
  - **12.75–16.00 (f307–384):** exponential descent from 380 m to 6 m above ground, pitching −90° → −4°, travelling outward along +X to r = 1040 m and reaching 25 m/s. Focal length 28→24 mm. The horizon rises: vermilion strata mesas, quiver trees on the rim, apricot horizon, ultramarine sky. The sun is from the left.
  - **16.00–17.50 (f385–420):** terrain-following skim 4–6 m above ground at 25 m/s, banking ±5° over dune crests.
  - **17.50–18.00 (f421–432):** decelerates to 3 m/s.
- **What moves:**
  - Kick rings expand outward from somewhere behind the camera on every detected kick: sand hops 0.6 m in a travelling ring, with saffron dust puffs. From 14.0 s their amplitude grows with the riser.
  - 17.0–17.5: about 20k grains lift slowly off the dunes (a first hint of wrong physics).
  - 17.5–18.0: half a beat of **total silence**. Grains hang motionless.
- **Out:** hard smash cut on the drop (f433) to the reverse angle.

### S4 THE DROP: 18.000–21.500 (f433–516), continuous take into S5 and S6

- **Camera:**
  - **18.00:** 20 mm, 14 m above ground at r = 1120 m on bearing 0°, facing the centre (−X), pitch −3°. Locked off. The sun is from the right.
  - **18.00–18.95:** on the drop, a ring of leaping sand (15–25 m crest, a 40 m saffron dust plume) bursts out of the base of the distant saffron label mesa and races toward the lens at 880 m/s across the dunes.
  - **18.95–19.20 (f456–462):** the front passes over the camera. Six frames of dust engulf the lens with grains blasting past, plus a 6-frame Noise-modifier shake (0 → 0.6° → 0).
  - **19.20–21.50:** the dust clears. Ahead, perfect concentric ridges (saffron crests with chalk crest lines, magenta troughs) and ultramarine spokes converge on the label mesa. The camera pushes forward from 15 m/s, accelerating to 40 m/s and rising from 14 m to 60 m while its roll settles.
- **What moves:**
  - Behind the front, the sand settles with a 10% spring overshoot.
  - Desert boulders sink into the sand as the front passes.
  - The rim trench (the record's edge) opens behind the camera at 19.05 s.
  - Launched grains fall back under real gravity (about 2–3 s airborne: heavy, majestic).
  - From 20.0, ring crests pulse with the music's band energy.

### S5 SIDE B: 21.500–26.000 (f517–624), no cut

- **Camera:**
  - **21.50–24.50:** exponential crane from 60 m to **1750 m**, pitching −8° → −89.5°. It travels to directly above the centre with a 20° yaw so the rings swing into place. Focal length 20→24 mm. Clip start and mist start are keyed with altitude.
  - **24.50–26.00:** top-down hold. Screen-up is the sun (+Y). The full disc spans frame left to right, cropped top and bottom.
  - **25.60:** the tip of a long S-shaped shadow (the tonearm's) slides in from the top-left edge.
- **What moves:**
  - Ring crests pulse by band: 8 radial zones, bass innermost, highs outermost.
  - **24.0 (f577):** the whole 2.4 km disc spins up from 0 to 3°/s by 25.0. Spokes and the NEEDLE DROP / SIDE B lettering visibly rotate. The mesas outside stay still.

### S6 NEEDLE: 26.000–30.000 (f625–708, then black)

- **Camera:**
  - **26.00–26.75:** hold. The tonearm's S-shaped shadow sweeps across the rings toward the centre as the (unseen) arm swings in.
  - **26.75–28.25:** tilt-up dive: pitch −89.5° → −24°, altitude 1750 → 560 m, moving to the final position about 1.1 km from the landing point L. Focal length 24→35 mm. The colossal chrome tonearm enters from the top-left, backlit by the low sun just out of frame. Its headshell carries the same four coloured lead wires seen in S2.
  - **28.25–29.00:** 2%/s push. The cartridge lowers the last 40 m, and downwash lifts a dust skirt from 28.7.
  - **29.00 (f697): TOUCHDOWN.** The diamond meets the outer groove. A dust ring bursts out (0 → 120 m radius, rising 60 m) plus a spray along the rotation direction, with a 3-frame micro-shake.
  - **29.00–29.50:** the burst expands.
  - **29.50 (f709):** hard cut to black. Frames 709–720 are black under the crackle.
- **Loop:** frame 720 (black, crackle) runs into frame 1 (crackle, fade-up in the groove).

### Event map (all timings live in `data/timing.json`)

| Event | Time (s) | Frame |
|---|---|---|
| Fade-in end | 0.25 | 6 |
| Lint pass | 1.90 | 46 |
| Spire visible | 2.60 | 63 |
| Vault start | 4.00 | 97 |
| Crest | 4.75 | 115 |
| Hidden cut | 5.00 | 121 |
| Filter opens | 6.00 | 145 |
| Hold start | 7.50 | 181 |
| Focus rack | 9.00 | 217 |
| Capture start | 10.00 | 241 |
| Match cut | 12.00 | 289 |
| Riser start | 14.00 | 337 |
| Grains lift | 17.00 | 409 |
| Silence | 17.50 | 421 |
| DROP | 18.00 | 433 |
| Front passes lens | 19.00 | 457 |
| Pulses start | 20.00 | 481 |
| Crane | 21.50 | 517 |
| Disc spin | 24.00 | 577 |
| Top-down hold | 24.50 | 589 |
| Shadow enters | 25.60 | 615 |
| Tilt-up | 26.75 | 643 |
| Push | 28.25 | 679 |
| Touchdown | 29.00 | 697 |
| Black | 29.50 | 709 |

Each event snaps to the nearest detected downbeat or beat within ±2 frames.

---

## 4. Build breakdown

### 4.0 Machine-safety protocol (mandatory: the user asked for this explicitly)

`scripts/safe_launch.ps1` wraps **every** Blender and ffmpeg launch. Never call `blender.exe` directly.

1. **Other Blender jobs come first.**
   - List `Get-Process blender`. Anything not in `logs/pipeline.pid` belongs to someone else. Never touch, kill, or read the files of other processes.
   - Before any **render** (test or final), sample `\GPU Engine(*engtype_3D)\Utilization Percentage` and CPU per PID for 30 s. If any foreign Blender uses more than 10% of the 3D engine or more than 25% CPU, **do not render**. Wait 5 minutes, re-check, and log it.
   - **Never run two GPU renders on the 780M at once**: the iGPU is shared and contention risks a driver timeout (TDR).
   - Build-only steps (no rendering) may run alongside a foreign Blender only if free RAM is at least 24 GB, with `-t 4`.
   - If blocked for more than 60 minutes, keep doing non-Blender work (downloads, audio) and keep polling.
2. **One pipeline Blender at a time**, enforced by a lockfile (`logs/pipeline.lock`).
3. **Launch:** `blender.exe -b --factory-startup -noaudio -t 8 <file> ...` for renders (`-t 4` for builds). Set the process to **BelowNormal** priority (`$p.PriorityClass='BelowNormal'`). `--factory-startup` keeps user add-ons and auto-run scripts off.
4. **RAM:**
   - Start only if free physical RAM is at least 20 GB (`Win32_OperatingSystem.FreePhysicalMemory`).
   - Target a peak of 10 GB or less per pipeline process (log `PeakWorkingSet64`).
   - Between chunks, if free RAM falls below 16 GB, pause and re-poll every 60 s.
5. **Disk:** at least 40 GB free before final rendering (16-bit PNGs are about 15–20 MB each).
6. **Chunks:** render in 24-frame chunks, one Blender invocation each, with `use_overwrite=False` and `use_placeholder=True`. Resuming is automatic, and a crash costs at most one frame. Cool down 20 s between chunks.
7. **Watchdog:** if any frame exceeds 3× its shot benchmark, stop **our** process (by our PID only), log it, and apply the mitigation ladder (§5). Rising frame times across chunks mean thermal throttling: lengthen the cooldown to 60 s.
8. **TDR guard:** before batching each shot, render its heaviest frame alone, first at 50% then at 100%:
   - S1 f100 · S2 f121 · S3 f410 · S4 f458 · S5 f600 · S6 f700.
9. **Isolation:**
   - All outputs go under `needle_drop/`.
   - Downloads go to `assets/_dl/<source>/<slug>/` as untrusted data. Only glTF, images, audio and fonts; nothing downloaded is ever executed.
   - Python that reads downloads runs with `-I`.
10. **ffmpeg** runs only after every render has finished (`-threads 6`, BelowNormal). If ffmpeg is not installed, ask the user before downloading a build. The fallback is Blender's own Video Sequencer encoder.
11. **Accounts:** never create accounts, log in, or solve CAPTCHAs for assets or audio. If a source requires any of those, skip it.
12. **Tell the user** in the final report: keep the laptop plugged in, on a hard surface, lid open.

### 4.1 Project layout and conventions

```
needle_drop/
  scripts/  nd_lib.py  probe.py  audio_analyze.py  build_set_a.py  build_set_b.py  build_set_c.py
            cams.py  safe_launch.ps1  render_queue.ps1  assemble.ps1
  data/     timing.json  beats.json  bands.json  handoff.json  layout_c.json
  assets/_dl/polyhaven/...  assets/_dl/audio/...  assets/fonts/ArchivoBlack-Regular.ttf
  blend/    set_a_groove.blend  set_b_turntable.blend  set_c_desert.blend
  audio/    music_src/  music_edit.wav  sfx/  mix.wav
  renders/frames/f_0001.png … f_0708.png     previz/     delivery/     logs/     credits.txt
```

- Each set file holds one scene. All shot cameras use timeline markers bound to cameras.
- Keyframes use **global** frame numbers.
- Every animated value is driven from a `CTRL` empty's keyed custom properties, or from directly keyframed Geometry Nodes modifier inputs. Values are written per frame from `timing.json`, `beats.json` and `bands.json`. **No timing is typed by hand into a scene.**

**`probe.py` (10-second headless run, before any build)** prints and saves `data/api.json` with:
- the EEVEE engine enum (`BLENDER_EEVEE` vs `BLENDER_EEVEE_NEXT`) and `dir(scene.eevee)`;
- the motion-blur property locations (`scene.render.use_motion_blur`, `motion_blur_shutter`, `scene.eevee.motion_blur_steps`);
- the compositor entry point (`scene.compositing_node_group` in 5.x vs `scene.node_tree`) and the Glare node's `glare_type` enum;
- the AgX look enum;
- the Principled BSDF input names;
- the Geometry Nodes node idnames used here: DistributePointsOnFaces, InstanceOnPoints, StoreNamedAttribute, IndexSwitch, FloatCurve, SampleIndex, GeometryProximity, ImageTexture.

Builders read `api.json` instead of guessing names.

### 4.2 Build order

1. **Safety wrapper and probe** (§4.0, `probe.py`).
2. **Audio:** choose the music, edit it, analyse it into `timing.json`, `beats.json` and `bands.json` (§4.3, §6). Everything is timed from this.
3. **`nd_lib.py`:** NG_Marble, NG_FadeByDistance, all materials in §2.3, bevel and weighted-normal helper, camera-bake helper, render and compositor presets, Poly Haven downloader with cache, keyframe writer.
4. **Set B (Turntable + Tonearm asset).** The tonearm is reused in S6, and S2's last frame defines the S3 match.
5. **Set C (Desert).** It carries 18 s, 60% of the film.
6. **Set A (Groove).**
7. **Previz:** the whole film at 960×540, 4 samples, no raytracing, no motion blur (about 25 min). Mux with the audio and check sync and pacing. Fix timing in `timing.json`, then rebuild keys.
8. **Look-dev per shot:** 3 stills at 50% (first, middle, last), a 12-frame contact sheet, and a 24-frame strip at 50% for shimmer (S1, S3, S4, S5). Then one full-resolution benchmark of the heaviest frame.
9. **Final render queue** (§5).
10. **Assembly and encode** (§5.6).

### 4.3 Audio data pipeline (`audio_analyze.py`, numpy only)

- **Input:** `music_edit.wav` (48 kHz, already edited and tempo-locked to 120 BPM, §6).
- **Process:**
  - Mono mix; STFT (n_fft 2048, hop 512).
  - Spectral-flux onsets. Kicks = peaks of flux in the 30–150 Hz band above an adaptive median threshold.
  - Beat grid = 120 BPM anchored on the drop downbeat at 18.000 s, checked by cross-correlating the onset envelope with the grid. If drift is more than 1 frame, re-edit.
- **Outputs:**
  - `beats.json`: beat times, downbeats, kick times and strengths.
  - `bands.json`: for frames 1–720, 8 log-spaced bands from 30 Hz to 16 kHz as per-frame RMS, with 1-frame attack and 6-frame release, normalised 0–1 by the 95th percentile, and clamped to a change of 0.25 or less per frame (anti-strobe).
  - `env_low[720]` and `rms[720]`.
  - `timing.json`: the event map in §3, with frames snapped to detected beats.

### 4.4 Shared camera and controls

- **Camera paths** are computed in numpy (positions, look targets, focal length, focus, roll) and baked as one keyframe per frame on location, rotation (quaternion), lens and focus distance.
- **Easing:**
  - Exponential distance curves for every pull-back and crane: `d(u) = d0·(d1/d0)^smoothstep(u)`.
  - Smootherstep everywhere else.
  - Nothing linear except constant cruising.
- **`clip_start`** is keyed at 0.05 × the distance to the nearest subject, so precision holds from 0.1 mm to 9 km.
- **`handoff.json`:**
  - S1 writes the last 3 frames' camera forward, up and screen-space velocity; S2's first 3 frames are solved to continue them (rising, same roll).
  - S2 writes the record-space point and orientation under its final camera; Set C uses it for the marble mapping (§4.6).

### 4.5 Set B: Turntable and Tonearm (real scale, metres; S2, and tonearm reused in S6)

All hard surfaces get a Bevel modifier (2–4 segments, clamp overlap) plus Weighted Normal (keep sharp). Nothing has a razor edge.

| Element | Build |
|---|---|
| Plinth | Cube 0.45×0.36×0.065, bevel 0.012 (4 segments), `M_VermilionLacquer`. Top plate inset 0.43×0.34, recessed 0.6 mm, `M_AnodisedViolet`. 4 feet: cylinders r 0.03 with chrome ring and violet rubber. |
| Platter | Profile curve → **Screw modifier** (r 0.150, 20 mm thick, rolled rim), `M_BrushedAlu`, radial anisotropy. |
| Strobe rows | 4 separate ring objects on the rim, each of hemispheres (r 0.9 mm) instanced by GN on a circle. Counts N = 216 / 212 / 220 / 224. **Each row rotates at its aliased apparent rate**, computed as (8.333°/frame mod spacing, wrapped to ±spacing/2) × 24/s, so row 216 looks frozen and the others drift slowly in opposite directions. Lit by the strobe lamp. |
| Slipmat | Disc r 0.148, 3 mm, `M_Felt`. |
| Record | Disc r 0.1505, 1.8 mm, rim bead, label recess, hole 7.2 mm, `M_Vinyl` with object coordinates (cm = coordinate × 100). Radial zones in the shader: lead-in 0.146–0.150 (smooth); programme 0.075–0.146 with 4 matte 1 mm track gaps (0.128, 0.111, 0.094, 0.082); run-out 0.060–0.075 (smooth, 2 spiral lines). |
| Label | r 0.05, `M_LabelPaper`. Text objects converted to mesh, inset 0.05 mm, `M_Ink`: "NEEDLE DROP" (Archivo Black, 7 mm cap height) and the ring text "SIDE A · 33 1/3 RPM · STEREO ·" repeated twice around r 0.04 via a Curve modifier on a circle. |
| Spindle | Chrome cylinder r 3.6 mm, 15 mm tall, tapered tip. |
| Rotation | Platter, slipmat, record and label parented to `PlatterRot`, Z rotation keyed linear at 200°/s (f121–288). `SpinRig` (camera capture, S2) is a separate empty on the same axis. |
| **Tonearm (collection `TonearmAsset`, origin at the pivot)** | **Base:** cylinder r 0.03, h 0.025, anodised violet with a chrome ring. **Gimbal yoke:** two plates, a bearing housing and a pivot pin. **S-arm:** 3-point Bezier with bevel depth 0.004 (resolution 16), `M_Chrome`. Rear stub. **Counterweight:** cylinder r 0.017 × 0.03, knurled with about 3000 GN-instanced 0.6 mm pyramids in a diamond lattice (geometry, not a texture). **Anti-skate dial:** r 0.012 with 30 arrayed ticks and a saffron index line. **Arm rest and cue lever:** chrome, ultramarine knob. **Headshell:** 50 mm, anodised violet, curved finger lift. **Cartridge:** 18×17×17 mm vermilion lacquer box with chamfers and 2 screws. **4 lead wires:** Bezier curves r 0.4 mm in Magenta, Saffron, Ultramarine, Vermilion. **Cantilever:** `M_BrushedAlu` tube r 0.25 mm × 6 mm, 20° down. **Stylus:** octagonal faceted `M_BlackDiamond` about 0.3 mm, seated in the record surface. Geometry: effective length 0.235 m, pivot 0.215 m from the spindle. |
| Controls | Start/stop button (chrome ring, violet cap), 33/45 buttons, pitch slider with a 2 mm saffron LED emitter (strength 8), power LED, strobe lamp housing with a vermilion emissive window. |
| Cove | 4×3 m plane bent through a 0.6 m radius (L-profile), `M_Cove`. |
| Light probe | One Sphere probe at the platter (r 0.4 m, resolution 512), baked headless if the operator works. If baking fails in background mode, skip it and rely on the HDRI. |

**Level of detail:** everything is hero-level (the camera reaches 1.6 mm from the cantilever). The record's groove micro-normal is faded so it never aliases.

### 4.6 Set C: The Desert Record (metres; S3–S6)

**Layout constants (`data/layout_c.json`):**
- Disc centre at the origin. Sun from +Y, elevation 9°, angle 0.6°.
- S3/S4 bearing θ3 = 0° (+X axis).
- Record radii:
  - spindle crater r < 25 m (bowl, 30 m deep);
  - label mesa r < 240 m (40 m tall, flat saffron top, two terraced 20 m steps over r 240–270);
  - groove zone r 270–1160 m;
  - lead-in land r 1160–1170 m;
  - rim trench r 1170–1200 m (18 m deep).
- Ring pitch **40 m**, crest height 6 m.
- Tonearm pivot P: r = 1720 m, bearing 145° (its tower's shadow misses the disc and the S5 frame). Landing point L: r = 1150 m, bearing 66°. Arm length in this set: 1880 m (8000× scale).
- Mesa ring at r 1500–2600 m (14 mesas, none between bearings 130° and 160°). Quiver trees at r 1230–1500 m.

**Objects**

**1. `RecordDisc`**
- numpy polar mesh: 900 rings × 3600 segments, about 3.24M vertices, radius 0 to 1205 m. Radial spacing 0.75 m below r = 300, 1.5 m beyond.
- Per-vertex float attributes baked once: `r`, `theta`, `zone` (0–7, radial eighths of the groove zone), `h_rec`, `h_dune`, `patch_lower`.
- **`h_rec`** (numpy, analytic):
  - Crests: `6·(1−|sin(π(r′−270)/40)|)^2.5` with `r′ = r + 2.5·cos(16θ)·window`. The scalloped petals give the cymatic mandala feel.
  - Plus spokes: `3·exp(−(r·cos(8θ)/48)²)·window`. These are the 16 Chladni nodal lines.
  - Plus label mesa, crater, lead-in and trench.
- **`h_dune`**: baked by a temporary GN modifier, then applied. GN Noise is identical to shader Noise, so the dunes follow the marble swirls exactly:
  - ridged(NG_Marble-equivalent field in the desert mapping) × 10 m + fBm × 2 m;
  - faded to 0 beyond r 1100–1300.
- **Marble mapping for the match cut:**
  - `k = 7.894e-4` vinyl-cm per desert-metre (S2 final frame width 0.3857 cm ÷ S3 first frame 488.6 m).
  - Offset `o` and rotation `R` come from `handoff.json` (the record-space point and orientation under S2's final camera).
  - Before committing, the builder renders 6 candidate S2 end points at 25% and picks the most beautiful filigree.

**2. `RecordPatch`** (hero LOD for S3's skim and S4)
- Sector r 900–1200 m, θ ±8° about bearing 0°, at 0.25 m spacing (about 1.4M vertices).
- Same attributes, same GN group and material, origin at the disc centre.
- `RecordDisc` is lowered 0.15 m under the patch footprint, with a 2 m skirt on the patch edges. The step lies 150 m or more from the camera in mist, so it is invisible.

**3. GN group `RecordLive`** (shared by Disc and Patch). Inputs are keyframed per frame.
- **Inputs:** `front` (m; linear `240 + 880·(t−18.0)` from f433, frozen at 1300 after 19.2 s), `kick_r1..3`, `kick_a1..3`, `band0..7`, `pulse_amp`.
- **Logic:**
  ```
  morph = FloatCurve( clamp((front − r)/60) )        # points (0,0) (0.55,1.10) (0.78,0.96) (1,1)
  hop   = 14·sin(π·clamp((front − r)/45))           # the leaping sand wave
  kicks = Σ kick_a_i·exp(−((r − kick_r_i)/10)²)·(1 − morph)    # pre-drop rings
  bandk = IndexSwitch(zone → band0..7)
  h     = mix(h_dune, h_rec·(1 + pulse_amp·0.15·bandk), morph) + hop + kicks − patch_lower
  ```
- Set Position (Z = h). Store Named Attribute `morph` (float, point) for the shader.
- **Kick rings:** each detected kick k from 12.0 to 17.5 s gets `kick_r = 450·(t − t_k)` and an amplitude that grows from 0.6 to 1.2 m through the riser. At most 3 rings are alive, rotated into the 3 input slots.
- **Disc rotation** is an object-level Z rotation (`spin`, from 0 to 3°/s, starting at 24.0). The shader's analytic colours use object coordinates, so they rotate too.

**4. `OuterDesert`** (static)
- Polar annulus r 1195–9000 m, 4096 segments. Radial spacing 1 m at 1200 m, growing geometrically to 25 m. About 1.6M vertices.
- Apricot dunes baked in, `M_OuterSand`. A far plane beyond 9 km carries the horizon colour.

**5. Mesas** (6 unique meshes, 14 instances)
- Noise-perturbed 64-vertex outline, extruded in 3–4 tiers of 30–50 m, each tier inset 5–15 m with noise, plus a slightly overhanging caprock.
- Remesh (voxel 2 m) → Displace (Clouds, scale 30 m, strength 4 m) → Decimate to about 60k triangles.
- `M_Mesa`. Height 60–180 m. Placed by GN from a fixed point list.

**6. Scale and debris instancers** (all static point sets, so IDs are stable)
- **Quiver trees:** 40 instances (`quiver_tree_01/02`, scaled 1.4×) plus 10 `dead_quiver_trunk` on r 1230–1500 m.
- **Boulders:** 30 `namaqualand_boulder_02..06` inside the patch. Their Z offset is `−1.2·size·morph(r_i)`, so they sink as the front passes.

**7. `LabelText`**
- "NEEDLE DROP" over "SIDE B", Archivo Black, letters 45 m tall, converted to mesh.
- Extruded 0.6 m and inset 0.4 m into the mesa top, `M_Ink`. Parented to `RecordDisc`.

**8. FX point sets** (built once in numpy, attributes per point, all motion analytic in GN; never Distribute-per-frame, never Realize)

| Set | Contents | Motion |
|---|---|---|
| `KickPuffs` | 300 sprites per kick in the camera sector | Born at ring passage, rise 2 m, fade over 1.2 s |
| `FloatGrains` | 20k icosphere grains, 4–25 cm, within 40 m of the S3 skim path | Rise 0 → 1.5 m with noise drift from 17.0. Velocity × 0 during 17.5–18.0 (they hang). |
| `FrontDust` | 60k sprites, size 2–12 m, sector r 300–1200 m, θ ±35° | `t_launch_i = 18.0 + (r_i − 240)/880`. Position = rest + up·(v_up·a − ½·9.81·a²) + radial·v_rad·a + noise. Alpha fades over 2.5 s. Scale 0 outside its life. |
| `FrontGrains` | 40k grains within 40 m of the S4 camera | Same ballistic formula with real g |
| `TouchdownDust` | 3000 sprites + 2000 grains at L | Ring expanding to 120 m and rising to 60 m over 0.5 s, plus a tangential spray along the disc rotation |

**9. Tonearm**
- Append `TonearmAsset` from Set B and scale it ×8000.
- **Cheat:** scale the cartridge, cantilever and diamond a further ×6 (diamond about 14 m), and the cantilever thickness ×3, so the contact reads.
- **Tower:** the base and gimbal on a 300 m anodised-violet column at P.
- **Rig:** two keyed rotations, like the real arm.
  - Yaw swing from rest to over L: 25.25 → 26.75 s, headshell height 190 m. Its shadow (about 6.3× height toward −Y) crosses the disc.
  - Lift hinge lowering 190 m → 0 m: 26.75 → 29.00 s (ease-out, last 40 m slow).
- Chrome roughness +0.03. Bloom streak on the glint at touchdown.

**10. Sun and world**
- Sun lamp and procedural world as in §2.3. No world volume, no volumetrics anywhere.
- Mist start and depth keyed with camera altitude.

### 4.7 Set A: The Groove (metres; S1)

**1. Groove mesh** (numpy; about 570k vertices)
- 9 parallel V-grooves at 100 m pitch.
- **Cross-section per pitch (48 vertices):** land 20 m → bevel (r 0.6 m, 4 vertices) → 45° wall → bottom arc (r 2 m, 8 vertices) → 45° wall → bevel → land 20 m. Groove 60 m wide, 30 m deep.
- **Samples along +X:** 0.4 m from −20 to 160 m; 1.5 m from 160 to 800 m; 5 m from 800 to 3000 m.
- **Lateral offset of groove g at x:** `y = 100g + 10·sin(2πx/700 + φ_g) + 9·(env_low(t(x) + 1.8g) − 0.5) + notch(x)`.
  - `t(x)` inverts the S1 camera's travel curve.
  - Adjacent grooves carry the music one revolution (1.8 s) earlier or later, as on a real record.
  - The whole V shifts rigidly; walls stay planar.
- **Depth modulation:** the floor rises or falls ±1 m with the L−R difference.
- **Chatter notches:** for each kick t_k ≤ 4.0, at `x_k = x_cam(t_k)`, both walls step 2 m outward over 1 m, then taper back over 17 m. A crisp light and shadow line passes the lens on each kick.
- Meander phases are tuned so a bend hides the spire until 2.6 s.
- Material `M_Vinyl` with object-space NG_Marble at **its own beauty scale** (Scale ≈ 0.004/m, so swirls run 20–200 m). Only S2↔S3 needs exact scale continuity.

**2. Lint fibre**
- Centre Bezier spanning the camera's groove at `x_cam(1.9 s)`, sagging to 14 m above the floor.
- 24 strands built in numpy around a parallel-transport frame (bundle radius 4 m, 2 twists per 100 m). Strand bevel 0.35 m.
- Plus 120 frayed fibrils (r 0.12 m, random curls). `M_Lint`.

**3. Vinyl dust**
- GN Distribute Points on Faces (Poisson, minimum distance 7 m, density 0.004/m²), masked to the lands (normal Z > 0.95) × a noise mask. About 600 instances of `moon_rock_01..07` (8k triangles each), scale 1–7 m.
- Plus 6 hand-placed 20k-triangle hero boulders on the floor off the camera line. `M_VinylDust`.

**4. Stylus**
- bmesh: elliptical tip (8 m sphere) contacting both walls about 12–18 m up, flaring to an octagonal shank 70 m across by 40 m height, rising to 140 m, chamfered top. `M_BlackDiamond`, flat-shaded, 0.3 m single-segment bevel.
- Front face about 22 m ahead of the camera at 4.0 s.

**5. Cantilever**
- Tube r 25 m, 700 m long, rising at 20° away from the camera into darkness. `M_BrushedAlu`, axial anisotropy.
- Black glossy epoxy collar at the joint.

**6. Lights and world** as in §2.2. Mist pass on.

**Level of detail:** near groove is hero quality; beyond 160 m mid; beyond 800 m low with heavy mist. Dust rocks use 8k triangles; heroes use 20k.

### 4.8 LOD and visibility matrix

| Element | S1 | S2 | S3 | S4 | S5 | S6 |
|---|---|---|---|---|---|---|
| Groove mesh / dust / lint / spire | hero | – | – | – | – | – |
| Turntable | – | hero | – | – | – | – |
| Tonearm | spire + cantilever only | hero | – | – | shadow only | ×8000 |
| RecordDisc (3.24M) | – | – | on | on | on | on |
| RecordPatch (1.4M) | – | – | on | on | on until 22.5 s, then hidden | hidden |
| OuterDesert + mesas + trees | – | – | on | on | on | on |
| FloatGrains | – | – | 17.0–18.0 | – | – | – |
| FrontDust / FrontGrains | – | – | – | on | until 23.5 s | – |
| TouchdownDust | – | – | – | – | – | 28.7 s onward |

Hidden means `hide_render` is keyed, so it is not evaluated.

---

## 5. Render plan

### 5.1 Resolution decision

- **2560×1440 native.** Native 4K would take about 2.2× longer (about 12 h) and does not fit the night.
- Deliver the 1440p master plus a 3840×2160 Lanczos upscale (with mild unsharp mask), H.265 10-bit.
- Only frames 1–708 are rendered. The fade-in and the black tail are made in ffmpeg.

### 5.2 EEVEE settings (names verified via `api.json`)

| Setting | Value |
|---|---|
| Engine | EEVEE (5.x enum) |
| Render samples (TAA) | S1 48 · **S2 64** · S3 48 · **S4 64** · S5 48 · S6 48 |
| Raytracing | ON, Screen-Trace method, resolution 1/2, denoise ON (spatial + temporal + bilateral), max roughness 0.5 (probes above that) |
| Fast GI (horizon scan) | ON, resolution 1/2 |
| Shadows | Virtual shadow maps, ray count 1, step count 6, resolution scale 1.0. Sun "shadow jitter" OFF. |
| Volumetrics | Not used anywhere |
| Motion blur | ON. Shutter 0.5 (S2 0.25), position Center, steps 1 |
| DOF | Camera DOF only in S2, with jittered camera ON. Max bokeh size 100 px. |
| Film | Filter 1.5 px. Overscan ON at 3% (stabilises screen-space effects at frame edges). |
| Clamping | Surface indirect clamp 10 (no fireflies) |
| Passes | Combined + Mist (S1, Desert) |
| Colour management | AgX + Punchy (§2.5) |
| Output | PNG, RGB, 16-bit, compression 15. Overwrite OFF, placeholders ON. `renders/frames/f_####.png` |

### 5.3 Per-shot cost estimates (verify by benchmark)

Estimates are per frame at 1440p.

| Shot | Frames | Est. s/frame | Main cost | Mitigation ladder (apply in order until ≤ 35 s/frame) |
|---|---|---|---|---|
| S1 | 120 | 20 | 570k-vertex groove, about 600 rock instances, sun VSM, mist | Samples 48→32 → rocks decimated to 4k → shadow resolution scale 0.75 |
| S2 | 168 | 28 | Jittered DOF, chrome reflections, 64 samples | Samples 64→48 → jittered DOF off (post DOF) → raytrace max roughness 0.3 |
| S3 | 144 | 24 | GN on 4.6M vertices, evaluated about 3× per frame for motion blur; puffs | Hide the patch above 50 m altitude → kick puffs 300→150 per kick |
| S4 | 84 | 34 | Plus 60k dithered sprites and 40k grains | Sprites 60k→30k → grains 40k→20k → samples 64→48 |
| S5 | 108 | 24 | GN on the disc, mist | Patch hidden (already) → samples 48→40 |
| S6 | 96 (88 rendered) | 28 | Giant chrome arm, touchdown sprites | Sprites 3000→1500 → raytrace resolution 1/4 |
| **Total** | 708 rendered | | About 18,500 s ≈ **5.1 h + 0.4 h chunk overhead ≈ 5.5 h** | **Hard gate:** if the benchmarked projection exceeds 7.5 h, apply ladders before launching. Never drop below 2560×1440. |

### 5.4 Render queue order (riskiest first)

S4 → S6 → S2 → S3 → S5 → S1. Each shot renders in 24-frame chunks under `safe_launch.ps1` (§4.0). Every finished chunk is logged to `logs/render.csv` with frame times, peak RAM and the foreign-process check.

### 5.5 Known EEVEE risks and their fixes

| Risk | Fix |
|---|---|
| VSM shadows swim during the S5 crane | Shadow resolution scale 1.0, jitter off, check a 24-frame strip. If it still swims, raise the sun's resolution limit and lower the crane's angular speed. |
| Chrome looks flat (off-screen reflections) | Matching emissive strip planes hidden from camera, sphere probe, HDRI. S6 reflects the on-screen desert and the procedural sky. |
| Deforming-mesh motion blur breaks | Vertex counts never change. Point sets never change size (scale-to-0 instead of deletion). |
| Dithered sprites look noisy | 64 samples in S4. Sprites cast no shadows. |
| Banding in the sky or cove gradient | 16-bit output, ±0.5% noise in the gradient shader, grain at encode. |

### 5.6 Assembly (`assemble.ps1`, only after all renders are done)

1. Concatenate `f_%04d.png` (1–708) at 24 fps. Pad frames 709–720 with black (`tpad=stop=12:color=black`). Fade in over frames 1–6.
2. Mux `mix.wav` (§6).
3. Encode:
   - **Master:** H.265 10-bit (`-pix_fmt yuv420p10le -crf 12 -preset slow`, BT.709 tags), AAC 320k.
   - **Upload:** H.264 High, `-crf 14`, `yuv420p`, `noise=alls=3:allf=t+u` before encoding.
   - **4K:** `scale=3840:2160:flags=lanczos`, `unsharp=5:5:0.4`, H.265 10-bit, CRF 14.
4. Write `delivery/credits.txt` (the music credit is mandatory if the track is CC-BY).

---

## 6. Audio cue sheet

### 6.1 Music brief

- **Genre and mood:** hybrid cinematic breakbeat (big-beat drums, warm analogue or slap bass, orchestral or brass stab hits), glossy and confident. Not house, not ambient. Arc: curious (filtered) → groove → rising tension → hard stop → huge drop → victorious groove → final hit.
- **Tempo:** 118–124 BPM. Lock to exactly **120 BPM** with ffmpeg `rubberband` or `atempo` (stretch of ±3% or less, editing only). If the track needs more than ±3%, reject it.
- **Required structure after editing** (bars of 2.0 s):

| Time (s) | Section |
|---|---|
| 0.0–6.0 | Sparse intro: drums and bass, with room for crackle |
| 6.0–12.0 | Main groove A |
| 12.0–17.5 | Build with riser or snare roll |
| **17.5–18.0** | Stop (imposed by volume automation if the track has none) |
| **18.0** | DROP downbeat |
| 18.0–26.0 | Drop groove |
| 26.0–29.0 | Continuation or lift |
| **29.0** | Final hit (the track's own hit, or a 0.5 s slice of its drop downbeat placed here) |
| 29.5 | Hard cut of the music |

- **Sources (no login or CAPTCHA):**
  1. Mixkit Music (Mixkit licence)
  2. freepd.com (CC0 / public domain)
  3. Pixabay Music (Pixabay Content Licence), only if downloadable without an account
  4. incompetech (CC BY 4.0, credit in the description)
- **Search keywords:** "cinematic breakbeat", "big beat trailer", "epic breakbeat", "hybrid trailer drop 120 bpm", "action electronic trailer", "funk trailer epic", "glitch hop cinematic", "breakbeat build drop", "groovy epic electronic".
- **Edit (ffmpeg; cutting, crossfading and filtering of the real recording only):**
  - Choose the source so its drop downbeat lands at 18.000 s. Splice intro bars at bar boundaries with 50 ms crossfades.
  - **POV filter automation (crossfading a filtered copy with the dry copy):**

| Time (s) | Treatment |
|---|---|
| 0–6.0 | `lowpass=f=650`, −4 dB ("inside the groove") |
| **6.0** | 6-frame crossfade to the full-range dry copy (the filter "snaps open") |
| 12.0–17.5 | Full range plus a light `aecho=0.8:0.6:60|120:0.2|0.12` (desert space) |
| 17.5–18.0 | Muted |
| 18.0–29.5 | Full and dry |

  - Music is ducked 3 dB for 0.5 s under the 18.0 and 29.0 impacts.

### 6.2 SFX (Mixkit SFX, Pixabay SFX, OpenGameArt CC0, freesound CC0 only if downloadable without login)

Every file and its licence is logged in `credits.txt`.

| Time (s) | Frame | Sound | Search keywords | Processing / level |
|---|---|---|---|---|
| 0.00 | 1 | **Needle-drop tick + crackle onset** (this exact file returns at 29.0) | "vinyl needle drop", "record needle", "vinyl crackle" | Crackle bed loops at about −30 LUFS, dips at 6.0, gone by 12.0 |
| 0.00–5.00 | 1–120 | Deep canyon wind | "canyon wind", "deep wind ambience" | LPF 2 kHz, low |
| 1.75–2.10 | 43–51 | Heavy low pass-under whoosh (lint) | "low whoosh pass by", "fabric whoosh" | −5 semitones |
| 3.30–4.00 | 80–97 | Crystal resonance swell + metal scrape | "crystal singing bowl", "glass resonance", "metal scrape" | Both **−12 semitones** (scale by pitch) |
| 4.00–4.80 | 97–116 | Big rising whoosh (the vault) | "cinematic whoosh rise", "swoosh up" | |
| 4.80–5.00 | 116–120 | Short metallic ring or swish | "metal swish", "metal ring short" | Quiet |
| 5.00–6.00 | 121–144 | Reverse air pull (pull-back) | "reverse whoosh" | |
| 6.00–12.00 | 145–288 | Turntable motor hum + strobe neon buzz | "turntable motor hum", "electric motor hum quiet", "neon hum" | Very low, dry, intimate |
| 10.00–12.00 | 241–288 | Rotating vortex whoosh ending in a reverse cymbal at exactly 12.0 | "vortex whoosh", "spinning whoosh", "reverse cymbal" | Rising |
| 12.00 | 289 | Soft deep thump on the cut + desert wind bed in | "deep impact soft", "desert wind ambience" | |
| 12.0–17.5 | per kick | Sand-hiss burst on every kick ring | "sand pour", "sand shake", "rain stick" | −20 dB, timed to `beats.json` kicks |
| 14.0–17.5 | 337–420 | Sub rumble swell | "earthquake rumble low", "deep rumble" | Under the riser |
| 17.0–17.5 | 409–420 | Soft shimmer as grains lift | "magic shimmer soft", "sparkle rise" | −7 semitones, quiet |
| **17.5–18.0** | 421–432 | **TOTAL SILENCE**, all tracks muted | – | – |
| **18.00** | 433 | **DROP:** sub boom + trailer impact + sand explosion | "cinematic sub boom", "trailer impact", "explosion debris" | Peak moment |
| 18.0–19.0 | 433–456 | Approaching roar | "sandstorm whoosh", "rushing wind" | Rising |
| 19.00 | 457 | Front passes the lens: heavy whoosh + sand blast | "heavy whoosh pass by", "sand blast", "debris impact" | Wide stereo |
| 19.1–21.5 | 459–516 | Settling sand rain | "sand falling", "grains pouring", "rain stick slow" | |
| 21.5–26.0 | 517–624 | High-altitude wind | "wind high altitude", "airplane wind ambience" | Low |
| 24.00 | 577 | Disc spin-up: turntable start + stone grind | "turntable start", "vinyl spin up", "stone grinding" | **−24 semitones** |
| 26.0–27.0 | 625–648 | Shadow pass: dark air-pressure drone | "low drone pass", "dark whoosh slow" | |
| 27.0–29.0 | 649–696 | Arm lowering: servo + metal creak + hydraulic hiss | "mechanical servo", "metal creak", "hydraulic hiss" | **−12 semitones** |
| **29.00** | 697 | **TOUCHDOWN:** the 0.00 needle-drop file + sub boom + sand burst | "sub boom", "sand explosion" | Needle file −12 semitones |
| 29.0–30.0 | 697–720 | Crackle bed (same file as 0.00) through the black | – | Seamless loop into 0.00 |

### 6.3 Mix spec

- Mix in an ffmpeg `filter_complex`: `adelay`, `volume` automation, `afade`, `amix`.
- Two-pass `loudnorm`: I = −14 LUFS, TP = −1 dBTP, LRA 11. 48 kHz stereo, AAC 320k in delivery.
- SFX sit under the music except at 18.0, 19.0 and 29.0.
- **Sync check:** after muxing, every row of the event map lands within ±1 frame.

---

## 7. Quality bar checklist (run on every test render; a failed item blocks the final render)

**Brief and reference distance**
- [ ] Nothing reads as a temple, palace, courtyard, pool, palm, door reveal, or a modelling-breakdown structure. No teal and gold anywhere.
- [ ] Automatic hue check on every still: pixels with hue 160–200°, saturation > 0.30 and value > 0.20 make up < 0.5% of the frame. No gold or metallic yellow. Saffron is only ever non-metallic.
- [ ] Each frame has 2–3 dominant palette colours plus one accent. No muddy grey seam where saffron meets ultramarine (spoke edges are magenta).

**Scale reads (the core of the film)**
- [ ] S1 at f60: a fresh viewer would say "canyon", not "macro". Deep focus, mist depth visible, hard long shadows. The spire is hidden before f63.
- [ ] S2 at f181–240 reads unmistakably as a small, premium turntable: shallow DOF, crisp bevel highlights on every edge, the label ring text readable at least half the time.
- [ ] S3 at f289 vs S2 at f288 side by side: the swirl composition overlaps; colour families and orientation match.
- [ ] S5 at f600 reads as a record from above (rings, label lettering at least 35 px tall, spindle crater, circular edge visible left and right).
- [ ] S6 at f690: the arm is recognisably the S2 tonearm (S-curve, counterweight, four coloured wires) and reads colossal (mist, backlit, slow).

**Clean as hell**
- [ ] No shimmer or crawl in the 24-frame 50% strips (S1 striations, S3/S4 ripples, S5 rings). Every repeating feature is at least 6 px on screen. Micro-normals fade by distance.
- [ ] No fireflies, no specular sparkle noise (roughness floors respected, indirect clamp 10).
- [ ] No banding in the sky or cove at 16-bit. No posterised gradients after the H.264 encode with grain.
- [ ] No razor CG edges: bevels on all hard surfaces. No visible mesh faceting on sand crests or groove walls.
- [ ] No seams: hero patch vs disc invisible; outer desert meets the trench cleanly; no z-fighting at any altitude (clip start keyed).
- [ ] Dust sprites have soft edges, no visible quad corners, and no shadow artefacts.

**Motion**
- [ ] No popping: instance counts constant per shot; grains and sprites appear and disappear by scale or alpha, not deletion.
- [ ] Motion blur looks right on the rotating platter, the S2 capture spin, and the S4 front pass. No streaking ghosts on static objects.
- [ ] The S1→S2 hidden cut plays without a bump at full speed: motion direction (rising), brightness and roll continuous.
- [ ] Spring overshoot visible but subtle on the post-front ridges. Ring pulses smooth, no strobing at 24 fps.
- [ ] No VSM shadow swimming during the S5 crane. No moiré on the S5 top-down.

**Sync and sound**
- [ ] Every event in the §3 event map lands within ±1 frame of its audio cue. Chatter notches (S1) and kick rings (S3) land on audible kicks.
- [ ] Half a beat of true silence at 17.5–18.0. The drop at f433 hits picture and sound together.
- [ ] The loop plays seamlessly by ear (crackle at 29.5–30.0 into 0.00). Loudness is −14 LUFS ±0.5 and true peak ≤ −1 dBTP.
- [ ] `credits.txt` lists every music and SFX file with URL, author and licence. Any CC-BY credit text is included.

**Machine safety and budget**
- [ ] Each test or benchmark frame logs time and peak RAM. Pipeline peak ≤ 10 GB. Projected total ≤ 7.5 h.
- [ ] No pipeline render ran while a foreign Blender was active on GPU or CPU. No foreign process or file was touched.
- [ ] One pipeline Blender at a time, BelowNormal priority, `-t 8` for renders. Free RAM never fell below 16 GB during rendering.
- [ ] The heaviest frame of each shot rendered at 100% with no driver reset before batching.