---
name: narrated-code-walkthrough
description: Create a plain-language interactive HTML code guide for a repository, PR or feature, with annotated source and optional local narration synchronized to exact code lines.
---

Create a learning artifact, without changing the application being explained.
Deliver an editable guide JSON and a self-contained HTML file. Add narration when
requested using available voice tooling; never describe silent output as narrated.

## Ask only what is missing

Use prior conversation and inspect the provided repo/PR first. Ask concise questions
only when answers would materially change the result. Bundle up to three:

- Which repository, PR, feature or request flow should the guide cover?
- Who is the reader, and how many minutes do they have? Default to a developer new
  to this codebase and a 15-minute reading path.
- If voice is wanted, which existing local TTS setup or voice should be used?
  Inspect user-provided locations; do not assume machine-specific paths or models.

Do not ask again for answered preferences. Continue independent source inspection
while awaiting optional answers. Respect text-only requests and chosen scope.

## Teach in easy language

Start with what a user sees, then trace one request through the code. Explain what
each component does, why it exists, what it receives and what it hands to the next
component. Use short sentences and explain technical terms on first use. Explain
the idea before showing syntax. Add a small example only when it makes the idea
clearer; label invented examples. Do not force an example into every chapter.

Keep the timed path focused; put exhaustive source in the explorer. Derive chapter
count and reading budgets from the goal rather than always using a fixed layout.
Read applicable repo instructions. Verify claims against actual source, including
errors and cleanup. Record the commit/base, or explicitly identify working-tree
source. Use the available GitHub CLI/connector for PR context. Do not execute the
target application merely to explain its source.

## Author and build

Read [references/guide-format.md](references/guide-format.md) and author `guide.json`.
The HTML builder uses Python 3.10+ and the standard library; voice tooling is optional.
Select source files deliberately and give each a plain-language purpose. Do not
include secrets/environment files or an unrelated private repository. The shared
skill distribution itself must contain no user source, voice assets or model weights.

```sh
python /path/to/skill/scripts/build_walkthrough.py \
  --guide /path/to/guide.json --repo /path/to/repo --revision HEAD \
  --output /path/to/output/index.html
```

Add `--base <base-commit>` for PR diffs, `--worktree` for explicitly requested local
edits, and `--overwrite` when rebuilding an existing artifact. A complete small
example lives at [assets/example/guide.json](assets/example/guide.json).

For voice, read [references/narration.md](references/narration.md). Generate one
semantic segment per idea and measure actual audio boundaries. Never estimate
timing from word counts. Bind narration to the authored script; reject stale audio.
Use exact source ranges: split a spoken property list into separate timed segments
instead of highlighting the same three lines while describing different fields.

The renderer must preserve nearby code context, move the exact line highlight and
scroll inside its code pane. Do not rebuild the pane or jump the whole page for
every small line change. Wrap narrated code on narrow screens. Follow narration
starts enabled with an obvious off switch. Seeking, replay, speed changes and
chapter navigation must stay synchronized without stealing keyboard focus.

## Verify and share

Run the bundled tooling tests when changing the skill's scripts:

```sh
python /path/to/skill/scripts/test_build_walkthrough.py
```

Check every chapter/reference in a browser. Test real playback across a cue
boundary, forward/back seeking, exact line highlights and internal pane scrolling,
follow-off/on, transcript jumps, chapter changes, mobile and keyboard controls.
Report verification limits honestly. A local demo is not a production run.

Provide the HTML, editable JSON, source snapshot identity and brief playback steps.
Embed audio for offline use. Distinguish measured audio length from the reading
budget. If serving locally, bind to localhost and use a free port. Publishing,
committing or pushing the artifact requires the user's task authorization.
