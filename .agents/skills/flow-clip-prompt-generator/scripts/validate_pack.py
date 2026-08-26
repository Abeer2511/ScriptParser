#!/usr/bin/env python3
"""
validate_pack.py — sanity-checks an assembled Flow prompt pack before it's
handed back to the user. Catches mistakes like:
- Durations outside {4, 6, 8, 10}s
- Inconsistent aspect ratios
- Missing required fields (Duration, Aspect ratio, References, Prompt, Audio)
- Lingering '**Starting frame:**' lines (starting frames must be ingredients in References)
- Prohibited references (@Prop or @Narrator)
- Misspelled or unresolvable @nametag references

Usage:
    python validate_pack.py <pack.md> <nametag_map.json>

Exits 0 with "PASS" if clean, exits 1 and lists every problem otherwise.
"""
import sys
import re
import json

ALLOWED_DURATIONS = {4, 6, 8, 10}

CLIP_HEADER_RE = re.compile(r"^###\s+Clip\s+([\w.]+)\s+—\s+(.+)$", re.MULTILINE)
DURATION_RE = re.compile(r"\*\*Duration:\*\*\s*(\d+)\s*s", re.IGNORECASE)
ASPECT_RE = re.compile(r"\*\*Aspect ratio:\*\*\s*([^\n]+)", re.IGNORECASE)
GLOBAL_ASPECT_RE = re.compile(r"\*\*Aspect ratio:\*\*\s*([^\n]+)")
STARTING_FRAME_RE = re.compile(r"\*\*Starting\s+frame:\*\*", re.IGNORECASE)


def find_nametag_refs(block, known_nametags_sorted_desc):
    """Find every '@...' reference in a block of text."""
    refs = []
    i = 0
    while True:
        at = block.find("@", i)
        if at == -1:
            break
        rest = block[at + 1:]
        found = None
        for tag in known_nametags_sorted_desc:
            if rest.startswith(tag):
                found = tag
                break
        if found:
            refs.append(found)
            i = at + 1 + len(found)
        else:
            m = re.match(r"[A-Za-z0-9_'\-]+(?:\s[A-Za-z0-9_'\-]+)?", rest)
            refs.append(m.group(0) if m else "")
            i = at + 1
    return refs


def split_clips(text):
    """Split the pack into clip blocks by '### Clip ...' headers."""
    matches = list(CLIP_HEADER_RE.finditer(text))
    blocks = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks.append((m.group(1), m.group(2), text[start:end]))
    return blocks


def validate_pack(text, nametag_map):
    """
    Validate pack text against nametag map.
    Returns list of problem strings (empty list if valid).
    """
    # Allowed categories: Character (except Narrator) and Location
    allowed_nametags = set()
    prop_nametags = set()

    for asset_name, info in nametag_map.get("matched", {}).items():
        cat = info.get("category", "")
        tag = info.get("nametag", "")
        if cat == "Prop":
            prop_nametags.add(tag)
        elif cat in ("Character", "Location"):
            if tag.lower() != "narrator":
                allowed_nametags.add(tag)

    # Frame stems from frame_index
    frame_stems = {re.sub(r"\.[A-Za-z0-9]+$", "", fn) for fn in nametag_map.get("frame_index", [])}
    allowed_nametags |= frame_stems

    # For regex search, combine all known nametags
    all_known_tags = allowed_nametags | prop_nametags | {"Narrator"}
    all_known_sorted_desc = sorted(all_known_tags, key=len, reverse=True)

    problems = []

    header_match = GLOBAL_ASPECT_RE.search(text.split("---", 1)[0])
    global_aspect = header_match.group(1).strip() if header_match else None
    if not global_aspect:
        problems.append("Pack header is missing a global **Aspect ratio:** line.")

    clips = split_clips(text)
    if not clips:
        problems.append("No '### Clip <n> — ...' headers found — pack may not be assembled yet.")

    seen_ids = set()
    for clip_id, title, block in clips:
        if clip_id in seen_ids:
            problems.append(f"Clip {clip_id}: duplicate clip id.")
        seen_ids.add(clip_id)

        dur_m = DURATION_RE.search(block)
        if not dur_m:
            problems.append(f"Clip {clip_id} ('{title}'): missing **Duration:** field.")
        else:
            dur = int(dur_m.group(1))
            if dur not in ALLOWED_DURATIONS:
                problems.append(f"Clip {clip_id} ('{title}'): duration {dur}s is not one of {sorted(ALLOWED_DURATIONS)}.")

        asp_m = ASPECT_RE.search(block)
        if not asp_m:
            problems.append(f"Clip {clip_id} ('{title}'): missing **Aspect ratio:** field.")
        elif global_aspect and asp_m.group(1).strip() != global_aspect:
            problems.append(f"Clip {clip_id} ('{title}'): aspect ratio '{asp_m.group(1).strip()}' "
                             f"does not match the pack's global '{global_aspect}'.")

        if "**References:**" not in block:
            problems.append(f"Clip {clip_id} ('{title}'): missing **References:** field.")

        if "**Prompt:**" not in block:
            problems.append(f"Clip {clip_id} ('{title}'): missing **Prompt:** section.")

        if not re.search(r"audio\s*:", block, re.IGNORECASE):
            problems.append(f"Clip {clip_id} ('{title}'): prompt has no explicit Audio: directive "
                             f"(every clip must state either the dialogue to speak or that it's silent/ambient-only).")

        # Disallow separate Starting frame field
        if STARTING_FRAME_RE.search(block):
            problems.append(f"Clip {clip_id} ('{title}'): contains separate '**Starting frame:**' field. "
                             f"In Google Flow, frames must be passed as ingredient references in **References:**.")

        # Check all @tag references
        for tag in find_nametag_refs(block, all_known_sorted_desc):
            if tag.lower() == "narrator":
                problems.append(f"Clip {clip_id} ('{title}'): references @Narrator. "
                                 f"Narrator is non-diegetic VO only and must not be tagged as an image reference.")
            elif tag in prop_nametags:
                problems.append(f"Clip {clip_id} ('{title}'): references prop @{tag}. "
                                 f"Props are baked into frame generations and must not be referenced as ingredients.")
            elif tag not in allowed_nametags:
                problems.append(f"Clip {clip_id} ('{title}'): references @{tag}, which has no matching "
                                 f"character/location/frame image in the nametag map.")

    return problems


def main():
    if len(sys.argv) != 3:
        print("Usage: python validate_pack.py <pack.md> <nametag_map.json>")
        sys.exit(1)

    pack_path, nametag_map_path = sys.argv[1], sys.argv[2]

    with open(pack_path, "r", encoding="utf-8") as f:
        text = f.read()

    with open(nametag_map_path, "r", encoding="utf-8") as f:
        nametag_map = json.load(f)

    problems = validate_pack(text, nametag_map)
    clips = split_clips(text)

    if problems:
        print(f"FAIL — {len(problems)} problem(s):\n")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    else:
        print(f"PASS — {len(clips)} clips validated. All durations in {sorted(ALLOWED_DURATIONS)}, "
              f"aspect ratio consistent, frames used as ingredients, props and narrator excluded from references.")
        sys.exit(0)


if __name__ == "__main__":
    main()