# Output format, duration rules, and worked example

## 1. Duration snapping — every clip must be 4, 6, 8, or 10 seconds

Never emit any other value. Decide per shot as follows:

**If the shot has dialogue/VO assigned to "native audio" (spoken in-clip):**
1. Count the words in the line(s) assigned to this shot.
2. `needed_seconds = words / 2.5` (≈150 wpm speaking pace).
3. Round UP to the nearest allowed value: ≤4→4, ≤6→6, ≤8→8, ≤10→10.
4. If `needed_seconds > 10`, the line doesn't fit one clip. Split it at a
   sentence boundary into two consecutive clips (label them `<n>a` and
   `<n>b`), each re-run through steps 1–3 independently. Never truncate a
   sentence mid-way or drop words to make a line fit.

**If the shot is silent/ambient-only** (no dialogue, or VO deferred to post),
snap by the dominant camera/action cue in the shot's Motion + Visual text:

| Cue in the shot | Duration |
|---|---|
| match-cut, whip-pan, smash-cut, quick cut, single sharp action, extreme-close-up beat | **4s** |
| a standard action beat with no special camera language (the default) | **6s** |
| push-in, dolly, tracking shot, rack focus, pull-back over a single subject | **8s** |
| slow orbit, wide establishing reveal, extended dissolve, long pull-back across a scene | **10s** |

If more than one cue applies, use the longest one present. If none apply, default to 6s.

## 2. Voice-over field — three possible states per clip

- `None` — no dialogue/VO in this shot at all.
- `<CHARACTER> (native audio) — "<exact line>"` — the video model should
  generate the spoken performance itself. Only use this for shots the user
  confirmed as native-audio during the voice-over question.
- `<CHARACTER> (deferred — add in post) — "<exact line>"` — the line exists
  and belongs to this shot, but per the user's choice it should NOT be
  generated as in-clip audio; it's a placeholder for separately-added TTS/VO.
  The Prompt block must still explicitly say the clip has no spoken dialogue
  (see Audio directive below), so the video model doesn't invent its own
  dialogue.

## 3. Asset & Frame Referencing Rules (Google Flow Platform Constraints)

1. **Frames as Ingredients**: Google Flow does NOT support specifying both
   "Ingredients" (references) and a "Starting Frame" in the same generation.
   Therefore, reference frames are supplied as **ingredients** in the `**References:**`
   field (e.g. `@The Patent Clerk`).
2. **Characters & Locations ONLY**: Only Character references (e.g. `@Elias`)
   and Location references (e.g. `@Patent Office`) are included in `**References:**`
   and tagged with `@` in the prompt.
3. **Narrator is VO ONLY**: Narrator is non-diegetic audio/voice-over only and
   never appears on-screen. Do NOT include `@Narrator` in `**References:**` or
   tag `@Narrator` in visual action text. Narrator belongs strictly in the `Audio:`
   directive or Dialogue/VO field.
4. **Ignore Props Assets**: Do NOT add Props assets to `**References:**`, and
   do NOT tag props with `@` in the Prompt (e.g. write "desk", "monitors",
   "pocket watch" in plain prose). Props are already baked into the generated
   frame images.
5. **No Separate Starting Frame Field**: Omit the `**Starting frame:**` line
   completely.

## 4. Prompt block — must be complete and self-contained

Google Flow's model has no memory between clips, so every `**Prompt:**`
block must stand alone. Include, in natural prose (not a bullet list):

1. **Scene context** — one short clause restating INT/EXT, location, time of
   day, from the Scene heading.
2. **Action** — the shot's Visual description, describing what is seen on-screen.
   Do not include meta-commentary about narrator voice-over in the action text.
3. **Asset references** — reference matched Characters (except Narrator) and
   Locations using `@nametag`. Unmatched characters/locations are described
   inline in prose. Props are described in regular prose without `@`.
4. **Camera/motion** — from the shot's Motion field.
5. **Framing** — state the aspect ratio explicitly, e.g. "Compose for 16:9
   landscape framing."
6. **Duration** — state the exact clip length: "Duration: 8s."
7. **Audio directive** — always end with one of:
   - `Audio: <foley/ambience description>. No spoken dialogue in this clip.`
   - `Audio: <foley/ambience description>; dialogue spoken on-screen by
     <CHARACTER>: "<exact line>."`
   - If a line is `deferred`, use the "No spoken dialogue" form or note narrator
     voice-over in ambient audio.

## 5. Full clip block format

```markdown
### Clip <scene>.<shot>[<a|b>] — <Shot Title>
**Duration:** <4|6|8|10>s
**Aspect ratio:** <the single ratio chosen for the whole pack>
**References:** @<frame-nametag>, @<character-nametag>, @<location-nametag>
**Dialogue / Voice-over:** <None | see Section 2>

**Prompt:**
<the complete self-contained prompt from Section 4>

---
```

## 6. Pack header

```markdown
# GOOGLE FLOW VIDEO PROMPT PACK — <Title>

**Source script:** <script_name>.md
**Aspect ratio:** <ratio>
**Total clips:** <n>  |  **Total runtime:** <sum of durations>s
**Voice-over plan:** <one clause per character with dialogue, e.g.
  "NARRATOR — deferred (add in post); ELIAS — native audio">
**Unresolved assets (no reference image, described inline):** <comma list, or "None">

---
```

## 7. Worked example

Input shot data:
```
Scene 1: Int. Patent Office - Day
Shot 03: The Patent Clerk
Visual: Elias sits at the desk, dwarfed by stacks of documents and
  mechanical parts. He looks weary and overwhelmed, his hands visibly
  trembling as he grips a Pocket Watch. The afternoon light from the
  window catches the dust motes dancing in the air of the Patent Office.
Audio: The sound of heavy breathing is heard, mixed with the scratching of
  a distant pen. The ticking of the watch becomes the dominant sound.
Motion: A medium shot slowly pulls back to reveal the cramped and chaotic
  nature of Elias's workspace.
Assets: Elias, Cluttered Wooden Desk, Patent Office, Pocket Watch
```
Nametag map: `Elias` → `@Elias` (Character), `Patent Office` → `@Patent Office` (Location), `The Patent Clerk` → Frame match. `Cluttered Wooden Desk` and `Pocket Watch` are Props (ignored as reference ingredients).

Output:
```markdown
### Clip 1.3 — The Patent Clerk
**Duration:** 8s
**Aspect ratio:** 16:9
**References:** @The Patent Clerk, @Elias, @Patent Office
**Dialogue / Voice-over:** None

**Prompt:**
Int. Patent Office - Day. @Elias sits at the cluttered wooden desk, dwarfed by stacks of documents and mechanical parts. He looks weary and overwhelmed, his hands visibly trembling as he grips a pocket watch. The afternoon light from the window catches dust motes dancing in the air of @Patent Office. A medium shot slowly pulls back to reveal the cramped and chaotic nature of Elias's workspace. Compose for 16:9 landscape framing. Duration: 8s. Audio: The sound of heavy breathing is heard, mixed with the scratching of a distant pen. The ticking of the watch becomes the dominant sound. No spoken dialogue in this clip.

---
```