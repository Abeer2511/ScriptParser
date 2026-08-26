---
name: flow-clip-prompt-generator
description: 'Turn a Google-Flow-exported script (the Markdowns/<name>.md + Images/Character|Location|Prop|Frame folder structure produced by a .NET storyboard parser) into a pack of Google Flow / Omni Flash video-generation prompts, one per shot, each snapped to an allowed clip length (4/6/8/10s), correctly referencing real `@nametag` images (Character and Location only, with Frames used as ingredients and Props ignored), and asking first about voice-over handling and aspect ratio.'
argument-hint: 'Script name (the <script_name> folder under your project root, e.g. Script1 or "WHAT THE LIMIT WAS FOR")'
---

# Google Flow Clip Prompt Generator

## What this does

Reads a script folder built by the user's .NET exporter —

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

## Key Platform Constraints & Rules

1. **Frames as Ingredients**: In Google Flow, you cannot select both "Ingredients"
   (references) and a separate "Starting Frame" in the same generation. Therefore,
   the frame image for each shot is used as an **ingredient** in `**References:**`.
   No separate `**Starting frame:**` field is output.
2. **Characters and Locations ONLY**: Only Character references (e.g. `@Elara`)
   and Location references (e.g. `@Lab`) are added as reference ingredients in
   `**References:**` and tagged with `@` in prompts.
3. **Narrator is VO ONLY**: Narrators are non-diegetic audio/voice-over and never
   appear on-screen. Do NOT include `@Narrator` in `**References:**` or tag
   `@Narrator` in visual action text. Narrator belongs strictly in the `Audio:`
   directive or Dialogue/VO field.
4. **Ignore Props Assets**: Props are already baked into the generated frame
   images. Do NOT include Props in `**References:**`, and do NOT tag props with
   `@` in prompt text (write "monitors", "locked cabinet", "tea" in plain prose).
5. **Snap Durations**: Allowed clip durations are exactly {4, 6, 8, 10} seconds.

## Procedure

### Step 1 — Get the script name and locate the folder
If not given via the argument, ask for `<script_name>`. Look for
`./Exports/<script_name>/Markdowns/<script_name>.md`. Confirm the `Images/`
subfolders exist.

### Step 2 — Parse the script (deterministic)
Run:
```bash
python3 <skill_dir>/scripts/parse_script.py <root>/Exports/<script_name>/Markdowns/<script_name>.md <root>/Exports/<script_name>/VideoPrompts/_script_data.json
```
Extracts title, characters, locations, props, full-story beats, and scenes/shots.

### Step 3 — Match assets to real nametag images (deterministic)
Run:
```bash
python3 <skill_dir>/scripts/scan_nametags.py <root>/Exports/<script_name>/VideoPrompts/_script_data.json <root>/Exports/<script_name>/Images <root>/Exports/<script_name>/VideoPrompts/_nametag_map.json
```
Matches Character, Location, and Prop names against files in `Images/` and indexes
the `Images/Frame` files.

### Step 4 — Align dialogue to shots
Walk the Full-Story narrative beats and Scenes in order, assigning dialogue lines
to the relevant shots based on character presence and visual context.

### Step 5 — Ask about voice-over handling
Ask the user regarding spoken audio:
- Default `deferred` for Narrator (non-diegetic voice-over added in post).
- Default `native audio` for on-screen characters.

### Step 6 — Ask aspect ratio
Ask once for the pack: `16:9` (default landscape), `9:16` (vertical), or `1:1`.

### Step 7 — Generate prompt pack & clip files
Run the generic prompt generator:
```bash
python3 <skill_dir>/scripts/generate_pack.py <root>/Exports/<script_name> --ar 16:9
```
This automatically:
- Inserts Frame nametags as ingredient references in `**References:**`.
- Filters references to Character and Location nametags only (excluding Narrator).
- Strips `@` from props in visual prompt text.
- Generates master markdown in `Exports/<script_name>/VideoPrompts/<script_name>-flow-prompts.md`.
- Generates individual clip files in `Exports/<script_name>/VideoPrompts/clips/`.

### Step 8 — Validate the pack
Run:
```bash
python3 <skill_dir>/scripts/validate_pack.py <root>/Exports/<script_name>/VideoPrompts/<script_name>-flow-prompts.md <root>/Exports/<script_name>/VideoPrompts/_nametag_map.json
```
Ensures:
- Durations strictly in {4, 6, 8, 10}s.
- Consistent aspect ratio.
- No `@Prop` or `@Narrator` references.
- No `**Starting frame:**` fields.
- All `@nametag` references resolve to real Character/Location/Frame images.

### Step 9 — Summarize for the user
Report total clip count, runtime, and output locations.
