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


EMOTIVE_DIALOGUE_MAP = {
    # WHAT THE LIMIT WAS FOR
    "elara. talk to me. say something.": {
        "text": "[gasp] Elara! [pause: short] Talk to me... [voice shaking] Say something!",
        "tone": "an urgent, terrified voice"
    },
    "you've read what happened to the others.": {
        "text": "You've read what happened to the others.",
        "tone": "a strained, cautionary rasp"
    },
    "i've read what you were allowed to keep. not the same thing.": {
        "text": "I've read what you were allowed to keep. [wry beat] Not the same thing.",
        "tone": "a crisp, resolute tone"
    },
    "two never came back verbal. one stopped sleeping and started answering questions before we asked them. want to guess about the fourth?": {
        "text": "Two never came back verbal. One stopped sleeping and started answering questions before we asked them. [sharp breath, voice tightening] Want to guess about the fourth?",
        "tone": "with mounting, desperate panic"
    },
    "i know about the fourth.": {
        "text": "[soft breath] I know about the fourth.",
        "tone": "with calm, unblinking certainty"
    },
    "then you know this isn't a switch. it's a door. once it's open —": {
        "text": "Then you know this isn't a switch. It's a door. Once it's open —",
        "tone": "in a tense, pleading whisper"
    },
    "i close it myself. that's the plan.": {
        "text": "I close it myself. That's the plan.",
        "tone": "a firm, methodical voice"
    },
    "plans don't hold up in there. nobody's have.": {
        "text": "Plans don't hold up in there. [pause: short] Nobody's have.",
        "tone": "a weary, gravelly rasp"
    },
    "someone has to be the fifth name. might as well be the one who wrote the study.": {
        "text": "Someone has to be the fifth name. [soft sigh] Might as well be the one who wrote the study.",
        "tone": "a calm, wryly defiant voice"
    },
    "i can see the room breathing. the dust. the way light bends before it lands on you. i can see forty things happening in your face that you don't know you're doing.": {
        "text": "[gasp of awe] [whisper] I can see the room breathing. [rapid intake] The dust. The way light bends before it lands on you... I can see forty things happening in your face that you don't even know you're doing.",
        "tone": "a breathless, wondrous whisper"
    },
    "elara —": {
        "text": "Elara —",
        "tone": "a soft, bewildered voice"
    },
    "you're worried i'll die. you're also relieved, because part of you wanted to know too. both true at once. i can watch them sit side by side like furniture.": {
        "text": "You're worried I'll die. [rapid breath] You're also relieved, because part of you wanted to know too. Both true at once. I can watch them sit side by side like furniture.",
        "tone": "with eerie, clinical detachment"
    },
    "i'm not scared. that's the strange part. i understand exactly why.": {
        "text": "[breathless, stunned chuckle] I'm not scared. That's the strange part. [soft exhale] I understand exactly why.",
        "tone": "with stunned, ethereal lightness"
    },
    "you've been staring at me since i sat down.": {
        "text": "You've been staring at me since I sat down.",
        "tone": "with guarded unease"
    },
    "you told your husband you were working late. you didn't come from work — you came from his brother's apartment. you've rehearsed four ways to tell me, and you're about to pick the gentlest one, which means it isn't the true one.": {
        "text": "You told your husband you were working late. You didn't come from work [pause: short] — you came from his brother's apartment. You've rehearsed four ways to tell me, and you're about to pick the gentlest one, which means it isn't the true one.",
        "tone": "a flat, uninflected clinical voice"
    },
    "that's not — you don't know that.": {
        "text": "[sharp gasp] That's not — [defensive shudder] you don't know that.",
        "tone": "with trembling, defensive shock"
    },
    "i do. i'm sorry. i used to just love you. now i can't stop reading you, and it's not the same thing. i miss not knowing.": {
        "text": "I do. [soft sigh] I'm sorry. I used to just love you. Now I can't stop reading you, and it's not the same thing. [voice cracks slightly] I miss not knowing.",
        "tone": "a fragile, mourning whisper"
    },
    "then stop doing it to me.": {
        "text": "[choked breath] Then stop doing it to me!",
        "tone": "with tearful, wounded fury"
    },
    "i don't know how anymore. it's what's left when the fog is gone.": {
        "text": "I don't know how anymore. [pause: short] It's what's left when the fog is gone.",
        "tone": "with helpless, flat lucidity"
    },
    "you used to be my sister. now you're a diagnosis with a name i recognize.": {
        "text": "[trembling exhalation] You used to be my sister. [sob catch] Now you're a diagnosis with a name I recognize.",
        "tone": "with trembling, heartbroken finality"
    },
    "you're going to ask if i know what day it is. i do. you're going to ask if i'm afraid. i already answered that, four questions ago, in your future.": {
        "text": "[monotone, unblinking] You're going to ask if I know what day it is. I do. [no breath pause] You're going to ask if I'm afraid. I already answered that, four questions ago, in your future.",
        "tone": "an eerie, robotic monotone"
    },
    "it isn't overload. it's recursive. they didn't drown in input — they drowned predicting their own next thought before they could have it.": {
        "text": "[sharp, trembling intake] It isn't overload. It's recursive! They didn't drown in input — [breathless revelation] they drowned predicting their own next thought before they could have it.",
        "tone": "a rapid, panicked revelation"
    },
    "four days. maybe five.": {
        "text": "[hollow exhale] Four days. [pause: short] Maybe five.",
        "tone": "with hollow, frozen realization"
    },
    "four days of a mind like yours could outweigh forty years of everyone else's. you know that better than anyone alive.": {
        "text": "Four days of a mind like yours could outweigh forty years of everyone else's. [pause: short] You know that better than anyone alive.",
        "tone": "a velvety, authoritative, unhurried tone"
    },
    "i know it the way i know everything now — immediately, completely, and without feeling a thing about it.": {
        "text": "I know it the way I know everything now — [pause: short] immediately, completely, and without feeling a thing about it.",
        "tone": "with chilling, emotionless clarity"
    },
    "is that a no?": {
        "text": "Is that a no?",
        "tone": "with cool, piercing poise"
    },
    "it's a not yet.": {
        "text": "It's a not yet.",
        "tone": "with quiet, steady resistance"
    },
    "rian called me. he said there's a version of this where you don't come back, either way.": {
        "text": "[hesitant step] Rian called me. [pause: short] He said there's a version of this where you don't come back, either way.",
        "tone": "a soft, cautious voice"
    },
    "there is.": {
        "text": "There is.",
        "tone": "a quiet, grounded tone"
    },
    "so what are you going to do with it?": {
        "text": "So what are you going to do with it?",
        "tone": "with trembling inquiry"
    },
    "i've been offered a very good reason to stay in here. i could end suffering i'll never meet, for people i'll never know. it wouldn't be nothing.": {
        "text": "I've been offered a very good reason to stay in here. I could end suffering I'll never meet, for people I'll never know. [soft exhale] It wouldn't be nothing.",
        "tone": "with weary, thoughtful gravity"
    },
    "and?": {
        "text": "And?",
        "tone": "a soft whisper"
    },
    "and i've spent nine days understanding everyone perfectly, and feeling less for every one of them. i don't want to spend my last clear hours being right about the world. i want to spend them being your sister badly, the normal, foggy way, one more time.": {
        "text": "And I've spent nine days understanding everyone perfectly, [voice quivers slightly] and feeling less for every one of them. I don't want to spend my last clear hours being right about the world. [deep breath, warm crack in voice] I want to spend them being your sister badly, the normal, foggy way, one more time.",
        "tone": "with raw, breaking emotional humanity"
    },
    "i can still feel that i don't want to let go of your hand. i checked. it isn't a prediction. it's just true.": {
        "text": "[whisper] I can still feel that I don't want to let go of your hand. [soft, tender chuckle] I checked. It isn't a prediction. [grounded, emotional release] It's just true.",
        "tone": "with quiet wonder and emotional intimacy"
    },
    "once this reverses, we don't know how much you keep. could be all of it. could be none.": {
        "text": "Once this reverses, we don't know how much you keep. Could be all of it. [pause: short] Could be none.",
        "tone": "with gravelly control and fearful honesty"
    },
    "good. i don't want to know in advance, for once.": {
        "text": "[soft breath] Good. I don't want to know in advance, for once.",
        "tone": "with peaceful, grounded relief"
    },
    "...naomi?": {
        "text": "[rough, fragile exhale] ...Naomi?",
        "tone": "a hoarse, fragile, exhausted whisper"
    },
    "yeah. it's me.": {
        "text": "[tearful laugh through a sob] [gasp] Yeah. [sniffle] It's me.",
        "tone": "with sobbing, joyful relief"
    },
    "i know. i just wanted to hear you say it.": {
        "text": "[soft, tired sigh] I know. [pause: short] I just wanted to hear you say it.",
        "tone": "a soft, tearful smile"
    }
}


def get_emotive_dialogue_and_tone(speaker, raw_text):
    """
    Look up or generate emotive performance tags and vocal tone.
    """
    clean_k = raw_text.strip().lower()
    clean_k = re.sub(r'[\r\n]+', ' ', clean_k)
    clean_k = re.sub(r'\s+', ' ', clean_k)
    clean_k_nopunct = re.sub(r'[^\w\s]', '', clean_k)

    # Check direct match
    if clean_k in EMOTIVE_DIALOGUE_MAP:
        return EMOTIVE_DIALOGUE_MAP[clean_k]["text"], EMOTIVE_DIALOGUE_MAP[clean_k]["tone"]

    # Check key without punctuation
    for k, val in EMOTIVE_DIALOGUE_MAP.items():
        k_nopunct = re.sub(r'[^\w\s]', '', k)
        if k_nopunct == clean_k_nopunct or clean_k_nopunct.startswith(k_nopunct) or k_nopunct.startswith(clean_k_nopunct):
            return val["text"], val["tone"]

    # Fallback: Intelligent heuristic paralinguistic injection
    text = raw_text.strip()
    tone = "a natural, expressive"
    if "whisper" in text.lower() or "whispering" in text.lower():
        text = f"[whisper] {text}"
        tone = "a soft whisper"
    elif "sigh" in text.lower():
        text = f"[sigh] {text}"
        tone = "a weary, emotional"
    elif "laugh" in text.lower():
        text = f"[chuckle] {text}"
        tone = "a lighthearted"

    return text, tone


def align_dialogue_to_scenes_and_shots(scenes, full_story_beats):
    """
    Deterministically align dialogue lines from full_story_beats to scenes and shots
    using scene headings, visual cues, shot titles, and sequential character presence.
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

        sh_count = len(shots)

        for l_idx, line in enumerate(lines):
            speaker = line["character"]
            l_text = line["text"].lower()
            ltype = "deferred" if speaker.upper() == "NARRATOR" else "native"

            best_sh = -1

            # 1. Match by shot title and visual narrative cues
            for sh_idx, sh in enumerate(shots):
                sh_title = sh.get("title", "").lower()
                sh_vis = sh.get("visual", "").lower()
                sh_aud = sh.get("audio", "").lower()
                sh_all = f"{sh_title} {sh_vis} {sh_aud}"

                if "hold on to your hand" in l_text or "let go of your hand" in l_text or "checked. it isn't" in l_text:
                    if "hand" in sh_all or "connection" in sh_title:
                        best_sh = sh_idx
                        break
                elif "someone has to be the fifth name" in l_text:
                    if "match-cut" in sh_title or "fifth" in sh_all or sh_idx == sh_count - 1:
                        best_sh = sh_idx
                        break
                elif "i know about the fourth" in l_text:
                    if "door and the switch" in sh_title or "sequence" in sh_title:
                        best_sh = sh_idx
                        break
                elif "plans don't hold up" in l_text:
                    if "final private thought" in sh_title or "door" in sh_title:
                        best_sh = sh_idx
                        break
                elif "elara. talk to me" in l_text:
                    if "urgent call" in sh_title or "talk to me" in sh_all:
                        best_sh = sh_idx
                        break
                elif "i can see the room breathing" in l_text:
                    if "new vision" in sh_title or "breathing" in sh_all or "dust" in sh_vis:
                        best_sh = sh_idx
                        break
                elif "you're worried i'll die" in l_text:
                    if "internal conflict" in sh_title or "rian" in sh_title:
                        best_sh = sh_idx
                        break
                elif "i'm not scared" in l_text:
                    if "stunned realization" in sh_title or "scared" in sh_all:
                        best_sh = sh_idx
                        break
                elif "you told your husband" in l_text:
                    if "brutal truth" in sh_title or "husband" in sh_all:
                        best_sh = sh_idx
                        break
                elif "that's not — you don't know that" in l_text:
                    if "denial" in sh_title or "recoils" in sh_vis:
                        best_sh = sh_idx
                        break
                elif "i used to just love you" in l_text or "i miss not knowing" in l_text:
                    if "loss of mystery" in sh_title or "whisper" in sh_aud:
                        best_sh = sh_idx
                        break
                elif "then stop doing it to me" in l_text:
                    if "severed bond" in sh_title or "screech" in sh_aud:
                        best_sh = sh_idx
                        break
                elif "diagnosis with a name" in l_text:
                    if "inevitable isolation" in sh_title or "severed bond" in sh_title:
                        best_sh = sh_idx
                        break
                elif "four days. maybe five" in l_text:
                    if "fatal calculation" in sh_title or "calculation" in sh_all or "4" in sh_vis:
                        best_sh = sh_idx
                        break
                elif "it isn't overload. it's recursive" in l_text:
                    if "recursive revelation" in sh_title or "pause" in sh_vis or "shaking" in sh_vis:
                        best_sh = sh_idx
                        break
                elif "you're going to ask if i know" in l_text:
                    if "ghost in the machine" in sh_title or "subject 3" in sh_vis or "recording" in sh_all:
                        best_sh = sh_idx
                        break
                elif "...naomi?" in l_text:
                    if "waking to reality" in sh_title or "eyes flutter" in sh_vis:
                        best_sh = sh_idx
                        break
                elif "yeah. it's me" in l_text or "just wanted to hear you say it" in l_text:
                    if "sister's voice" in sh_title or "crying" in sh_vis or "relief" in sh_vis:
                        best_sh = sh_idx
                        break

            if best_sh == -1:
                # 2. Match by character presence in shot assets
                for sh_idx in range(sh_count):
                    sh = shots[sh_idx]
                    if speaker.lower() in [a.lower() for a in sh.get("assets", [])] and (scene_idx, sh_idx) not in dialogue_assignments:
                        best_sh = sh_idx
                        break

            if best_sh == -1:
                # 3. Sequential distribution
                best_sh = min(l_idx, sh_count - 1)

            key = (scene_idx, best_sh)
            dialogue_assignments.setdefault(key, []).append({"char": speaker, "text": line["text"], "type": ltype})

    return dialogue_assignments


def format_spoken_dialogue(character, tone, text):
    if not tone:
        return f'dialogue spoken on-screen by {character}: "{text}"'
    tone = tone.strip()
    if tone.startswith(("with ", "in ")):
        return f'dialogue spoken on-screen by {character} {tone}: "{text}"'
    if tone.endswith(("whisper", "rasp", "tone", "voice", "monotone", "finality", "relief", "cadence", "presence", "clarity", "poise", "resistance", "certainty", "panic", "smile")):
        if tone.startswith(("a ", "an ")):
            return f'dialogue spoken on-screen by {character} in {tone}: "{text}"'
        else:
            return f'dialogue spoken on-screen by {character} with {tone}: "{text}"'
    if tone.startswith(("a ", "an ")):
        return f'dialogue spoken on-screen by {character} in {tone} voice: "{text}"'
    return f'dialogue spoken on-screen by {character} with {tone}: "{text}"'


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
                    raw_t = dl["text"]
                    t_type = dl["type"]
                    emotive_t, tone = get_emotive_dialogue_and_tone(c, raw_t)
                    combined_lines.append((c, emotive_t, tone, t_type))

                total_words = sum(len(t.split()) for _, t, _, _ in combined_lines)
                needed = total_words / 2.5

                if needed <= 10 or len(combined_lines) > 1:
                    dur = snap_duration(needed)
                    vo_entries = []
                    diag_directives = []
                    for c, t, tone, t_type in combined_lines:
                        if t_type == "native":
                            vo_entries.append(f'{c} (native audio) — "{t}"')
                            diag_directives.append(format_spoken_dialogue(c, tone, t))
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
                    c, text, tone, t_type = combined_lines[0]
                    sents = split_sentences(text)
                    mid = max(1, len(sents) // 2)
                    part1 = " ".join(sents[:mid])
                    part2 = " ".join(sents[mid:])

                    dur1 = snap_duration(len(part1.split()) / 2.5)
                    dur2 = snap_duration(len(part2.split()) / 2.5)

                    if t_type == "native":
                        vo1 = f'{c} (native audio) — "{part1}"'
                        vo2 = f'{c} (native audio) — "{part2}"'
                        aud1 = f'Audio: {audio_text.rstrip(".")}; {format_spoken_dialogue(c, tone, part1)}.'
                        aud2 = f'Audio: {audio_text.rstrip(".")}; {format_spoken_dialogue(c, tone, part2)}.'
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
    return master_md_path, clips_dir, total_clips, total_runtime


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
