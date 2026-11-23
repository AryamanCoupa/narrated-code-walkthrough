# Narration tooling

Use an existing user-provided setup first. Inspect its scripts/environment and ask
for voice preference only if it matters and is unknown. Keep machine-specific
paths in command arguments, not in this skill or a shared artifact.

The bundled Kokoro adapter expects an existing Python environment with
`kokoro-onnx`, `onnxruntime`, `numpy` and `soundfile`, plus local ONNX/voice files.
It uses CPU inference and downloads no models. MP3 output uses installed `ffmpeg`;
`--format wav` avoids that dependency but produces larger HTML files.

```sh
/path/to/tts/python /path/to/skill/scripts/synthesize_kokoro.py \
  --guide /path/to/guide.json --output-dir /path/to/output/voice \
  --model /path/to/model.onnx --voices /path/to/voices.bin --voice am_michael

python /path/to/skill/scripts/build_walkthrough.py \
  --guide /path/to/guide.json --repo /path/to/repo --revision HEAD \
  --audio /path/to/output/voice/narration.json \
  --output /path/to/output/index.html --overwrite
```

Do not assume the example voice exists; inspect available voices. The adapter
synthesizes semantic segments separately, records sample boundaries and joins them
with short pauses. Completed chapters are cached against script, voice and model
metadata for resuming. Use accurate audio boundaries or forced alignment for other
engines. Do not silently substitute a browser voice with guessed timing.

Cloud voice services require authorization to send that source-derived narration
and incur costs. Keep credentials, recordings, model weights and generated customer
narration out of the skill distribution.

Test two adjacent segments that explain different lines of the same component.
The code context should remain in place while the highlight moves, and the code
pane should scroll only when the active line is no longer visible. Test seeking,
replay, speed changes, follow-off/on, transcripts and chapter transitions too.
