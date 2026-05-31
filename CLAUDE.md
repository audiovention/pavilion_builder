# 3D Pavilion Builder — Project Documentation

## Overview

A parametric 3D model of a gable pavilion with an L-shaped brick wall, built as a single self-contained HTML file using Three.js r128 (CDN). The user is planning to build this pavilion in real life and uses this tool to visualize and adjust dimensions before construction. Based on a 16×20 ft MyOutdoorPlans gable pavilion PDF (uploaded as reference), adapted to metric units and Bulgarian brick standards.

**File:** `pavilion.html` — single file, no build step, opens directly in any browser.

## Units & Standards

- **All dimensions are in meters.** The CONFIG object, GUI sliders, and all builder functions work in meters.
- **Brick dimensions:** Bulgarian standard — 250×120×65mm (length × width × height) with 10mm mortar joints. These are configurable via `CONFIG.brickWall`.
- The original reference plans used imperial (feet/inches). Converted values are approximate.

## Architecture

### Single-file structure

The HTML file contains everything inline: CSS `<style>`, then a single `<script>` block with all JS. Sections are separated by comment banners (`═══`). The major sections in order:

1. **CONFIG** (~line 57) — The central configuration object. All parametric dimensions live here.
2. **GUI_SCHEMA** (~line 79) — Declarative definition of the control panel. Each entry maps a CONFIG path to a slider with min/max/step.
3. **Helpers** — `cfgGet(path)` / `cfgSet(path, val)` for dot-notation access into CONFIG.
4. **Procedural Textures** — `woodTexture()`, `concreteTexture()`, `shingleTexture()` generate canvas-based textures at init time. No external image files.
5. **Scene Setup** (`initScene`) — Three.js renderer, camera, lights, materials, and group containers.
6. **Orbit Controls** (`initControls`) — Custom mouse/touch orbit, pan, zoom. No dependency on OrbitControls.js.
7. **Utility functions** — `box()` creates a positioned box mesh. `clearGroup()` tears down a named group for rebuild.
8. **Builder functions** — One per structural component. Each follows the pattern: clear its group, read CONFIG, generate geometry, add to group.
9. **`rebuildModel()`** — Calls all builders in order. Debounced via `scheduleRebuild()` (60ms).
10. **GUI generation** (`createGUI`) — Reads GUI_SCHEMA and generates HTML sliders + value inputs.
11. **Animation loop** — Simple `requestAnimationFrame` render loop.
12. **Init sequence** — `initScene()` → `initControls()` → `createGUI()` → `rebuildModel()` → `animate()`.

### Group system

Each structural component has a named `THREE.Group` in the `groups` object:

| Group Key    | Builder Function    | What It Contains |
|-------------|-------------------|-----------------|
| `ground`     | `buildGround()`    | Green ground plane |
| `foundation` | `buildFoundation()` | Concrete slab |
| `posts`      | `buildPosts()`     | Vertical 6×6 post columns |
| `beams`      | `buildBeams()`     | Long beams (along X) + cross beams (along Z) |
| `ridge`      | `buildRidge()`     | Ridge supports + ridge beam |
| `braces`     | `buildBraces()`    | Post-to-beam braces + ridge braces |
| `rafters`    | `buildRafters()`   | Sloped rafter pairs on both sides |
| `roof`       | `buildRoof()`      | Plywood/shingle panels, ridge cap, fascia |
| `brickWall`  | `buildBrickWall()` | InstancedMesh of bricks + mortar backing |

To rebuild only one part, call `buildXxx()` directly. `rebuildModel()` rebuilds everything.

### Coordinate system

- **Y is up.** Ground plane is at Y=0.
- **X axis** runs along the pavilion's long dimension (the ridge/beam direction).
- **Z axis** runs along the short dimension (rafter span direction).
- Origin is at the center of the post grid at ground level.
- The foundation slab is centered at origin.
- Posts are placed symmetrically: `±totalX/2` in X, `±totalZ/2` in Z.

### Vertical stacking order

```
Ground (Y=0)
  └─ Foundation slab (0 to foundation.thickness)
      └─ Posts (foundation.thickness to fndTop + brickWall.wallHeight)
          └─ Beams (postTop to postTop + beams.height)
              └─ Ridge supports (beamTop to beamTop + ridge.supportHeight)
                  └─ Ridge beam (top of supports + ridge.size/2)
                      └─ Rafters slope from ridge down to beams
                          └─ Roof panels on top of rafters
```

Key derived values used across builders:
- `postTop = CONFIG.foundation.thickness + CONFIG.brickWall.wallHeight`
- `beamTop = postTop + CONFIG.beams.height`
- `ridgeTop = beamTop + CONFIG.ridge.supportHeight + CONFIG.ridge.size/2`

### Post grid

The post grid is **derived from the foundation dimensions**. The helper `getPostGridDimensions()` computes spacing from `foundation.length`, `foundation.width`, and `foundation.extension`:
- `totalX = length - 2 * extension`, `totalZ = width - 2 * extension`
- `spacingX = totalX / (gridCols - 1)`, `spacingZ = totalZ / (gridRows - 1)`

Posts are arranged in a rectangular grid defined by `posts.gridCols` (along X) × `posts.gridRows` (along Z). The function `getPostPositions()` returns an array of `{x, z, col, row}` objects, centered on the origin, with posts behind the brick wall filtered out.

- `gridCols` controls how many columns along the long (X) axis. Default 3.
- `gridRows` controls rows along the short (Z) axis. Default 2.
- Post height equals `brickWall.wallHeight` — they share the same parameter.
- Posts that fall within the brick wall coverage area are automatically omitted.

Beams and ridge elements iterate over gridCols/gridRows (via `getPostGridDimensions()`, not `getPostPositions()`) to match — they span the full structure even where posts are omitted, since the wall supports them.

### Brick wall

The L-shaped wall occupies the **back-right corner** of the pavilion:
- **Long wall** runs along the +Z face (back), from right corner leftward.
- **Short wall** runs along the +X face (right side), from back corner forward.

Coverage is controlled by `longSideCoverage` (0.0–1.0) and `shortSideCoverage` (0.0–1.0) as fractions of the full side length.

Implementation details:
- Uses `THREE.InstancedMesh` for performance — a single draw call for all bricks.
- Running bond pattern: odd courses are offset by half a brick length.
- Corner interlocking: on alternating courses, the perpendicular wall's brick extends into the corner.
- Each brick gets a randomized HSL color variation around a terracotta hue for realism.
- A flat mortar-colored box is placed behind the bricks as a backing plane (visible through gaps).
- `updateStats()` displays brick count and course count in the top-left HUD.

### Procedural textures

All textures are generated on `<canvas>` elements at startup — no external files needed:
- **Wood:** Brown base with wavy grain lines and occasional knots. 512×512.
- **Concrete:** Gray with per-pixel noise. 256×256.
- **Shingles:** Dark rows of offset rectangles simulating asphalt shingles. 512×512.

All use `THREE.CanvasTexture` with `RepeatWrapping`.

### GUI system

The GUI panel is generated from `GUI_SCHEMA`, a declarative array of sections. Each section has:
- `section`: display name
- `open`: whether it starts expanded
- `controls[]`: array of `{k, l, mn, mx, s}` where:
  - `k` = dot-notation path into CONFIG (e.g. `'posts.height'`)
  - `l` = label text
  - `mn/mx` = slider min/max
  - `s` = step value

Each control renders a range slider + a text input. Changes trigger `scheduleRebuild()` which debounces and calls `rebuildModel()`.

To add a new parameter: (1) add it to CONFIG, (2) add a GUI_SCHEMA entry, (3) read it in the relevant builder function.

## How to Extend

### Adding a new structural component

1. Add a new key to `CONFIG` with its parameters.
2. Add corresponding entries to `GUI_SCHEMA`.
3. Add the group name to `groupNames` array.
4. Write a `buildNewComponent()` function following the pattern: `clearGroup('name')` → read CONFIG → create geometry → add to `groups.name`.
5. Call it from `rebuildModel()`.

### Adding a new GUI section

Add an object to `GUI_SCHEMA`:
```js
{ section:'New Section', open:false, controls:[
  {k:'newSection.param1', l:'Param 1 (m)', mn:0, mx:10, s:0.1},
]}
```

### Changing the brick wall position

The wall corner is currently computed from the post grid's back-right corner (`+X, +Z`). To move it to a different corner, modify the `cornerX`/`cornerZ` calculations and the loop directions in `buildBrickWall()`.

### Performance considerations

- Brick wall uses InstancedMesh — can handle thousands of bricks efficiently. The max instance count is pre-calculated; `mesh.count` is set to the actual number used.
- Each `clearGroup()` call disposes geometries to prevent memory leaks.
- Rebuild is debounced to 60ms to avoid jank during slider dragging.
- Shadow map is 2048×2048. Reduce if performance is an issue on low-end hardware.

## Known Limitations / TODO

- Braces use simplified 45° rotation; real mitered angles from the PDF (18.5°, 26.5°, 45°) are not yet precisely replicated.
- Rafter birdsmouth cuts are not modeled — rafters are simple boxes.
- No gable-end trim pieces (the triangular decorative V-braces visible in the PDF step 15).
- Roof panel geometry uses flat boxes rather than proper trapezoids at the edges.
- The mortar backing plane is a single flat box; individual mortar lines between bricks are not rendered (would need a texture or additional geometry).
- No export functionality (STL, OBJ, etc.) yet.
- No undo/redo for parameter changes.
- Foundation is the driving dimension for the post grid; `foundation.extension` controls how much the slab extends beyond the outermost posts on each side.

## Dependencies

- **Three.js r128** loaded from CDN: `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js`
- No other external dependencies. No npm, no build tools.

## Reference

- Original plans: `16x20_pavilion_plans.pdf` from MyOutdoorPlans.com
- Brick standard: Bulgarian standard brick 250×120×65mm, mortar joint 10mm
- All structural dimensions derived from the PDF's cut list and step diagrams, converted to metric

---

# Bathroom Tile Designer (`bathrooms.html`)

A **separate, self-contained** tool (not part of the pavilion) for designing tile layouts for two real bathrooms before laying them. Same conventions as `pavilion.html`: Three.js r128 from CDN, single HTML file, all dimensions in **metres**, GUI generated from a schema, `cfgGet`/`cfgSet` dot-notation, debounced `scheduleRebuild()`. It does **not** share code with `pavilion.html` — edit each file independently.

## What it does

- **Two bathrooms**, switched by the top tabs:
  - **Bath A** — a simple rectangle.
  - **Bath B** — a rectangle with a parametric corner **notch** (L-shape).
- **Two view modes**, switched by the green toggle:
  - **3D Room** — orbit the tiled interior.
  - **Unfold 2D** — top-down "net": floor in the centre, each wall folded flat outward (a tile-setter's elevation layout).
- Everything is parametric: room W/D/H, notch corner + width + depth, door (which wall, position, width, height), floor tiles (size, grout, **angle**, start X/Z), and **per-wall** tile settings.

## Tiles — KEROS "Kalina Gris" (the user's actual product)

Real product, sourced from praktiker.bg. Photos live in `tiles/` and are loaded as textures (one image mapped per tile face, `ClampToEdge`). Falls back to procedural canvas textures if the JPGs are missing, and the GUI **Display → Texture** toggle switches between photos and flat colours.

| File | Product | Real size |
|------|---------|-----------|
| `tiles/kalina_gris_floor.jpg`      | Granitogres floor (alt)    | 33×33 cm |
| `tiles/kalina_gris_wall.jpg`       | Faience wall field         | 25×50 cm |
| `tiles/kalina_gris_decor.jpg`      | Patchwork décor            | 25×50 cm |
| `tiles/kalina_olas_gris_decor.jpg` | "Olas" wave relief décor   | 25×50 cm |
| `tiles/momastela_ghirigori_0..2.jpg` | Momastela Ghirigori N — **default floor** | 31×62 cm |

**Tile catalog — type fixes texture AND dimensions.** Products live in `FLOOR_TILES` and `WALL_TILES`; each entry carries its label, its dimensions, and which texture to use. The GUI exposes a **Tile type** dropdown per surface (`floor.prod`, `walls.<C>.prod`) — there are no free width/height sliders; the laid size is read from the chosen product (walls swap long/short by the per-wall `orient` toggle). Floor products: `0` Momastela Ghirigori 31×62 (mixed, default), `1` Kalina Gris 33×33. Wall products: `0` Kalina Gris 25×50. Add a product = push one catalog entry (+ its texture).

**Mixed / multi-face floor pack:** Momastela Ghirigori N (catalog `kind:'momastela'`) is sold as a pack of several *different* decorated faces. The face textures are in `momastelaPhoto[]`; `floorMatFor(kind,i,j)` assigns one per floor cell via a stable hash of `(i,j)` (scattered, never reshuffles). Add faces by pushing more `loadTile(...)`. The praktiker image URL scheme for this product differs from Kalina's: `medias/<id>.jpg-Product-zoom?context=…` with numbered variants `<id>-1/-2/-3`; one of the four images was a lifestyle room photo, not a tile — excluded.

The Momastela photos are square shots of a 2:1 tile, so after cropping (below) they are 2:1 and the floor product size is **0.62×0.31** (landscape) to map without distortion.

**Tile schedule / take-off:** `TALLY` (reset each `buildRoom`, rendered in the top-left HUD by `updateStats`) counts **logical** tiles — one per grid cell that lands in the room, so a cut tile or a tile split by the door still counts once (not per polygon). It reports the floor product (with a per-face breakdown for mixed packs), wall field, each décor/accent product, and a grand total.

## Cropping + baking — `bake_tiles.py`

`python3 bake_tiles.py` (needs Pillow) does two things:
1. **Auto-crops the white photo border** off every `tiles/*.jpg` referenced by the HTML (writes to `tiles/cropped/`, or `--inplace` to overwrite with originals backed up to `tiles/_originals/`). Cropping detects the content bbox via a thresholded + eroded mask, with a `--max-trim` safety clamp. This both removes the fake-grout frame on the wall tile and reveals that the décor/floor shots are 2:1 (white letterbox top/bottom removed).
2. **Bakes a self-contained `bathrooms_baked.html`** — every `tiles/<file>.jpg` string in the HTML is replaced by a base64 JPEG `data:` URI of the cropped image, so the result needs no `tiles/` folder and opens straight off `file://`. ~1.2 MB.

`bathrooms.html` stays the editable source (loads from `tiles/`); `bathrooms_baked.html` is the generated, portable artifact (git-ignored — regenerate with the script). Re-run after changing any tile or the HTML. **Note:** images downloaded from praktiker's media API need the `?context=…` token from the product page HTML, and re-encode with `sips` if a browser reports the JPG as not-found (one raw download was subtly malformed).

## Architecture

- **CONFIG** holds `view`, `active`, `texture`, and `A`/`B` bath objects built by `bathCfg()`. Each wall is built by `wallCfg()` (tileW/H, orient, bond, grout, offsets, band rows/height/tile, accent).
- **GUI_SCHEMA is built programmatically** by `buildSchema(tab)` so the four walls stay DRY — there is no static schema array.
- **Geometry is built from a single primitive:** `poly(group, mat, pts, uvs)` — a fan-triangulated convex polygon with explicit UVs. Used for every tile, the grout backing, and the screed. Cut tiles keep the pattern continuous because UVs are computed from each clipped vertex's position within the tile.
- **Room shape:** `roomPolygon(R)` returns a CCW point list (4 corners, or 6 for the notch). `floorRects(R)` returns 1–2 axis-aligned rectangles covering the floor (the notch splits the L into two rects).
- **Floor tiling** (`buildFloorTiles`): a rotated/offset grid clipped to each floor rect via Sutherland–Hodgman (`clipToRect`). Handles angle + L-shape.
- **Wall tiling** (`buildWall`): each polygon edge → a wall in local (u=along, v=up) space. Tiles are axis-aligned rects, clipped to the wall and **carved around the door** with `rectSubtract`. Each polygon edge is classified to a cardinal (N/E/S/W) via its outward normal, so it uses that cardinal's wall config (notch sub-walls inherit from the nearest cardinal). The door goes on the **longest** edge of the chosen cardinal.
- **3D vs Unfold** differ only in the wall's vertical direction: `(0,1,0)` in 3D, or the outward horizontal normal (folded flat) in unfold. One flag, no separate geometry.
- **Groups:** `floor`, `walls`, `trim` (door leaf), `base` (grout backing + screed). `frameCamera()` repositions the orbit per bath + view.

## Effect / décor tiles

- **Band:** `bandRows` (0/1/2) of décor at `bandHeight` (m), tile chosen by `bandTile` (0 patchwork, 1 olas, 2 plain). Selected by row v-centre proximity to the band height.
- **Accent wall:** `accent` (0 off, else décor index +1) tiles the **whole** wall in that décor (overrides the band).

## Known limitations / TODO

- Texture is not rotated for portrait (vertical) tile orientation — the near-isotropic concrete look hides the stretch; revisit if directional tiles are added.
- In the **Unfold** view of the notched bath, the two notch sub-walls fold into the notch area and can overlap their neighbours slightly. Readable, but not a clean net.
- No ceiling; the room is open-topped for visibility.
- No per-tile manual override, no export, no tile-count/m² cut-list beyond the HUD estimate.
- Door is a flat recessed leaf (no frame/handle modelling).