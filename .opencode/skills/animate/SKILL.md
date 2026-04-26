---
name: animate
description: Generate self-contained p5.js animations from scene descriptions, suitable for story segments and browser preview.
license: MIT
compatibility: opencode
metadata:
  library: p5.js
  output: html
  sound_tools: search-soundtracks, kokoro-tts
---

## Purpose

Use this skill when the user asks for an animation, an animated story scene, or a visual sequence that should be rendered with p5.js.

## Output

Create a self-contained HTML file that loads p5.js from a CDN and contains the sketch code inline. Prefer writing files under `animations/` with a short, descriptive kebab-case name, for example `animations/moonlit-forest.html`.


## Workflow

Refer to the p5.js docs at https://p5js.org/reference/

1. Infer the scene from the user’s prompt or story segment.
2. If the scene includes story narration and no narration audio path has been provided, use the `kokoro-tts` tool to generate a WAV file for the exact story text before creating the animation.
3. Use the `search-soundtracks` tool to find one relevant Openverse audio track for the scene mood, setting, or ambience when background audio improves the scene. Prefer playable `audio_url` results with clear Creative Commons attribution.
4. Create or update the p5.js HTML animation file.
5. Include narration audio when available. Keep playback controls hidden, start narration with the visuals, and make the animation continue silently if audio loading or playback fails.
6. Include the selected soundtrack only when it does not compete with narration. If both narration and soundtrack are used, keep the soundtrack lower than the voice. Add `p5.sound` if using `loadSound`, keep playback controls hidden unless the user asks for them, and make the animation continue silently if audio loading or playback fails.
7. Attempt to autoplay narration and soundtrack as soon as the animation starts. Because browsers can block unmuted autoplay, also add a subtle click/tap/key fallback that starts audio without showing media controls.

8. Report the file path, narration audio path if used, selected soundtrack if used, and briefly describe the animation.
