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
      └─ Posts (foundation.thickness to fndTop + posts.height)
          └─ Beams (postTop to postTop + beams.height)
              └─ Ridge supports (beamTop to beamTop + ridge.supportHeight)
                  └─ Ridge beam (top of supports + ridge.size/2)
                      └─ Rafters slope from ridge down to beams
                          └─ Roof panels on top of rafters
```

Key derived values used across builders:
- `postTop = CONFIG.foundation.thickness + CONFIG.posts.height`
- `beamTop = postTop + CONFIG.beams.height`
- `ridgeTop = beamTop + CONFIG.ridge.supportHeight + CONFIG.ridge.size/2`

### Post grid

Posts are arranged in a rectangular grid defined by `posts.gridCols` (along X) × `posts.gridRows` (along Z). The function `getPostPositions()` returns an array of `{x, z, col, row}` objects, centered on the origin.

- `gridCols` controls how many columns along the long (X) axis. Default 3.
- `gridRows` controls rows along the short (Z) axis. Default 2.
- `spacingX` / `spacingZ` control the distance between adjacent posts.

Beams and ridge elements iterate over gridCols/gridRows to match.

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
- Foundation slab does not automatically resize to match post grid + overhang.

## Dependencies

- **Three.js r128** loaded from CDN: `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js`
- No other external dependencies. No npm, no build tools.

## Reference

- Original plans: `16x20_pavilion_plans.pdf` from MyOutdoorPlans.com
- Brick standard: Bulgarian standard brick 250×120×65mm, mortar joint 10mm
- All structural dimensions derived from the PDF's cut list and step diagrams, converted to metric