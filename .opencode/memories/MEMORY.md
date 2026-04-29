Kokoro TTS is configured via the local `kokoro-tts` OpenCode tool, running `hexgrad/Kokoro-82M` through `uv run --python 3.13` with `kokoro>=0.9.4`, `soundfile`, `numpy`, and the English spaCy model wheel.
§
For local animation audio, native HTMLAudioElement is more reliable than p5 createAudio; use click/tap/key fallback when browser autoplay blocks narration.
§
When displaying multi-segment animated stories, avoid opening separate autoplaying HTML files simultaneously because their narration can overlap; use one sequential combined page or otherwise stop prior audio.
