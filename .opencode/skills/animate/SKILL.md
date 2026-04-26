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

## Animation Requirements

- Use p5.js global mode unless the project already uses instance mode.
- Include `setup()` and `draw()`.
- Make the canvas responsive with `createCanvas(windowWidth, windowHeight)` and implement `windowResized()`.
- Use time-based or frame-based motion so the scene continuously animates.
- Keep the sketch deterministic enough to be recognizable, but use subtle randomness/noise where it improves organic motion.
- Avoid external assets unless the user explicitly asks for them.
- Prefer concise, readable code over framework-heavy structure.
- Add short comments only for non-obvious animation techniques.

## Visual Direction

Translate the scene description into a clear visual composition:

- Establish a background, subject, motion, and atmosphere.
- Use color palettes that match the mood of the story segment.
- Layer elements from background to foreground for depth.
- Include at least one meaningful animated detail, such as drifting particles, rippling water, moving stars, swaying grass, blinking lights, or character motion.
- Make the animation work on desktop and mobile canvas sizes.

## Workflow

1. Infer the scene from the user’s prompt or story segment.
2. Create or update the p5.js HTML animation file.
3. If browser preview is available, open the generated file in the browser.
4. Report the file path and briefly describe the animation.

## Minimal Template

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>p5.js Animation</title>
  <style>
    html, body { margin: 0; height: 100%; overflow: hidden; background: #050712; }
    canvas { display: block; }
  </style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.4/p5.min.js"></script>
</head>
<body>
  <script>
    function setup() {
      createCanvas(windowWidth, windowHeight);
    }

    function draw() {
      background(5, 7, 18);
    }

    function windowResized() {
      resizeCanvas(windowWidth, windowHeight);
    }
  </script>
</body>
</html>
```
