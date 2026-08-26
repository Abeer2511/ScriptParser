#!/usr/bin/env python3
"""
generate_voice_profiles.py — Generates a comprehensive VoiceProfiles.md markdown
file containing audio descriptors, acoustic profiles, dynamic emotional states,
and TTS prompts for all characters in a script.

Usage:
    python generate_voice_profiles.py <script_name_or_folder>
"""

import sys
import os
import json
import re
import argparse


def infer_acoustic_profile(char_name, physical, backstory, dialogue_lines, shot_audio_mentions):
    """
    Infer acoustic profile, pitch, timbre, pacing, and archetype based on character data.
    """
    name_lower = char_name.lower()
    phys_lower = physical.lower()
    back_lower = backstory.lower()
    all_context = (physical + " " + backstory + " " + " ".join(shot_audio_mentions)).lower()

    # Determine gender & demographic clues
    is_female = any(w in phys_lower for w in ["woman", "female", "she", "her", "sister", "mother", "daughter", "girl"])
    is_male = any(w in phys_lower for w in ["man", "male", "he", "his", "brother", "father", "son", "boy"])

    age_m = re.search(r'(\d{2})s?|\b(late|early|mid[- ])(\d{2})s?', phys_lower)
    age_str = age_m.group(0) if age_m else "adult"

    # Default traits
    if "narrator" in name_lower:
        archetype = "The Omniscient Chronicler / Elder Statesman"
        demographics = f"Male, {age_str}, Distinguished Standard Atlantic / Neutral Accent"
        pitch = "Low-to-mid Baritone (approx. 95–125 Hz)"
        timbre = "Deep, resonant, warm, weathered, philosophical gravitas"
        pacing = "Deliberate, measured, unhurried (~110–125 WPM)"
        engine_prompt = (
            f"A distinguished, mature male narrator in his {age_str} with a deep, weathered baritone voice. "
            "Calm, authoritative, and philosophical. Delivers lines with deliberate, measured pacing, "
            "rich chest resonance, and warm acoustic intimacy."
        )
        stability, similarity, style = 0.75, 0.85, 0.10
    elif "elara" in name_lower:
        archetype = "The Brilliant Pioneer / Overclocked Mind"
        demographics = f"Female, {age_str}, South Asian descent, educated Mid-Atlantic academic accent"
        pitch = "Mid Alto (approx. 180–220 Hz)"
        timbre = "Crisp, articulate, piercing clarity; shifts between intense analytical flow and fragile whispers"
        pacing = "Dynamic (~95–150 WPM), ranging from breathless rapid-fire clarity to exhausted pauses"
        engine_prompt = (
            f"A brilliant South Asian woman in her {age_str} with a crisp, intelligent mid-alto voice. "
            "Naturally articulate, sharp, and confident. Capable of shifting into a rapid, hyper-focused, "
            "emotionally detached clinical tone, as well as a soft, exhausted, vulnerable emotional whisper."
        )
        stability, similarity, style = 0.55, 0.80, 0.30
    elif "rian" in name_lower:
        archetype = "The Loyal Protector / Stressed Safety Officer"
        demographics = f"Male, {age_str}, Caucasian, working-academic accent"
        pitch = "Low-to-mid Tenor / High Baritone (approx. 110–140 Hz)"
        timbre = "Raspy, strained, gravelly undertones, breathy under chronic stress"
        pacing = "Hesitant, tense, urgent micro-pauses (~125–140 WPM)"
        engine_prompt = (
            f"A Caucasian male technician in his {age_str} with a raspy, strained high-baritone voice. "
            "Sounds perpetually tense, earnest, and deeply concerned. Speaks with an urgent, slightly hesitant cadence, "
            "carrying the weight of past trauma and protective devotion."
        )
        stability, similarity, style = 0.50, 0.80, 0.30
    elif "naomi" in name_lower:
        archetype = "The Human Anchor / The Sister"
        demographics = f"Female, {age_str}, South Asian descent, warm contemporary conversational accent"
        pitch = "Mezzo-Soprano (approx. 200–240 Hz)"
        timbre = "Warm, velvety, highly expressive, prone to tremolo/emotional tightening"
        pacing = "Natural conversational flow (~120–135 WPM), shifting to defensive halts and tearful breaks"
        engine_prompt = (
            f"A warm and expressive South Asian woman in her {age_str} with a melodic mezzo-soprano voice. "
            "Highly emotional, natural, and conversational. Capable of expressing sharp defensive vulnerability, "
            "trembling emotional heartbreak, and tearful, joyous relief."
        )
        stability, similarity, style = 0.55, 0.85, 0.35
    elif "subject" in name_lower:
        archetype = "The Lost Predecessor / Cognitive Casualty"
        demographics = f"Male, {age_str}, East Asian descent, flat neutral speech"
        pitch = "Mid-Tenor (approx. 130–160 Hz)"
        timbre = "Deadened, monotone, hollow, devoid of prosodic inflection"
        pacing = "Metronomic, rhythmic, uncanny stillness (~110 WPM)"
        engine_prompt = (
            f"A young man in his {age_str} speaking in a deadened, flat, monotone voice. "
            "Uncannily devoid of emotional inflection or vocal dynamics, delivered with metronomic stillness "
            "as if experiencing all points of time simultaneously. Low-fidelity archival texture."
        )
        stability, similarity, style = 0.95, 0.85, 0.00
    elif "director" in name_lower:
        archetype = "The Institutional Utilitarian / Pragmatist"
        demographics = f"Female, {age_str}, Middle Eastern descent, refined commanding international English accent"
        pitch = "Low Alto / Contralto (approx. 150–185 Hz)"
        timbre = "Polished, icy, resonant, razor-sharp sibilance, unhurried weight"
        pacing = "Slow, deliberate, unflinching (~105–115 WPM)"
        engine_prompt = (
            f"A commanding, sophisticated woman in her {age_str} with a polished, low-alto voice. "
            "Speaks with razor-sharp articulation, icy composure, and unhurried corporate-scientific authority. "
            "Velvety smooth yet entirely uncompromising."
        )
        stability, similarity, style = 0.80, 0.90, 0.15
    elif "elias" in name_lower:
        archetype = "The Obsessive Visionary / Reluctant Pioneer"
        demographics = f"Male, {age_str}, Central European / Ashkenazi descent, 1900s intellectual accent"
        pitch = "Mid Tenor (approx. 120–150 Hz)"
        timbre = "Nervous, rapid, breathy, intense, crackling with intellectual restlessness"
        pacing = "Fast, muttered, halting (~135–155 WPM)"
        engine_prompt = (
            f"A young intellectual man in his {age_str} with a nervous, intense mid-tenor voice. "
            "Speaks with restless urgency, muttered introspection, and breathy intellectual passion."
        )
        stability, similarity, style = 0.45, 0.80, 0.35
    elif "julian" in name_lower:
        archetype = "The Innocent Youth / Tragic Catalyst"
        demographics = f"Male, {age_str}, warm youthful European accent"
        pitch = "Bright Tenor (approx. 140–170 Hz)"
        timbre = "Warm, resonant, optimistic, buoyant, full-chested"
        pacing = "Brisk, cheerful, open (~125–140 WPM)"
        engine_prompt = (
            f"A vibrant young man in his {age_str} with a bright, cheerful tenor voice. "
            "Optimistic, warm, open-hearted, and buoyant."
        )
        stability, similarity, style = 0.65, 0.80, 0.20
    elif "postman" in name_lower:
        archetype = "The Rhythmic Commoner / Routine Messenger"
        demographics = f"Male, {age_str}, Swiss / Continental working-class accent"
        pitch = "Robust Baritone (approx. 100–130 Hz)"
        timbre = "Gravelly, boisterous, wind-burned, sturdy, rhythmic"
        pacing = "Steady, cadence-driven (~115–125 WPM)"
        engine_prompt = (
            f"A sturdy middle-aged working-class male in his {age_str} with a hearty, gravelly baritone voice. "
            "Pragmatic, friendly, and grounded."
        )
        stability, similarity, style = 0.70, 0.80, 0.15
    else:
        gender_word = "female" if is_female else "male"
        archetype = "Supporting Character"
        demographics = f"{gender_word.capitalize()}, {age_str}, Neutral accent"
        pitch = "Mid Register"
        timbre = "Natural, clear, conversational"
        pacing = "Standard conversational (~120 WPM)"
        engine_prompt = (
            f"A natural {gender_word} voice for a character in their {age_str}. "
            "Clear, balanced articulation and authentic conversational delivery."
        )
        stability, similarity, style = 0.60, 0.80, 0.25

    return {
        "archetype": archetype,
        "demographics": demographics,
        "pitch": pitch,
        "timbre": timbre,
        "pacing": pacing,
        "engine_prompt": engine_prompt,
        "stability": stability,
        "similarity": similarity,
        "style": style,
    }


def generate_voice_profiles(script_dir):
    script_data_path = os.path.join(script_dir, "VideoPrompts", "_script_data.json")
    if not os.path.exists(script_data_path):
        # Try finding markdown directly
        script_name = os.path.basename(os.path.abspath(script_dir))
        md_path = os.path.join(script_dir, "Markdowns", f"{script_name}.md")
        if not os.path.exists(md_path):
            raise FileNotFoundError(f"Neither _script_data.json nor {md_path} was found.")
        # Auto-parse script into temp or target
        from parse_script import main as parse_main
        os.makedirs(os.path.join(script_dir, "VideoPrompts"), exist_ok=True)
        sys.argv = ["parse_script.py", md_path, script_data_path]
        parse_main()

    with open(script_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    title = data.get("title", "Voice Profiles")
    characters = data.get("characters", [])
    full_story_beats = data.get("full_story_beats", [])
    scenes = data.get("scenes", [])

    # Collect dialogue lines per character
    char_dialogues = {}
    for beat in full_story_beats:
        for diag in beat.get("dialogue", []):
            char_name = diag.get("character", "").strip()
            text = diag.get("text", "").strip()
            paren = diag.get("parenthetical")
            if char_name and text:
                char_dialogues.setdefault(char_name.upper(), []).append({"text": text, "paren": paren})

    # Collect audio mentions per character from scenes/shots
    char_shot_audio = {}
    for sc in scenes:
        for sh in sc.get("shots", []):
            audio_text = sh.get("audio", "")
            for asset in sh.get("assets", []):
                char_shot_audio.setdefault(asset.upper(), []).append(audio_text)

    # Build profiles
    profiles = []
    for char in characters:
        name = char.get("name", "").strip()
        name_key = name.upper()
        phys = char.get("physical", "")
        clothing = char.get("clothing", "")
        backstory = char.get("backstory", "")
        lines = char_dialogues.get(name_key, [])
        shot_audios = char_shot_audio.get(name_key, [])

        inferred = infer_acoustic_profile(name, phys, backstory, lines, shot_audios)
        profiles.append({
            "name": name,
            "physical": phys,
            "clothing": clothing,
            "backstory": backstory,
            "lines": lines,
            "inferred": inferred
        })

    # Add any speaking character not explicitly declared in ## Characters
    declared_names = {c["name"].upper() for c in characters}
    for spoken_name, lines in char_dialogues.items():
        if spoken_name not in declared_names:
            inferred = infer_acoustic_profile(spoken_name, "", "", lines, [])
            profiles.append({
                "name": spoken_name.title(),
                "physical": "Supporting vocal character.",
                "clothing": "N/A",
                "backstory": "N/A",
                "lines": lines,
                "inferred": inferred
            })

    # Render Markdown
    out_file = os.path.join(script_dir, "VoiceProfiles.md")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"# CHARACTER VOICE PROFILES & AUDIO DESCRIPTORS\n")
        f.write(f"## Project: {title}\n\n")
        f.write(f"This document defines the complete acoustic profiles, vocal characteristics, emotional dynamics, "
                f"and text-to-speech (TTS) / AI voice generation prompts for all characters in **{title}**.\n\n")
        f.write("---\n\n")
        f.write("### Table of Contents\n")
        for idx, p in enumerate(profiles, 1):
            anchor = re.sub(r'[^a-z0-9\-]', '', p['name'].lower().replace(' ', '-'))
            f.write(f"{idx}. [{p['name']}](#{idx}-{anchor})\n")
        f.write(f"{len(profiles)+1}. [Engine Settings & Implementation Guidelines](#{len(profiles)+1}-engine-settings--implementation-guidelines)\n\n")
        f.write("---\n\n")

        for idx, p in enumerate(profiles, 1):
            name = p["name"]
            inf = p["inferred"]
            is_narrator = "narrator" in name.lower()
            tag_str = "Narrator (Non-diegetic VO)" if is_narrator else f"@{name}"

            f.write(f"## {idx}. {name}\n\n")
            f.write("| Field | Specification |\n")
            f.write("| :--- | :--- |\n")
            f.write(f"| **Asset / Tag** | `{tag_str}` |\n")
            f.write(f"| **Archetype** | {inf['archetype']} |\n")
            f.write(f"| **Demographics** | {inf['demographics']} |\n")
            f.write(f"| **Pitch & Register** | {inf['pitch']} |\n")
            f.write(f"| **Timbre & Texture** | {inf['timbre']} |\n")
            f.write(f"| **Pacing & Cadence** | {inf['pacing']} |\n")
            if p["backstory"] and p["backstory"] != "N/A":
                f.write(f"| **Character Background** | {p['backstory']} |\n")
            f.write("\n")

            f.write("### TTS Generation Prompt (ElevenLabs / Gemini / OpenAI / Flow)\n")
            f.write("```text\n")
            f.write(f"{inf['engine_prompt']}\n")
            f.write("```\n\n")

            if p["lines"]:
                f.write("### Key Script Line Performance Directives\n")
                # Pick up to 5 representative lines
                sample_lines = p["lines"][:5]
                for l_item in sample_lines:
                    paren = f" *({l_item['paren']})*" if l_item["paren"] else ""
                    f.write(f"- *\"{l_item['text']}\"*{paren}\n")
                    f.write(f"  - **Directive:** Deliver in character's signature {inf['pitch'].split('(')[0].strip().lower()} register with {inf['timbre'].split(',')[0].strip().lower()} tone.\n")
                f.write("\n")

            f.write("---\n\n")

        # Engine Settings Summary Table
        f.write(f"## {len(profiles)+1}. Engine Settings & Implementation Guidelines\n\n")
        f.write("### ElevenLabs Voice Design & Multilingual v2 Recommended Parameters\n\n")
        f.write("| Character | Voice Archetype | Stability | Similarity / Clarity | Style Exaggeration |\n")
        f.write("| :--- | :--- | :---: | :---: | :---: |\n")
        for p in profiles:
            inf = p["inferred"]
            f.write(f"| **{p['name']}** | {inf['archetype']} | `{inf['stability']:.2f}` | `{inf['similarity']:.2f}` | `{inf['style']:.2f}` |\n")

        f.write("\n### Google Flow Video Prompt Audio Directives\n")
        f.write("When generating native audio lip-sync clips in Google Flow prompt packs, pair the character's vocal register with their dialogue text:\n")
        f.write("- **On-screen characters:** `Audio: [ambient sound]; dialogue spoken on-screen by [NAME] in a [vocal descriptor] voice: \"[Line]\".`\n")
        f.write("- **Narrator (deferred):** `Audio: [ambient sound] No spoken dialogue in this clip.` (Narrator audio is mixed non-diegetically in post-production).\n")

    print(f"[SUCCESS] Voice profiles generated at: {out_file}")
    return out_file


def main():
    parser = argparse.ArgumentParser(description="Generate VoiceProfiles.md for a script")
    parser.add_argument("script", help="Script name (under Exports/) or full directory path")
    args = parser.parse_args()

    script_target = args.script
    if not os.path.isdir(script_target):
        candidate = os.path.join("Exports", script_target)
        if os.path.isdir(candidate):
            script_target = candidate
        else:
            print(f"Error: Directory not found: {script_target} or {candidate}")
            sys.exit(1)

    generate_voice_profiles(script_target)


if __name__ == "__main__":
    main()
