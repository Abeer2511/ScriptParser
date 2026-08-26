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

If more than one cue applies, use the longest one present. If none apply, default to 6s. State the reason briefly isn't required in the output — just pick the duration silently and move on; don't clutter the pack with rationale.

## 2. Voice-over field — three possible states per clip

- `None` — no dialogue/VO in this shot at all.
- `<CHARACTER> (native audio) — "<exact line>"` — the video model should
  generate the spoken performance itself. Only use this for shots the user
  confirmed as native-audio during the voice-over question.
- `<CHARACTER> (deferred — add in post) — "<exact line>"` — the line exists
  and belongs to this shot, but per the user's choice it should NOT be
  generated as in-clip audio; it's a placeholder for separately-added TTS/VO.
  The Prompt block must still explicitly say the clip has no spoken audio
  (see Audio directive below), so the video model doesn't invent its own
  dialogue.

If a Scene's dialogue couldn't be confidently pinned to one specific Shot
(common — the shot breakdown doesn't carry scene-id, so alignment to the
Full Story is approximate), say so plainly to the user and let them
confirm/reassign rather than guessing silently. Never split a single line
of dialogue across two clips' Voice-over fields — if it doesn't fit, split
by duration (Section 1, step 4) instead, keeping the sentence in whichever
clip it fits, or push the excess sentence(s) to the following clip.

## 3. Prompt block — must be complete and self-contained

Google Flow's model has no memory between clips, so every `**Prompt:**`
block must stand alone. Include, in natural prose (not a bullet list):

1. **Scene context** — one short clause restating INT/EXT, location, time of
   day, from the Scene heading.
2. **Action** — the shot's Visual description, condensed/adjusted to suit
   the clip's duration.
3. **Asset references** — for every asset in the shot's Assets list that has
   a resolved nametag, reference it with its exact `@nametag` (copy the
   nametag string exactly — including any spacing or punctuation the actual
   filename has; never invent, abbreviate, or "clean up" a nametag). For any
   asset the user marked as unresolved (no reference image), write a short
   inline visual description instead of a nametag — pull from the asset's
   own description in the script's Assets section when it's a Character;
   for Props/Locations with no description on file, derive a concise one
   from how the shot text portrays it.
4. **Camera/motion** — from the shot's Motion field.
5. **Mood/lighting** — inferred from the scene's day/night setting and the
   shot's Audio/Visual mood cues.
6. **Framing** — state the aspect ratio explicitly, e.g. "Compose for 16:9
   landscape framing" / "Vertical 9:16 framing, subject centered for a tall
   frame."
7. **Duration** — state the exact clip length: "Duration: 8s."
8. **Audio directive** — always end with one of:
   - `Audio: <foley/ambience description>. No spoken dialogue in this clip.`
   - `Audio: <foley/ambience description>; dialogue spoken on-screen by
     <CHARACTER>: "<exact line>."`
   - If a line is `deferred`, use the "No spoken dialogue" form even though
     a line exists for this shot — the deferred line lives only in the
     Voice-over field, never inside the Prompt's spoken-audio directive.

## 4. Frame image reference (image-to-video seed)

If `scan_nametags.py`'s `frame_index` contains a file that plausibly
corresponds to this shot (matching scene/shot number in the filename, or a
title match), add one line right after the Prompt block:

```
**Starting frame:** @<frame-nametag> — use as the reference frame for
image-to-video generation.
```

If no frame file matches, omit this line entirely (don't write "None" —
just leave it out).

## 5. Full clip block format

```
### Clip <scene>.<shot>[<a|b>] — Shot <NN>: <Shot Title>
**Duration:** <4|6|8|10>s
**Aspect ratio:** <the single ratio chosen for the whole pack>
**References:** @<nametag>, @<nametag>, ...   (or "None" if every asset in
  this shot was left as inline description)
**Dialogue / Voice-over:** <None | see Section 2>

**Prompt:**
<the complete self-contained prompt from Section 3>

**Starting frame:** @<frame-nametag> — ...   (omit line if no match)

---
```

## 6. Pack header

```
# GOOGLE FLOW VIDEO PROMPT PACK — <Title>

**Source script:** <script_name>.md
**Aspect ratio:** <ratio>
**Total clips:** <n>  |  **Total runtime:** <sum of durations>s
**Voice-over plan:** <one clause per character with dialogue, e.g.
  "NARRATOR — deferred (add in post); ELIAS — native audio">
**Unresolved assets (no reference image, described inline):** <comma list, or "None">

---
```
Then one `## Scene <n>: <Heading>` section per scene, containing that
scene's Clip blocks in shot order.

## 7. Worked example (from a real parsed script)

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
Nametag map: `Elias` → `@Elias` (matched), `Patent Office` → `@Patent
Office` (matched), `Cluttered Wooden Desk` and `Pocket Watch` → unmatched
(no image found). No dialogue in this shot. Aspect ratio chosen: 16:9.

Motion says "slowly pulls back to reveal" → matches the 8s cue (pull-back
over a single subject).

Output:
```
### Clip 1.3 — Shot 03: The Patent Clerk
**Duration:** 8s
**Aspect ratio:** 16:9
**References:** @Elias, @Patent Office
**Dialogue / Voice-over:** None

**Prompt:**
Interior, Patent Office, day. @Elias sits at a cluttered wooden desk piled
with stacks of documents and mechanical parts (desk has no reference image
— cluttered, dark-wood, stacked with papers), dwarfed by the mess, hands
visibly trembling as he grips a small tarnished silver pocket watch (no
reference image — worn silver casing, thin chain). Afternoon light from a
window catches dust motes drifting through @Patent Office. Camera opens on
a medium shot and slowly pulls back to reveal the full cramped, chaotic
workspace. Warm, dusty, late-afternoon lighting, muted period color
palette. Compose for 16:9 landscape framing. Duration: 8s. Audio: heavy
breathing, the scratch of a distant pen, and the ticking of the pocket
watch growing dominant in the mix. No spoken dialogue in this clip.

---
```