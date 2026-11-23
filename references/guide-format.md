# Editable guide format

The root has `version: 1`, `title`, `summary`, `audience`, `minutes`, `files` and
`chapters`. Chapter minutes must total `minutes`. IDs use lowercase letters, digits
and hyphens, starting with a letter. See `../assets/example/guide.json`.

Each file has a repository-relative `path`, `purpose`, optional `details` and
`group`. Source is read from the selected Git revision, without importing it.
`--base` supplies PR diffs and removed-file source; `--worktree` explicitly opts
into local source and labels it accordingly.

Each chapter has `id`, `title`, `minutes`, `summary`, `blocks`, optional `narration`
and optional `quiz`. Blocks have a unique `id` within the chapter and a `type`:

| Type | Fields |
|---|---|
| `text` | Optional `title`, plain `text` (paragraphs separated by newlines) |
| `code` | Optional `title`, `file`, `anchor` or `line`, optional `lines`/`end_line`, `explanation` |
| `flow` | `title`, `items` with `id`, `title`, `text`, optional source reference |
| `cards` | Optional `title`, `items` with `title`, `text` |

All prose is plain text. Anchors must match exactly one source line. Refine an
ambiguous anchor or use exact 1-based line numbers. Ranges are inclusive and must
exist. Static code blocks default to 12 lines; narration defaults to one focused
line with nearby context shown by the renderer.

Narration segments have `text`, `label` and either `target` (a block ID in the same
chapter, optionally `node` for a flow item) or a source reference (`file` plus
`anchor`/`line`, optional `lines`/`end_line`). A file must appear in `files`.
One spoken idea should match one focus range. Explain identifiers naturally in
speech while showing their exact spelling in code.

An optional quiz has `question`, `choices` (2–5 strings), zero-based `answer` and
`explanation`. Examples and quizzes are optional teaching tools, not quotas.

## Audio manifest

The local adapter creates `narration.json` with a `script_hash` computed by the
builder's `script_hash()` helper. It binds audio to chapter IDs/narration segments.
`chapters[id]` contains `file` (relative to the manifest), `seconds`, and ordered
`cues`: `{segment: 0, start: 0.0, end: 4.25}`. Every segment appears exactly once;
times are measured media seconds at 1×, ordered, nonoverlapping and in bounds.

Other local TTS/alignment tools can produce the same manifest. Do not invent
timestamps. The builder embeds the audio and validated timing into one HTML file.
