---
name: process-script
description: 'End-to-end automated orchestration pipeline for Google Storyboard scripts: validates the raw JSON in Scripts/, runs the .NET extractor to populate Exports/<script_name>/ (Markdowns and Images), scans nametags, presents dialogue alignment and VO handling in chat for review, generates complete Google Flow / Omni Flash video prompts, and runs automated pack validation.'
argument-hint: 'Script name (the .json filename in Scripts/, e.g. Script1 or "WHAT THE LIMIT WAS FOR")'
---

# Process Script Pipeline Orchestrator

## What this does

Orchestrates the entire Google Storyboard to Google Flow video prompt pack generation pipeline inside the unified `ScriptParser` workspace:

1. **Validates & Extracts**: Takes `<script_name>`, checks `f:\ScriptParser\Scripts\<script_name>.json`, and executes the .NET parser to create:
   - `Exports/<script_name>/Markdowns/<script_name>.md`
   - `Exports/<script_name>/Images/{Character,Location,Prop,Frame}/`
2. **Parses & Matches Nametags**: Runs deterministic scripts to produce `_script_data.json` and `_nametag_map.json`.
3. **Interactive Review**: Proposes dialogue-to-shot alignments and voice-over settings in chat for user confirmation.
4. **Generates & Validates**: Writes the master prompt pack `Exports/<script_name>/VideoPrompts/<script_name>-flow-prompts.md`, per-clip text files in `clips/`, and runs `validate_pack.py` to ensure complete compliance.

---

## Procedure

### Step 1 — Validate script name and check `Scripts/`
1. Check the provided `<script_name>`. If not specified, list the available `.json` files in `f:\ScriptParser\Scripts\` and ask the user to provide the script name.
2. Verify that `f:\ScriptParser\Scripts\<script_name>.json` exists (case-insensitive, ignoring `.json` if passed).
3. If the file is **not found**:
   - List all available `.json` files in `f:\ScriptParser\Scripts\`.
   - Ask the user to input the correct script name again.
   - Do NOT guess or proceed until a valid script is confirmed.

### Step 2 — Run .NET extraction
Run the .NET CLI command from the project root:
```bash
dotnet run -- "<script_name>"
```
Verify that the output reports success and that `Exports/<script_name>/Markdowns/<script_name>.md` and `Exports/<script_name>/Images/` exist.

### Step 3 — Parse script & scan nametags
Run the deterministic parsing tools:
```bash
python .agents/skills/flow-clip-prompt-generator/scripts/parse_script.py Exports/<script_name>/Markdowns/<script_name>.md Exports/<script_name>/VideoPrompts/_script_data.json
python .agents/skills/flow-clip-prompt-generator/scripts/scan_nametags.py Exports/<script_name>/VideoPrompts/_script_data.json Exports/<script_name>/Images Exports/<script_name>/VideoPrompts/_nametag_map.json
```
Read the output summary and check:
- Total scenes, shots, characters, and dialogue lines parsed.
- Cleanly matched nametags and frame images found.
- If there are **ambiguous** asset matches, ask the user to resolve which image to use.
- If there are **unmatched assets**, notify the user that these will be described inline in prose.

### Step 4 — Propose dialogue alignment & voice-over review
1. **Dialogue Alignment**:
   - Align Full-Story dialogue lines to Scenes and Shots by matching INT/EXT scene headings sequentially.
   - Assign each line to the most relevant Shot based on Visual/Motion description (defaulting to the first shot in the scene if general).
2. **Voice-Over Plan**:
   - Identify every character with spoken lines.
   - Set sensible defaults:
     - **Non-diegetic / Narrator**: `deferred` (recorded/added in post-production).
     - **On-screen character**: `native audio` (Flow lip-synced audio generation).
3. **Present in Chat for User Review**:
   - Present a concise table/summary of proposed dialogue assignments (e.g. `Scene X Shot Y: CHARACTER -> "Dialogue snippet..."`).
   - Present the proposed Voice-Over handling per character.
   - Confirm aspect ratio (default `16:9` landscape).
   - Ask the user: *"Please confirm or adjust the dialogue assignments and VO plan above before prompt generation."*

### Step 5 — Generate prompt pack & clip files
Once the user confirms or provides adjustments:
1. Refer to `.agents/skills/flow-clip-prompt-generator/references/output_template.md` for prompt format, duration snapping ({4, 6, 8, 10}s), and `@nametag` referencing rules.
2. Assemble the master markdown file:
   ```
   Exports/<script_name>/VideoPrompts/<script_name>-flow-prompts.md
   ```
3. Assemble individual plain-text prompt files for each clip:
   ```
   Exports/<script_name>/VideoPrompts/clips/Scene<NN>_Shot<NN>[a|b].txt
   ```

### Step 6 — Validate the pack
Run the pack validator:
```bash
python .agents/skills/flow-clip-prompt-generator/scripts/validate_pack.py Exports/<script_name>/VideoPrompts/<script_name>-flow-prompts.md Exports/<script_name>/VideoPrompts/_nametag_map.json
```
- If it reports **PASS**, proceed to summary.
- If it reports any issues (durations outside allowed set, unresolvable nametag references, missing directives), fix the affected clips and re-validate until it passes cleanly.

### Step 7 — Final Summary
Report to the user:
- Total clips generated and total runtime.
- Master pack file location: `Exports/<script_name>/VideoPrompts/<script_name>-flow-prompts.md`
- Clips folder location: `Exports/<script_name>/VideoPrompts/clips/`
- Applied Voice-Over plan and aspect ratio.
- Any unresolved assets that are described inline in prose.
