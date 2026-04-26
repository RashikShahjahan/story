---
name: animate
description: Generate self-contained p5.js animations from scene descriptions, suitable for story segments and browser preview.
license: MIT
compatibility: opencode
metadata:
  library: p5.js
  output: html
  sound_tool: search-soundtracks
---

## Purpose

Use this skill when the user asks for an animation, an animated story scene, or a visual sequence that should be rendered with p5.js.

## Output

Create a self-contained HTML file that loads p5.js from a CDN and contains the sketch code inline. Prefer writing files under `animations/` with a short, descriptive kebab-case name, for example `animations/moonlit-forest.html`.


## Workflow

Refer to the p5.js docs at https://p5js.org/reference/

1. Infer the scene from the user’s prompt or story segment.
2. Use the `search-soundtracks` tool to find one relevant Openverse audio track for the scene mood, setting, or ambience. Prefer playable `audio_url` results with clear Creative Commons attribution.
3. Create or update the p5.js HTML animation file.
4. Include the selected soundtrack when it improves the scene. Add `p5.sound` if using `loadSound`, keep playback controls hidden unless the user asks for them, and make the animation continue silently if audio loading or playback fails.
5. Attempt to autoplay the soundtrack as soon as the animation starts so sound runs with the visuals. Because browsers can block unmuted autoplay, also add a subtle click/tap/key fallback that starts audio without showing media controls.
6. Include the track attribution in the HTML, either in a small readable footer/caption or another visible attribution area.
7. If browser preview is available, open the generated file in the browser.
8. Report the file path, the selected soundtrack, and briefly describe the animation.
