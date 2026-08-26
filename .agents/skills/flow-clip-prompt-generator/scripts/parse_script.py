#!/usr/bin/env python3
"""
parse_script.py — deterministic parser for the Google-Flow-exported script
markdown (Title / Full Story / Assets / Scenes-Shots format).

Usage:
    python parse_script.py <path-to-script.md> <output-json-path>

Produces a JSON file with:
    title, characters[], locations[], props[],
    full_story_beats[]  (scene-id ordered narrative + dialogue),
    scenes[]            (Scene -> Shot breakdown with Visual/Audio/Motion/Assets),
    warnings[]          (anything the parser wasn't sure how to handle)

The parser is intentionally line-based and defensive: it never raises on
unexpected input, it records a warning and keeps going, so a long/irregular
script still produces a usable partial result instead of a crash.
"""
import sys
import json
import re


def load_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().splitlines()


SCENE_ID_RE = re.compile(r"<!--\s*scene-id:\s*([0-9a-fA-F-]+)\s*-->")
HEADING_RE = re.compile(r"^###\s+((?:INT|EXT)[./].*)$", re.IGNORECASE)
TRANSITION_RE = re.compile(r"^#####\s+(.*)$")
SPEAKER_RE = re.compile(r"^\*\*([A-Z0-9 ,.'\-]+)\*\*\s*$")
PARENTHETICAL_RE = re.compile(r"^_\((.*)\)_\s*$")

SCENE_HEADER_RE = re.compile(r"^###\s+Scene\s+(\d+):\s*(.*)$", re.IGNORECASE)
SHOT_HEADER_RE = re.compile(r"^####\s+Shot\s+(\d+):\s*(.*)$", re.IGNORECASE)
ASSET_ITEM_RE = re.compile(r"^\s*-\s*`([^`]+)`\s*$")
FIELD_LABEL_RE = re.compile(r"^\s*-\s*\*\*(Visual|Audio|Motion|Assets):\*\*\s*$", re.IGNORECASE)
BLOCKQUOTE_RE = re.compile(r"^\s*>\s?(.*)$")


def parse_full_story(lines, start, end, warnings):
    """Parse the Full Story section into ordered narrative beats with dialogue."""
    beats = []
    current = None
    i = start
    while i < end:
        line = lines[i]

        m = SCENE_ID_RE.search(line)
        if m:
            if current:
                beats.append(current)
            current = {
                "scene_id": m.group(1),
                "heading": None,
                "narrative_text": [],
                "dialogue": [],
                "transitions": [],
            }
            i += 1
            continue

        m = HEADING_RE.match(line)
        if m and current is not None:
            current["heading"] = m.group(1).strip()
            i += 1
            continue

        m = TRANSITION_RE.match(line)
        if m:
            if current:
                current["transitions"].append(m.group(1).strip())
            i += 1
            continue

        m = SPEAKER_RE.match(line)
        if m and current is not None:
            speaker = m.group(1).strip()
            parenthetical = None
            j = i + 1
            if j < end:
                pm = PARENTHETICAL_RE.match(lines[j])
                if pm:
                    parenthetical = pm.group(1).strip()
                    j += 1
            # collect dialogue text until blank line
            text_lines = []
            while j < end and lines[j].strip() != "":
                if SPEAKER_RE.match(lines[j]) or HEADING_RE.match(lines[j]) or SCENE_ID_RE.search(lines[j]):
                    break
                text_lines.append(lines[j].strip())
                j += 1
            current["dialogue"].append({
                "character": speaker,
                "parenthetical": parenthetical,
                "text": " ".join(text_lines).strip(),
            })
            i = j
            continue

        stripped = line.strip()
        if stripped and current is not None and not stripped.startswith("#"):
            current["narrative_text"].append(stripped)

        i += 1

    if current:
        beats.append(current)

    for b in beats:
        b["narrative_text"] = " ".join(b["narrative_text"]).strip()
        if not b["heading"]:
            warnings.append(f"scene-id {b['scene_id']} has no INT/EXT heading captured")

    return beats


def parse_characters(lines, start, end, warnings):
    characters = []
    current = None
    i = start
    while i < end:
        line = lines[i]
        m = re.match(r"^###\s+(.+)$", line)
        if m:
            if current:
                characters.append(current)
            current = {"name": m.group(1).strip(), "physical": "", "clothing": "", "backstory": ""}
            i += 1
            continue
        m = re.match(r"^\s*-\s*\*\*Physical Characteristics:\*\*\s*(.*)$", line)
        if m and current is not None:
            current["physical"] = m.group(1).strip()
            i += 1
            continue
        m = re.match(r"^\s*-\s*\*\*Clothing/Accessories:\*\*\s*(.*)$", line)
        if m and current is not None:
            current["clothing"] = m.group(1).strip()
            i += 1
            continue
        m = re.match(r"^\s*-\s*\*\*Backstory:\*\*\s*(.*)$", line)
        if m and current is not None:
            current["backstory"] = m.group(1).strip()
            i += 1
            continue
        i += 1
    if current:
        characters.append(current)
    if not characters:
        warnings.append("No characters parsed under ## Characters — check heading format (expected '### Name').")
    return characters


def parse_flat_list(lines, start, end):
    items = []
    for line in lines[start:end]:
        m = re.match(r"^\s*-\s*\*\*(.+?)\*\*\s*$", line)
        if m:
            items.append(m.group(1).strip())
    return items


def parse_scenes(lines, start, end, warnings):
    scenes = []
    current_scene = None
    current_shot = None
    pending_field = None  # 'Visual' | 'Audio' | 'Motion' | 'Assets' | None
    i = start
    while i < end:
        line = lines[i]

        m = SCENE_HEADER_RE.match(line)
        if m:
            if current_shot and current_scene:
                current_scene["shots"].append(current_shot)
                current_shot = None
            if current_scene:
                scenes.append(current_scene)
            current_scene = {"scene_number": int(m.group(1)), "heading": m.group(2).strip(), "shots": []}
            pending_field = None
            i += 1
            continue

        m = SHOT_HEADER_RE.match(line)
        if m:
            if current_shot and current_scene:
                current_scene["shots"].append(current_shot)
            current_shot = {
                "shot_number": int(m.group(1)),
                "title": m.group(2).strip(),
                "visual": [],
                "audio": [],
                "motion": [],
                "assets": [],
            }
            pending_field = None
            i += 1
            continue

        m = FIELD_LABEL_RE.match(line)
        if m and current_shot is not None:
            pending_field = m.group(1).lower()
            i += 1
            continue

        if current_shot is not None and pending_field in ("visual", "audio", "motion"):
            bm = BLOCKQUOTE_RE.match(line)
            if bm and bm.group(1).strip():
                current_shot[pending_field].append(bm.group(1).strip())
                i += 1
                continue

        if current_shot is not None and pending_field == "assets":
            am = ASSET_ITEM_RE.match(line)
            if am:
                current_shot["assets"].append(am.group(1).strip())
                i += 1
                continue

        if line.strip() == "---":
            pending_field = None

        i += 1

    if current_shot and current_scene:
        current_scene["shots"].append(current_shot)
    if current_scene:
        scenes.append(current_scene)

    for sc in scenes:
        for sh in sc["shots"]:
            sh["visual"] = " ".join(sh["visual"]).strip()
            sh["audio"] = " ".join(sh["audio"]).strip()
            sh["motion"] = " ".join(sh["motion"]).strip()
            if not sh["assets"]:
                warnings.append(f"Scene {sc['scene_number']} Shot {sh['shot_number']} ('{sh['title']}') has no Assets listed.")

    if not scenes:
        warnings.append("No scenes parsed under ## Scenes — check heading format (expected '### Scene N: ...').")

    return scenes


def find_section(lines, header_pattern):
    """Return (start_index_after_header, end_index) for a top-level section,
    where end is the next line matching the same-or-higher heading level, or EOF."""
    pass


def main():
    if len(sys.argv) != 3:
        print("Usage: python parse_script.py <script.md> <output.json>")
        sys.exit(1)

    src, out = sys.argv[1], sys.argv[2]
    lines = load_lines(src)
    n = len(lines)
    warnings = []

    title = None
    for line in lines:
        m = re.match(r"^##\s+Title:\s*(.+)$", line)
        if m:
            title = m.group(1).strip()
            break
    if not title:
        warnings.append("No '## Title:' line found.")

    # Locate top-level section boundaries by their known headers.
    idx_full_story = next((i for i, l in enumerate(lines) if re.match(r"^##\s+Full Story:", l)), None)
    idx_assets = next((i for i, l in enumerate(lines) if re.match(r"^#\s+Assets\s*$", l)), None)
    idx_characters = next((i for i, l in enumerate(lines) if re.match(r"^##\s+Characters\s*$", l)), None)
    idx_locations = next((i for i, l in enumerate(lines) if re.match(r"^##\s+Locations\s*$", l)), None)
    idx_props = next((i for i, l in enumerate(lines) if re.match(r"^##\s+Props\s*$", l)), None)
    idx_scenes = next((i for i, l in enumerate(lines) if re.match(r"^##\s+Scenes\s*$", l)), None)

    required = {
        "## Full Story:": idx_full_story,
        "# Assets": idx_assets,
        "## Characters": idx_characters,
        "## Locations": idx_locations,
        "## Props": idx_props,
        "## Scenes": idx_scenes,
    }
    missing = [k for k, v in required.items() if v is None]
    if missing:
        warnings.append(f"Missing expected section header(s): {', '.join(missing)}. "
                         f"Parsing will proceed with whatever was found; results may be incomplete.")

    full_story_beats = []
    if idx_full_story is not None:
        fs_end = idx_assets if idx_assets is not None else n
        full_story_beats = parse_full_story(lines, idx_full_story + 1, fs_end, warnings)

    characters = []
    if idx_characters is not None:
        ch_end = idx_locations if idx_locations is not None else (idx_props if idx_props is not None else n)
        characters = parse_characters(lines, idx_characters + 1, ch_end, warnings)

    locations = []
    if idx_locations is not None:
        loc_end = idx_props if idx_props is not None else n
        locations = parse_flat_list(lines, idx_locations + 1, loc_end)

    props = []
    if idx_props is not None:
        pr_end = idx_scenes if idx_scenes is not None else n
        props = parse_flat_list(lines, idx_props + 1, pr_end)

    scenes = []
    if idx_scenes is not None:
        scenes = parse_scenes(lines, idx_scenes + 1, n, warnings)

    # Cross-check: assets referenced in shots but never declared anywhere.
    known_assets = set(c["name"] for c in characters) | set(locations) | set(props)
    undeclared = set()
    for sc in scenes:
        for sh in sc["shots"]:
            for a in sh["assets"]:
                if a not in known_assets:
                    undeclared.add(a)
    if undeclared:
        warnings.append("Assets referenced in shots but not declared in Characters/Locations/Props: "
                         + ", ".join(sorted(undeclared)))

    data = {
        "title": title,
        "characters": characters,
        "locations": locations,
        "props": props,
        "full_story_beats": full_story_beats,
        "scenes": scenes,
        "warnings": warnings,
        "stats": {
            "scene_count": len(scenes),
            "shot_count": sum(len(sc["shots"]) for sc in scenes),
            "character_count": len(characters),
            "location_count": len(locations),
            "prop_count": len(props),
            "dialogue_line_count": sum(len(b["dialogue"]) for b in full_story_beats),
        },
    }

    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Parsed '{data['title']}': {data['stats']['scene_count']} scenes, "
          f"{data['stats']['shot_count']} shots, {data['stats']['character_count']} characters, "
          f"{data['stats']['dialogue_line_count']} dialogue lines.")
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")


if __name__ == "__main__":
    main()