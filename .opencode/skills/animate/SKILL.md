---
name: animate
description: Generate self-contained p5.js animations from scene descriptions, suitable for story segments and browser preview.
license: MIT
compatibility: opencode
metadata:
  library: p5.js
  output: html
---

## Purpose

Use this skill when the user asks for an animation, an animated story scene, or a visual sequence that should be rendered with p5.js.

## Output

Create a self-contained HTML file that loads p5.js from a CDN and contains the sketch code inline. Prefer writing files under `animations/` with a short, descriptive kebab-case name, for example `animations/moonlit-forest.html`.


## Workflow

Refer to the p5.js docs at https://p5js.org/reference/

1. Infer the scene from the user’s prompt or story segment.
2. Create or update the p5.js HTML animation file.
3. If browser preview is available, open the generated file in the browser.
4. Report the file path and briefly describe the animation.

