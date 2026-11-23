# Narrated Code Walkthrough

An AI coding skill that turns a repository, pull request, or feature into an interactive HTML explanation. Learn the flow in plain language, inspect the actual source, and optionally listen while the guide highlights the lines being explained.

- A focused reading path, with a default budget of 15 minutes.
- Clickable flow diagrams, annotated source, optional questions, and a file explorer.
- Optional local narration with measured cue timing, transcripts, seeking, playback speed, and exact line following.
- Editable guide JSON and one HTML file with styles, scripts, source, and optional audio embedded for offline use.
- A recorded source revision; local edits are included only when explicitly requested.

## Install as a skill

For Codex, clone into your skills directory:

```sh
git clone https://github.com/AryamanCoupa/narrated-code-walkthrough.git \
  ~/.codex/skills/narrated-code-walkthrough
```

Then ask your coding assistant:

```text
Use $narrated-code-walkthrough to explain this feature in 15 minutes.
I am new to this codebase. Use simple language and examples only where helpful.
Make it text-only for now.
```

For narration, provide an existing local voice setup or ask the assistant to inspect one you identify. The skill asks only for missing information that affects the result.

Other assistants that support `SKILL.md` can load [the skill instructions](SKILL.md) and use the same files. Installation varies by assistant.

## Build the fictional example

The HTML builder requires Python 3.10+ and Git, with no third-party Python packages. Run these commands from this repository. They create a temporary Git repository containing only the fictional example:

```sh
example_repo="$(mktemp -d)"
cp assets/example/source/app.py "$example_repo/app.py"
git -C "$example_repo" init -q
git -C "$example_repo" add app.py
git -C "$example_repo" -c user.name='Example' \
  -c user.email='example@example.invalid' -c core.hooksPath=/dev/null \
  -c commit.gpgsign=false commit -qm 'Add fictional example'

python3 scripts/build_walkthrough.py \
  --guide assets/example/guide.json --repo "$example_repo" \
  --output output/index.html
```

Open `output/index.html` in a modern browser. This example is text-only; its narration script can be used with the optional adapter below. The builder reads selected source files without importing or running the application.

## Add local narration

Voice generation is optional. The included adapter supports an existing Kokoro ONNX environment with `kokoro-onnx`, `onnxruntime`, `numpy`, and `soundfile`, plus model and voice files you supply. MP3 output also needs `ffmpeg`; WAV output does not.

See [narration setup](references/narration.md) for commands and the timing manifest. Models, voice files, recordings, and generated audio are not included. Other local voice tools can produce the same measured timing manifest.

Press Play in the HTML to listen. “Follow narration” moves the highlight to the current code lines while keeping nearby context visible. Turn it off to browse independently. Use Transcript to jump to a spoken segment.

## Author your own guide

Start with [the small example](assets/example/guide.json) and [the guide format](references/guide-format.md). Choose source files explicitly, explain the user-visible behavior first, and trace one request through the code. Use a source anchor that matches one line or specify exact line numbers.

The builder validates source references and rejects stale or overlapping narration cues. Add `--base <commit>` for PR changes, `--worktree` for local source, and `--overwrite` to replace an existing output.

## Review before sharing generated guides

This repository contains only generic tooling and a fictional example. A guide you generate can embed the **complete selected source files**, diffs, explanations, and audio, even when a chapter displays only a few lines. Review the HTML and JSON before sharing them. Keep private source, credentials, customer data, model files, and recordings out of this repository.

The builder and renderer make no network requests. The optional adapter uses local model files; installing tools is a separate step. This does not mean every external voice setup is offline. The public-bundle check detects selected common mistakes, not every secret or proprietary material.

Run the bundle check before committing or pushing. A CI check runs after upload and cannot undo a disclosure.

## Checks

```sh
python3 -B scripts/test_build_walkthrough.py
python3 -B scripts/test_public_bundle.py
node --check assets/walkthrough.js
node --test scripts/test_renderer.cjs
python3 -B scripts/check_public_bundle.py
```

The tests cover source snapshots, explicit local edits, removed files, source references, HTML escaping, embedded audio, timing validation, source versus diff colors, and flow-node source links. GitHub Actions runs the same checks. Browser testing remains necessary for real playback, seeking, internal code scrolling, keyboard use, and narrow screens.
