OmniVoice TTS is configured to run under Python 3.13 because torch==2.8.0 has no CPython 3.14 wheel; dependency resolution and `omnivoice` import were verified with `uv run --python 3.13`.
§
OmniVoice TTS auto voice works for Bangla when `instruct` is left empty; a freeform `instruct` value can fail in `_resolve_instruct`.
