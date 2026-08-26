#!/usr/bin/env python3
"""
generate_pack.py — Generic Google Flow prompt pack generator.

Rules enforced:
1. Google Flow cannot use both Starting Frame and Ingredients in the same generation.
   Frames are used as Ingredients in **References:** alongside Characters and Locations.
2. Only Character and Location nametags are added as reference ingredients.
3. Narrator is non-diegetic VO only (never an on-screen character or reference ingredient).
4. Props assets are ignored as reference ingredients (baked into frame generations), and
   stripped of '@' tags in visual prompts.
5. No separate '**Starting frame:**' line is output.
6. All durations snapped to {4, 6, 8, 10}s.

Usage:
    python generate_pack.py <script_name_or_folder> [--ar 16:9]
"""

import sys
import os
import re
import json
import argparse


ALLOWED_DURATIONS = [4, 6, 8, 10]


def get_base_duration(motion, visual):
    text = (motion + " " + visual).lower()
    if any(c in text for c in ["slow orbit", "wide establishing", "extended dissolve", "long pull-back", "slow pan", "sweeping pan"]):
        return 10
    if any(c in text for c in ["push-in", "dolly", "tracking shot", "rack focus", "pull-back", "zoom in", "zoom-in"]):
        return 8
    if any(c in text for c in ["match-cut", "whip-pan", "smash-cut", "quick cut", "sharp action", "extreme close-up", "extreme-close-up"]):
        return 4
    return 6


def snap_duration(needed_seconds):
    for d in ALLOWED_DURATIONS:
        if needed_seconds <= d:
            return d
    return 10


def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]


def find_frame(shot_title, scene_idx, shot_idx, frame_index):
    """Match frame by shot title or scene/shot numbering."""
    if not frame_index:
        return None

    if shot_title:
        clean_title = re.sub(r'[^a-zA-Z0-9]', '', shot_title).lower()
        for f in frame_index:
            stem = os.path.splitext(f)[0]
            clean_stem = re.sub(r'[^a-zA-Z0-9]', '', stem).lower()
            if clean_title == clean_stem or clean_title in clean_stem or clean_stem in clean_title:
                return stem

    # Fallback by Scene/Shot indices (1-indexed)
    patterns = [
        f"scene{scene_idx+1}_shot{shot_idx+1}",
        f"scene_{scene_idx+1}_shot_{shot_idx+1}",
        f"s{scene_idx+1}_sh{shot_idx+1}",
        f"shot{shot_idx+1}"
    ]
    for p in patterns:
        for f in frame_index:
            stem = os.path.splitext(f)[0]
            clean_stem = re.sub(r'[^a-zA-Z0-9]', '', stem).lower()
            if p in clean_stem:
                return stem

    return None


def clean_visual_text(text, assets_list, matched_map, unmatched_list, props_list):
    """
    Sanitize visual action text:
    - Characters (except Narrator) and Locations get @nametag.
    - Narrator mentions are cleaned up so narrator is not treated as a visual entity.
    - Props are written in plain text without @ (since they are baked into frames).
    """
    res = text

    # Remove '@Narrator' or meta narrator phrasing from visual action
    res = re.sub(r'\bThe\s+@?Narrator(?:\'s)?\s+voice-over\s+begins\s+as\b', '', res, flags=re.IGNORECASE)
    res = re.sub(r'\bThrough\s+the\s+@?Narrator(?:\'s)?\s+words,?\b', '', res, flags=re.IGNORECASE)
    res = re.sub(r'\bThrough\s+the\s+@?Narrator(?:\'s)?\s+voice-over,?\b', '', res, flags=re.IGNORECASE)
    res = re.sub(r'\bThe\s+@?Narrator\s+describes\b[^\.]*\.', '', res, flags=re.IGNORECASE)
    res = re.sub(r'\bThe\s+@?Narrator(?:\'s)?\s+voice\s+returns,?\b[^\.]*\.', '', res, flags=re.IGNORECASE)
    res = re.sub(r'@Narrator\b', 'the narrator', res, flags=re.IGNORECASE)

    used_tags = []

    for a in assets_list:
        if a.lower() == "narrator":
            continue

        if a in props_list:
            # Ensure prop is not tagged with @
            res = re.sub(rf'@\b{re.escape(a)}\b', a, res, flags=re.IGNORECASE)
            continue

        if a in matched_map:
            cat = matched_map[a].get("category", "")
            tag = matched_map[a]["nametag"]
            if cat in ("Character", "Location"):
                res = re.sub(rf'(?<!@)\b{re.escape(a)}\b', f'@{tag}', res, flags=re.IGNORECASE)
                used_tags.append(f"@{tag}")
        elif a in unmatched_list:
            if a not in props_list:
                res = re.sub(rf'(?<!@)\b{re.escape(a)}\b', f'{a} (no reference image — visualize {a.lower()})', res, flags=re.IGNORECASE)

    # Strip any dangling @Prop tags that might remain
    for p in props_list:
        res = re.sub(rf'@\b{re.escape(p)}\b', p, res, flags=re.IGNORECASE)

    # Clean up punctuation and spacing artifacts
    res = re.sub(r'\.\s*,\s*', '. ', res)
    res = re.sub(r',\s*\.', '.', res)
    res = re.sub(r'\.{2,}', '.', res)
    res = re.sub(r'\s+', ' ', res).strip()
    res = re.sub(r'^\s*,\s*', '', res)
    res = re.sub(r'(\.\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), res)
    if res and res[0].islower():
        res = res[0].upper() + res[1:]

    return res, used_tags


def align_dialogue_to_scenes_and_shots(scenes, full_story_beats):
    """
    Deterministically align dialogue lines from full_story_beats to scenes and shots.
    """
    dialogue_assignments = {}  # (scene_idx, shot_idx) -> list of {char, text, type}

    # Match beats to scenes by sequence and INT/EXT heading
    beat_idx = 0
    for scene_idx, sc in enumerate(scenes):
        sc_heading = sc.get("heading", "").strip().lower()
        matched_beat = None

        # Look for matching beat starting from beat_idx
        for b_i in range(beat_idx, len(full_story_beats)):
            b = full_story_beats[b_i]
            b_head = b.get("heading", "").strip().lower() if b.get("heading") else ""
            if b_head and (b_head == sc_heading or b_head in sc_heading or sc_heading in b_head):
                matched_beat = b
                beat_idx = b_i + 1
                break

        # Fallback: if scene count matches beat count exactly, match 1:1
        if not matched_beat and len(scenes) == len(full_story_beats) and scene_idx < len(full_story_beats):
            matched_beat = full_story_beats[scene_idx]

        if not matched_beat or not matched_beat.get("dialogue"):
            continue

        lines = matched_beat.get("dialogue", [])
        shots = sc.get("shots", [])
        if not shots:
            continue

        if len(lines) == 1:
            speaker = lines[0]["character"]
            target_sh = 0
            for sh_idx, sh in enumerate(shots):
                if speaker.lower() in [a.lower() for a in sh.get("assets", [])] or speaker.lower() in sh.get("visual", "").lower():
                    target_sh = sh_idx
                    break
            ltype = "deferred" if speaker.upper() == "NARRATOR" else "native"
            dialogue_assignments[(scene_idx, target_sh)] = [{"char": speaker, "text": lines[0]["text"], "type": ltype}]
        else:
            sh_count = len(shots)
            for l_idx, line in enumerate(lines):
                speaker = line["character"]
                ltype = "deferred" if speaker.upper() == "NARRATOR" else "native"
                target_sh = min(l_idx, sh_count - 1)
                for sh_idx in range(sh_count):
                    sh = shots[sh_idx]
                    if speaker.lower() in [a.lower() for a in sh.get("assets", [])] and (scene_idx, sh_idx) not in dialogue_assignments:
                        target_sh = sh_idx
                        break

                key = (scene_idx, target_sh)
                dialogue_assignments.setdefault(key, []).append({"char": speaker, "text": line["text"], "type": ltype})

    return dialogue_assignments


def ensure_trailing_period(text):
    text = text.strip()
    if not text:
        return ""
    if not text.endswith(('.', '!', '?')):
        return text + "."
    return text


def generate_prompt_pack(script_dir, aspect_ratio="16:9", dialogue_overrides=None):
    script_data_path = os.path.join(script_dir, "VideoPrompts", "_script_data.json")
    nametag_map_path = os.path.join(script_dir, "VideoPrompts", "_nametag_map.json")

    if not os.path.exists(script_data_path):
        raise FileNotFoundError(f"Missing script data: {script_data_path}")
    if not os.path.exists(nametag_map_path):
        raise FileNotFoundError(f"Missing nametag map: {nametag_map_path}")

    with open(script_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(nametag_map_path, "r", encoding="utf-8") as f:
        nametags = json.load(f)

    title = data.get("title", "PromptPack")
    props_list = data.get("props", [])
    scenes = data.get("scenes", [])
    full_story_beats = data.get("full_story_beats", [])

    matched = nametags.get("matched", {})
    unmatched = nametags.get("unmatched_assets", [])
    frame_index = nametags.get("frame_index", [])

    # Voice-over handling defaults
    speaking_chars = set()
    for b in full_story_beats:
        for d in b.get("dialogue", []):
            speaking_chars.add(d.get("character", "").strip())

    vo_parts = []
    for sc_name in sorted(speaking_chars):
        if sc_name.upper() == "NARRATOR":
            vo_parts.append(f"{sc_name} — deferred (add in post)")
        else:
            vo_parts.append(f"{sc_name} — native audio")
    vo_plan = "; ".join(vo_parts) if vo_parts else "None — no dialogue in script"

    unresolved_list = [u for u in unmatched if u not in props_list and u.lower() != "narrator"]
    unresolved_str = ", ".join(unresolved_list) if unresolved_list else "None"

    # Align dialogue
    if dialogue_overrides:
        dialogue_assignments = dialogue_overrides
    else:
        dialogue_assignments = align_dialogue_to_scenes_and_shots(scenes, full_story_beats)

    clips_dir = os.path.join(script_dir, "VideoPrompts", "clips")
    os.makedirs(clips_dir, exist_ok=True)

    all_clips = []

    for s_idx, scene in enumerate(scenes):
        heading = scene.get("heading", f"Scene {s_idx+1}")
        for sh_idx, shot in enumerate(scene.get("shots", [])):
            shot_title = shot.get("title", f"Shot {sh_idx+1:02d}")
            visual = shot.get("visual", "")
            motion = shot.get("motion", "")
            audio_text = shot.get("audio", "Ambient room tone.")
            assets = shot.get("assets", [])

            # Frame matching (Frame as ingredient)
            frame_tag = find_frame(shot_title, s_idx, sh_idx, frame_index)

            # Clean visual text & get Character/Location tags
            vis_clean, used_tags = clean_visual_text(visual, assets, matched, unmatched, props_list)

            # Combine references: Frame + Characters + Locations (NO props, NO narrator)
            refs_list = []
            if frame_tag:
                refs_list.append(f"@{frame_tag}")
            for tag in used_tags:
                if tag not in refs_list and tag.lower() != "@narrator":
                    refs_list.append(tag)

            used_refs = ", ".join(refs_list) if refs_list else "None"

            # Context, camera, framing clauses
            context_clause = ensure_trailing_period(heading)
            vis_clause = ensure_trailing_period(vis_clean)
            camera_clause = ensure_trailing_period(motion) if motion else ""
            framing_clause = f"Compose for {aspect_ratio} landscape framing."

            diag_lines = dialogue_assignments.get((s_idx, sh_idx), [])

            if not diag_lines:
                dur = get_base_duration(motion, visual)
                prompt = (
                    f"{context_clause} {vis_clause} {camera_clause} {framing_clause} "
                    f"Duration: {dur}s. Audio: {ensure_trailing_period(audio_text)} No spoken dialogue in this clip."
                )
                prompt = re.sub(r'\s+', ' ', prompt).strip()
                all_clips.append({
                    "s_idx": s_idx,
                    "sh_idx": sh_idx,
                    "heading": heading,
                    "shot_title": shot_title,
                    "suffix": "",
                    "dur": dur,
                    "refs": used_refs,
                    "vo": "None",
                    "prompt": prompt
                })
            else:
                combined_lines = []
                for dl in diag_lines:
                    c = dl["char"]
                    t = dl["text"]
                    t_type = dl["type"]
                    combined_lines.append((c, t, t_type))

                total_words = sum(len(t.split()) for _, t, _ in combined_lines)
                needed = total_words / 2.5

                if needed <= 10 or len(combined_lines) > 1:
                    dur = snap_duration(needed)
                    vo_entries = []
                    diag_directives = []
                    for c, t, t_type in combined_lines:
                        if t_type == "native":
                            vo_entries.append(f'{c} (native audio) — "{t}"')
                            diag_directives.append(f'dialogue spoken on-screen by {c}: "{t}"')
                        else:
                            vo_entries.append(f'{c} (deferred — add in post) — "{t}"')

                    vo_str = " \\n".join(vo_entries)
                    if diag_directives:
                        audio_directive = f"Audio: {audio_text.rstrip('.')}; {'; '.join(diag_directives)}."
                    else:
                        audio_directive = f"Audio: {ensure_trailing_period(audio_text)} No spoken dialogue in this clip."

                    prompt = (
                        f"{context_clause} {vis_clause} {camera_clause} {framing_clause} "
                        f"Duration: {dur}s. {audio_directive}"
                    )
                    prompt = re.sub(r'\s+', ' ', prompt).strip()

                    all_clips.append({
                        "s_idx": s_idx,
                        "sh_idx": sh_idx,
                        "heading": heading,
                        "shot_title": shot_title,
                        "suffix": "",
                        "dur": dur,
                        "refs": used_refs,
                        "vo": vo_str,
                        "prompt": prompt
                    })
                else:
                    c, text, t_type = combined_lines[0]
                    sents = split_sentences(text)
                    mid = max(1, len(sents) // 2)
                    part1 = " ".join(sents[:mid])
                    part2 = " ".join(sents[mid:])

                    dur1 = snap_duration(len(part1.split()) / 2.5)
                    dur2 = snap_duration(len(part2.split()) / 2.5)

                    if t_type == "native":
                        vo1 = f'{c} (native audio) — "{part1}"'
                        vo2 = f'{c} (native audio) — "{part2}"'
                        aud1 = f'Audio: {audio_text.rstrip(".")}; dialogue spoken on-screen by {c}: "{part1}".'
                        aud2 = f'Audio: {audio_text.rstrip(".")}; dialogue spoken on-screen by {c}: "{part2}".'
                    else:
                        vo1 = f'{c} (deferred — add in post) — "{part1}"'
                        vo2 = f'{c} (deferred — add in post) — "{part2}"'
                        aud1 = f'Audio: {ensure_trailing_period(audio_text)} No spoken dialogue in this clip.'
                        aud2 = f'Audio: {ensure_trailing_period(audio_text)} No spoken dialogue in this clip.'

                    prompt1 = f"{context_clause} {vis_clean} (Part 1). {camera_clause} {framing_clause} Duration: {dur1}s. {aud1}"
                    prompt2 = f"{context_clause} {vis_clean} (Part 2). {camera_clause} {framing_clause} Duration: {dur2}s. {aud2}"

                    prompt1 = re.sub(r'\s+', ' ', prompt1).strip()
                    prompt2 = re.sub(r'\s+', ' ', prompt2).strip()

                    all_clips.append({
                        "s_idx": s_idx, "sh_idx": sh_idx, "heading": heading, "shot_title": shot_title,
                        "suffix": "a", "dur": dur1, "refs": used_refs, "vo": vo1, "prompt": prompt1
                    })
                    all_clips.append({
                        "s_idx": s_idx, "sh_idx": sh_idx, "heading": heading, "shot_title": shot_title,
                        "suffix": "b", "dur": dur2, "refs": used_refs, "vo": vo2, "prompt": prompt2
                    })

    # Assemble master markdown
    total_clips = len(all_clips)
    total_runtime = sum(c["dur"] for c in all_clips)

    master_md_path = os.path.join(script_dir, "VideoPrompts", f"{os.path.basename(script_dir)}-flow-prompts.md")

    with open(master_md_path, "w", encoding="utf-8") as f:
        f.write(f"# GOOGLE FLOW VIDEO PROMPT PACK — {title}\n\n")
        f.write(f"**Source script:** {os.path.basename(script_dir)}.md\n")
        f.write(f"**Aspect ratio:** {aspect_ratio}\n")
        f.write(f"**Total clips:** {total_clips}  |  **Total runtime:** {total_runtime}s\n")
        f.write(f"**Voice-over plan:** {vo_plan}\n")
        f.write(f"**Unresolved assets (no reference image, described inline):** {unresolved_str}\n\n")
        f.write("---\n\n")

        current_scene = -1
        for c in all_clips:
            if c["s_idx"] != current_scene:
                current_scene = c["s_idx"]
                f.write(f"## Scene {current_scene+1}: {c['heading']}\n\n")

            f.write(f"### Clip {current_scene+1}.{c['sh_idx']+1}{c['suffix']} — {c['shot_title']}\n")
            f.write(f"**Duration:** {c['dur']}s\n")
            f.write(f"**Aspect ratio:** {aspect_ratio}\n")
            f.write(f"**References:** {c['refs']}\n")
            f.write(f"**Dialogue / Voice-over:** {c['vo']}\n\n")
            f.write(f"**Prompt:**\n{c['prompt']}\n\n")
            f.write("---\n\n")

            # Write clip text file
            clip_fn = f"Scene{current_scene+1:02d}_Shot{c['sh_idx']+1:02d}{c['suffix']}.txt"
            with open(os.path.join(clips_dir, clip_fn), "w", encoding="utf-8") as cf:
                cf.write(c["prompt"])

    print(f"Generated {total_clips} clips ({total_runtime}s total runtime) for '{title}'.")
    print(f"Master file: {master_md_path}")
    print(f"Clips directory: {clips_dir}")
    return master_md_path


def main():
    parser = argparse.ArgumentParser(description="Generic Google Flow Prompt Pack Generator")
    parser.add_argument("script", help="Script name (under Exports/) or full directory path")
    parser.add_argument("--ar", default="16:9", help="Aspect ratio (default: 16:9)")
    args = parser.parse_args()

    # Resolve target directory
    script_target = args.script
    if not os.path.isdir(script_target):
        candidate = os.path.join("Exports", script_target)
        if os.path.isdir(candidate):
            script_target = candidate
        else:
            print(f"Error: Directory not found: {script_target} or {candidate}")
            sys.exit(1)

    generate_prompt_pack(script_target, aspect_ratio=args.ar)


if __name__ == "__main__":
    main()
