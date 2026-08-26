---
name: process-script
description: 'End-to-end automated orchestration pipeline for Google Storyboard scripts: validates raw JSON in Scripts/, runs .NET extractor to populate Exports/<script_name>/ (Markdowns and Images), scans nametags, aligns dialogue/VO, generates character voice profiles (Exports/<script_name>/VoiceProfiles.md), generates Google Flow video prompts (frames as ingredients, Character/Location refs only, props ignored), and runs automated pack validation.'
argument-hint: 'Script name (the .json filename in Scripts/, e.g. Script1 or "WHAT THE LIMIT WAS FOR")'
---

# Process Script Pipeline Orchestrator

## What this does

Orchestrates the entire Google Storyboard to Google Flow video prompt pack generation pipeline inside the unified `ScriptParser` workspace:

1. **Validates & Extracts**: Takes `<script_name>`, checks `f:\ScriptParser\Scripts\<script_name>.json`, and executes the .NET parser to create:
   - `Exports/<script_name>/Markdowns/<script_name>.md`
   - `Exports/<script_name>/Images/{Character,Location,Prop,Frame}/`
2. **Parses & Matches Nametags**: Runs deterministic scripts to produce `_script_data.json` and `_nametag_map.json`.
3. **Generates Voice Profiles**: Creates comprehensive acoustic profiles, emotional states, and TTS prompts in `Exports/<script_name>/VoiceProfiles.md`.
4. **Interactive Review**: Proposes dialogue-to-shot alignments and voice-over settings in chat for user confirmation.
5. **Generates & Validates**:
   - Uses Frames as ingredient references in `**References:**`.
   - Restricts references to Character and Location assets only (Props ignored; Narrator handled as VO only).
   - Writes the master prompt pack `Exports/<script_name>/VideoPrompts/<script_name>-flow-prompts.md` and per-clip text files in `clips/`.
   - Runs `validate_pack.py` to ensure complete compliance.

---

## Quick Start (Single-Command Execution)

Run the entire pipeline end-to-end with a single terminal command:
```bash
python process_pipeline.py <script_name> [--ar 16:9]
```
Or process all scripts in `Scripts/`:
```bash
python process_pipeline.py --all
```

---

## Detailed Step-by-Step Procedure

### Step 1 — Validate script name and check `Scripts/`
1. Check the provided `<script_name>`. If not specified, list the available `.json` files in `f:\ScriptParser\Scripts\` and ask the user to provide the script name.
2. Verify that `f:\ScriptParser\Scripts\<script_name>.json` exists.

### Step 2 — Run .NET extraction
Run the .NET CLI command from the project root:
```bash
dotnet run -- "<script_name>"
```
Verify that `Exports/<script_name>/Markdowns/<script_name>.md` and `Exports/<script_name>/Images/` exist.

### Step 3 — Parse script & scan nametags
Run:
```bash
python .agents/skills/flow-clip-prompt-generator/scripts/parse_script.py Exports/<script_name>/Markdowns/<script_name>.md Exports/<script_name>/VideoPrompts/_script_data.json
python .agents/skills/flow-clip-prompt-generator/scripts/scan_nametags.py Exports/<script_name>/VideoPrompts/_script_data.json Exports/<script_name>/Images Exports/<script_name>/VideoPrompts/_nametag_map.json
```

### Step 4 — Generate character voice profiles & emotive dialogue (LLM Audio Direction)
The agent generates `Exports/<script_name>/VoiceProfiles.md` using creative audio acting direction:
- **Acoustic DNA & Demographics**: Archetype, timbre, register, pacing (WPM), and dynamic vocal states across the narrative arc.
- **Human-Emotive Dialogue Generation**: Every single dialogue line in the script is dynamically annotated with rich acting directives and naturalistic bracketed vocal cues (e.g., `[sigh]`, `[whisper]`, `[voice cracking]`, `[trembling breath]`, `[gasp of awe]`, `[breathless chuckle]`, `[sob catch]`, `[monotone]`).
- **TTS Prompts & Parameter Matrix**: Engine-specific voice prompts and parameter recommendations (Stability, Clarity, Style Exaggeration) for ElevenLabs, Gemini Audio, and OpenAI Voice.
- Run `python .agents/skills/flow-clip-prompt-generator/scripts/generate_voice_profiles.py Exports/<script_name>` as an initial scaffolding if needed, then enrich with full creative audio direction.

### Step 5 — Propose dialogue alignment & voice-over review
1. **Dialogue Alignment**: Align Full-Story dialogue lines to Scenes and Shots sequentially.
2. **Voice-Over Plan**:
   - **Narrator**: `deferred` (recorded/added in post-production).
   - **On-screen characters**: `native audio` (Flow lip-synced audio generation).
3. **Present in Chat for User Review**:
   - Present proposed dialogue assignments, character voice summaries, and VO handling.
   - Confirm aspect ratio (default `16:9` landscape).

### Step 6 — Generate prompt pack & clip files
Run the generic prompt generator:
```bash
python .agents/skills/flow-clip-prompt-generator/scripts/generate_pack.py Exports/<script_name> --ar 16:9
```
This automatically formats each clip to:
- Pass the shot's Frame as an ingredient in `**References:**`.
- Only include Character and Location reference ingredients.
- Exclude Props from references and strip `@` from prop mentions in prompts.
- Ensure Narrator is non-diegetic audio only (no `@Narrator` references or visual tags).
- Write `Exports/<script_name>/VideoPrompts/<script_name>-flow-prompts.md` and `Exports/<script_name>/VideoPrompts/clips/*.txt`.

### Step 7 — Validate the pack
Run the pack validator:
```bash
python .agents/skills/flow-clip-prompt-generator/scripts/validate_pack.py Exports/<script_name>/VideoPrompts/<script_name>-flow-prompts.md Exports/<script_name>/VideoPrompts/_nametag_map.json
```
Verify that validation returns **PASS**.

### Step 8 — Final Summary
Report to the user:
- Total clips generated & total runtime.
- Path to Master prompt pack: `Exports/<script_name>/VideoPrompts/<script_name>-flow-prompts.md`.
- Path to Voice profiles: `Exports/<script_name>/VoiceProfiles.md`.
- Path to clips: `Exports/<script_name>/VideoPrompts/clips/`.
