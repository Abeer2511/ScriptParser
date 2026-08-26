---
name: flow-clip-prompt-generator
description: 'Turn a Google-Flow-exported script (the Markdowns/<name>.md + Images/Character|Location|Prop|Frame folder structure produced by a .NET storyboard parser) into a pack of Google Flow / Omni Flash video-generation prompts, one per shot, each snapped to an allowed clip length (4/6/8/10s), correctly referencing real `@nametag` images, and asking first about voice-over handling and aspect ratio. Use this whenever the user mentions Google Flow, a storyboard export, nametag/@-reference images, Omni Flash, a script with Markdowns/Images folders, or asks to "generate video prompts from my script folder" / "make the Flow clip pack". This is a different pipeline from the ai-video-content / video-prompt-generator skills (which write scripts from scratch and have no real reference images) — use this one whenever an existing Markdowns+Images project folder is involved.'
argument-hint: 'Script name (the <script_name> folder under your project root, e.g. Script1)'
---

# Google Flow Clip Prompt Generator

## What this does

Reads a script folder built by the user's own .NET exporter —

```
<root>/Exports/<script_name>/Markdowns/<script_name>.md
<root>/Exports/<script_name>/Images/Character/
<root>/Exports/<script_name>/Images/Location/
<root>/Exports/<script_name>/Images/Prop/
<root>/Exports/<script_name>/Images/Frame/
```

— and produces a **Video Prompt Pack**: one self-contained, copy-paste-ready
Google Flow / Omni Flash prompt per shot, with correct `@nametag` asset
references, a duration snapped to {4, 6, 8, 10}s, and an explicit
voice-over decision, at the aspect ratio the user chooses.

This skill assumes bash/file access to the workspace (Claude Code, not
claude.ai chat) since it needs to list the Images folders and run its
bundled parsing scripts.

## Assumptions — check these against the user's actual Flow setup

These are taken from how the user described their pipeline, not verified
platform documentation. Confirm with the user if anything looks off, and
adjust the relevant script/step rather than silently overriding what you
observe on disk:
- A nametag is exactly an image's filename minus its extension (e.g.
  `Elias.png` → `@Elias`). Never reformat, abbreviate, or "clean up" a
  nametag — copy it byte-for-byte from the actual filename.
- Allowed clip durations are exactly {4, 6, 8, 10} seconds — no other value.
- "Omni Flash" prompts are plain natural-language text (scene, action,
  camera, lighting, framing, duration, audio directive) with inline
  `@nametag` references — not JSON or a structured schema.

## Procedure

### Step 1 — Get the script name and locate the folder
If not given via the argument, ask for `<script_name>`. Then look for
`./Exports/<script_name>/Markdowns/<script_name>.md` (or `./<script_name>/Markdowns/<script_name>.md`)
relative to the current workspace root. If it's not there, run a recursive search
(`find . -iname "<script_name>.md"`) and derive the root from wherever it's
found (two levels above the `Markdowns` folder). If you find more than one
candidate, or none, tell the user what you found and ask them to confirm
the path rather than guessing.

Confirm the four `Images/` subfolders exist alongside it; note which ones
are missing or empty (that's fine — just means those categories have no
reference images yet, and everything in them will be described inline).

### Step 2 — Parse the script (deterministic)
Run:
```bash
python3 <skill_dir>/scripts/parse_script.py <root>/Exports/<script_name>/Markdowns/<script_name>.md <root>/Exports/<script_name>/VideoPrompts/_script_data.json
```
This extracts the title, Characters/Locations/Props asset lists, the
Full-Story narrative beats (in scene-id order, with dialogue attributed to
each speaker), and the Scenes → Shots breakdown (Visual/Audio/Motion/Assets
per shot). Read the script's printed summary and any warnings — a warning
usually means an unusual heading format; open the .md file and check
before proceeding if the shot/scene counts look wrong.

### Step 3 — Match assets to real nametag images (deterministic)
Run:
```bash
python3 <skill_dir>/scripts/scan_nametags.py <root>/Exports/<script_name>/VideoPrompts/_script_data.json <root>/Exports/<script_name>/Images <root>/Exports/<script_name>/VideoPrompts/_nametag_map.json
```
This cross-references every Character/Location/Prop name against the actual
files in `Images/`. Report back to the user, concisely (don't dump raw
JSON):
- How many assets matched cleanly.
- **Ambiguous** matches (two+ files could be the same asset) — list them
  and ask the user to pick the right file for each.
- **Unmatched assets** (no image at all) — tell the user these will be
  described inline in prose instead of referenced by `@nametag`, and give
  them a chance to say "actually it's called X.png" for any of them before
  you lock that in.
- The raw `frame_index` list (Images/Frame files) — you'll match these to
  individual shots yourself in Step 7 using filename/title similarity;
  mention up front if the folder is empty or the names don't look
  shot-addressable, so the user isn't surprised frame references are sparse.

Update `_nametag_map.json` by hand (or re-run the script after the user
renames a file) once ambiguities are resolved, so Step 8's Prompt/validate
steps use the corrected map.

### Step 4 — Align dialogue to shots (judgment call — do this yourself, then confirm)
The Full-Story beats carry `scene-id` and exact dialogue; the Scenes/Shots
breakdown doesn't carry scene-id, so there's no guaranteed 1:1 link. Align
them yourself:
1. Walk the Full-Story beats in order and the Scenes in order together,
   matching each Scene's heading to the next Full-Story beat with the same
   INT/EXT + location + time-of-day heading (scenes recur, e.g. multiple
   "INT. PATENT OFFICE - DAY" beats — take them in sequence, don't just
   match on the first occurrence every time).
2. Within an aligned group, assign each dialogue line to whichever Shot's
   Visual/Motion text most plausibly depicts that character speaking or
   that beat of narration; when nothing clearly fits, default to the
   scene's first shot.
3. Show the user your proposed line→shot assignments in one short list
   before moving on ("NARRATOR line 'What if...' → Scene 2 Shot 01" etc.)
   and let them correct any of it. This is the one genuinely ambiguous
   step in the pipeline — don't skip the confirmation to save time.

If the script has no dialogue at all, skip this step and say so.

### Step 5 — Ask about voice-over handling (dynamic, based on what's actually in the script)
From the aligned dialogue, list every character who has lines, with a line
count, e.g.:
```
NARRATOR — 8 V.O. lines (non-diegetic)
ELIAS    — 3 spoken lines (on-screen/diegetic)
```
Ask the user, in one batched question covering every character found —
don't ask turn-by-turn per character:
"For each character with dialogue, should Flow generate the spoken audio
natively in the clip, or should the clip stay silent/ambient so you add
narration/VO separately afterward?"
Offer a sensible default per character type (non-diegetic V.O. narrators
usually get added in post — default "deferred"; on-screen speaking
characters usually benefit from native lip-synced audio — default
"native") and let the user override any of them, including "skip this
character's lines entirely" if they don't want that dialogue in the pack
at all. If the script has no dialogue, skip this question entirely.

### Step 6 — Ask aspect ratio
Ask once, applies to the whole pack: 16:9 (landscape), 9:16 (vertical/
Reels/Shorts), 1:1 (square), or a custom ratio the user names.

### Step 7 — Assign durations and write each clip prompt
Read `references/output_template.md` now for the exact duration-snapping
rules, the Voice-over field states, the required Prompt-block content, the
frame-reference convention, and the full clip/header format — follow it
precisely rather than improvising a different layout.

Work scene by scene, writing each scene's clip blocks to the output file
as you finish them (see Step 8) rather than holding the whole pack in
memory until the end — this matters for longer scripts (dozens of scenes)
so nothing gets lost or truncated partway through a long generation.

### Step 8 — Assemble the pack file(s)
Write the master pack to:
```
<root>/Exports/<script_name>/VideoPrompts/<script_name>-flow-prompts.md
```
using the header + per-scene + per-clip format from
`references/output_template.md`.

Also write one plain-text file per clip (no markdown, just the Prompt
block's text, ready to paste straight into Flow) to:
```
<root>/Exports/<script_name>/VideoPrompts/clips/Scene<NN>_Shot<NN>[a|b].txt
```
Ask the user up front in Step 6 whether they want the per-clip .txt files
too, or only the master pack — default to producing both since it costs
little and saves the user from copy-splitting the master file by hand.

If `<script_name>-flow-prompts.md` already exists from a previous run, ask
whether to overwrite it, save as a new version (`-v2`), or only regenerate
specific scenes — don't silently clobber prior work.

### Step 9 — Validate before handing back (deterministic)
Run:
```bash
python3 <skill_dir>/scripts/validate_pack.py <root>/Exports/<script_name>/VideoPrompts/<script_name>-flow-prompts.md <root>/Exports/<script_name>/VideoPrompts/_nametag_map.json
```
This catches: durations outside {4,6,8,10}, aspect ratio drift between
clips, missing required fields, and any `@nametag` that doesn't correspond
to a real matched image or frame file (a strong signal you invented or
mis-copied a reference). If it reports FAIL, fix the flagged clips and
re-run — don't hand back a pack that fails validation.

### Step 10 — Summarize for the user
Report: total clip count, total runtime, where the files are, which assets
are still undeclared/described-inline (so the user knows what still needs
art), and the voice-over plan actually used. Don't repeat the whole pack
back in chat — it's already on disk.

## Other things worth handling

- **No dialogue in the script at all**: skip Steps 4–5 cleanly; note it in
  the pack header's Voice-over plan line as "None — no dialogue in script."
- **An asset referenced in a shot but never declared** in
  Characters/Locations/Props (parse_script.py flags this as a warning):
  treat it like any other unmatched asset — describe it inline — and
  mention the inconsistency to the user in case it's a typo in their
  export.
- **Re-running for a later episode/script in the same project**: nametags
  are scoped per script folder here (unlike the video-prompt-generator
  skill's cross-episode voice lock), so there's no persistent lock file to
  maintain — each script's Images folder is self-contained.
- **Very large scripts**: process and write scene-by-scene (Step 7) to
  avoid losing work; if the model context is getting long, it's fine to
  finish and validate one scene's clips, report brief progress, and
  continue rather than trying to hold the entire pack in one pass.
- **Possessive/punctuated asset names** (e.g. "Elias's Apartment"): the
  nametag scanner already normalizes apostrophes/case/spacing for matching
  — trust its `matched`/`ambiguous`/`unmatched_assets` output rather than
  re-guessing matches yourself.
