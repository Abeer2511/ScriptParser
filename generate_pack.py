import json
import os
import re
import math

with open(r'f:\ScriptParser\Script1\VideoPrompts\_script_data.json', encoding='utf-8') as f:
    data = json.load(f)

with open(r'f:\ScriptParser\Script1\VideoPrompts\_nametag_map.json', encoding='utf-8') as f:
    nametags = json.load(f)

matched = nametags.get('matched', {})
unmatched = nametags.get('unmatched_assets', [])
frames = nametags.get('frame_index', [])

props_list = data.get('props', [])

dialogue_assignments = {
    (1, 1): [{"char": "NARRATOR", "text": "What if the most dangerous invention in human history wasn’t an explosive? What if it wasn’t born in a top-secret military bunker, but on a cluttered wooden desk?", "type": "deferred"}],
    (2, 3): [{"char": "NARRATOR", "text": "The world is accelerating. This is his job. Day after day, inventors send their dreams to the office. But Elias has a mind that sees past the mechanics.", "type": "deferred"}],
    (3, 0): [{"char": "NARRATOR", "text": "For three years, he has spent his evenings in a cramped apartment, ignoring the world outside, trying to solve an equation that no one else even knows exists.", "type": "deferred"}],
    (3, 1): [{"char": "ELIAS", "text": "If the resonance frequency matches the electromagnetic drag... then the local entropy shouldn't just stabilize. It should...", "type": "native"}],
    (3, 4): [{"char": "NARRATOR", "text": "He hasn't synchronized time. He has inverted it.", "type": "deferred"}],
    (5, 0): [{"char": "NARRATOR", "text": "The power of a god, sitting on a wooden table.", "type": "deferred"}],
    (5, 4): [{"char": "NARRATOR", "text": "He could publish this. He would be the most famous man to ever live. Kings would bow to him. Wars could be undone. Death itself could be outmaneuvered.", "type": "deferred"}],
    (5, 5): [{"char": "NARRATOR", "text": "He wouldn't need to explain it to the world. He only needs to turn the dial fourteen degrees, expand the field to encompass the valley, and walk out the door.", "type": "deferred"}],
    (6, 2): [{"char": "ELIAS", "text": "Just fourteen hours. Just one day. I save him, and then I destroy it. Just this once.", "type": "native"}],
    (8, 4): [{"char": "NARRATOR", "text": "The universe is not a machine. It does not like to be forced into reverse.", "type": "deferred"}],
    (8, 3): [{"char": "NARRATOR", "text": "If he goes back to save Julian, the grief that drove him to build the machine is erased. If the grief is erased, he never turns the dial.", "type": "deferred"}],
    (10, 0): [{"char": "NARRATOR", "text": "He has a choice. Save his brother and risk the annihilation of reality. Or let the tragedy stand.", "type": "deferred"}],
    (10, 4): [{"char": "ELIAS", "text": "I'm sorry. Julian, I'm so sorry.", "type": "native"}],
    (12, 3): [{"char": "NARRATOR", "text": "What if the greatest discovery in human history wasn’t announced to the world? What if the man who held the power realized that humanity is not meant to rewrite its own story?", "type": "deferred"}],
}

os.makedirs(r'f:\ScriptParser\Script1\VideoPrompts\clips', exist_ok=True)

pack_file = open(r'f:\ScriptParser\Script1\VideoPrompts\Script1-flow-prompts.md', 'w', encoding='utf-8')

title = data.get('title', 'Script1')
unresolved_str = ', '.join([u for u in unmatched if u not in props_list]) if [u for u in unmatched if u not in props_list] else 'None'
vo_plan = "NARRATOR — deferred (add in post); ELIAS — native audio"
ar = "16:9"

def get_base_duration(motion, visual):
    text = (motion + " " + visual).lower()
    if any(c in text for c in ["slow orbit", "wide establishing", "extended dissolve", "long pull-back", "slow pan", "sweeping pan"]):
        return 10
    if any(c in text for c in ["push-in", "dolly", "tracking shot", "rack focus", "pull-back", "zoom in", "zoom-in"]):
        return 8
    if any(c in text for c in ["match-cut", "whip-pan", "smash-cut", "quick cut", "sharp action", "extreme close-up", "extreme-close-up"]):
        return 4
    return 6

def snap_duration(needed):
    if needed <= 4: return 4
    if needed <= 6: return 6
    if needed <= 8: return 8
    if needed <= 10: return 10
    return 10

def replace_assets(text, assets_list):
    res = text
    used = []
    # Replace matched assets with @nametag
    for a in assets_list:
        if a in props_list:
            continue # ignore props entirely
        
        if a in matched:
            tag = matched[a]['nametag']
            res = re.sub(rf'\b{re.escape(a)}\b', f'@{tag}', res, flags=re.IGNORECASE)
            used.append(f"@{tag}")
        elif a in unmatched:
            res = re.sub(rf'\b{re.escape(a)}\b', f'{a} (no reference image - visualize {a.lower()})', res, flags=re.IGNORECASE)
    return res, used

def get_frame(s_idx, sh_idx, heading, shot_title):
    if shot_title:
        clean_title = shot_title.lower().strip()
        for f in frames:
            clean_f = f.lower().replace('.png', '').replace('.jpg', '').strip()
            if clean_title == clean_f or clean_title in clean_f:
                return f.replace('.png', '').replace('.jpg', '')
    
    # fallback
    target = f"Scene{s_idx+1}_Shot{sh_idx+1}"
    for f in frames:
        if target.lower() in f.lower():
            return f.replace('.png', '').replace('.jpg', '')
    return None

def split_sentences(text):
    return re.split(r'(?<=[.!?])\s+', text)

all_clips = []

for s_idx, scene in enumerate(data.get('scenes', [])):
    heading = scene.get('heading', '')
    for sh_idx, shot in enumerate(scene.get('shots', [])):
        visual = shot.get('visual', '')
        motion = shot.get('motion', '')
        audio_text = shot.get('audio', 'Ambient room tone.')
        assets = shot.get('assets', [])
        
        diag_lines = dialogue_assignments.get((s_idx, sh_idx), [])
        
        clips_for_shot = []
        
        vis_mod, used_tags = replace_assets(visual, assets)
        
        frame = get_frame(s_idx, sh_idx, heading, shot.get('title', ''))
        
        if frame:
            used_tags.append(f"@{frame}")
            vis_mod = f"Base composition: @{frame}. " + vis_mod
            
        if not used_tags: used_refs = "None"
        else: used_refs = ", ".join(list(set(used_tags)))
        
        context_str = f"Scene context: {heading}."
        camera_str = f"Camera/motion: {motion}"
        framing_str = f"Compose for {ar} landscape framing."
        
        if not diag_lines:
            dur = get_base_duration(motion, visual)
            prompt = f"{context_str} Action: {vis_mod} {camera_str} {framing_str} Duration: {dur}s. Audio: {audio_text}. No spoken dialogue in this clip."
            clips_for_shot.append({
                "suffix": "",
                "dur": dur,
                "refs": used_refs,
                "vo": "None",
                "prompt": prompt
            })
        else:
            line = diag_lines[0]
            char = line['char']
            text = line['text']
            ltype = line['type']
            
            if ltype == "native":
                words = len(text.split())
                needed = words / 2.5
                if needed <= 10:
                    dur = snap_duration(needed)
                    vo_str = f"{char} (native audio) — \"{text}\""
                    prompt = f"{context_str} Action: {vis_mod} {camera_str} {framing_str} Duration: {dur}s. Audio: {audio_text}; dialogue spoken on-screen by {char}: \"{text}\""
                    clips_for_shot.append({
                        "suffix": "", "dur": dur, "refs": used_refs, "vo": vo_str, "prompt": prompt
                    })
                else:
                    sents = split_sentences(text)
                    mid = len(sents)//2
                    part1 = " ".join(sents[:mid])
                    part2 = " ".join(sents[mid:])
                    dur1 = snap_duration(len(part1.split())/2.5)
                    dur2 = snap_duration(len(part2.split())/2.5)
                    
                    vo_str1 = f"{char} (native audio) — \"{part1}\""
                    prompt1 = f"{context_str} Action: {vis_mod} (Part 1). {camera_str} {framing_str} Duration: {dur1}s. Audio: {audio_text}; dialogue spoken on-screen by {char}: \"{part1}\""
                    clips_for_shot.append({
                        "suffix": "a", "dur": dur1, "refs": used_refs, "vo": vo_str1, "prompt": prompt1
                    })
                    
                    vo_str2 = f"{char} (native audio) — \"{part2}\""
                    prompt2 = f"{context_str} Action: {vis_mod} (Part 2). {camera_str} {framing_str} Duration: {dur2}s. Audio: {audio_text}; dialogue spoken on-screen by {char}: \"{part2}\""
                    clips_for_shot.append({
                        "suffix": "b", "dur": dur2, "refs": used_refs, "vo": vo_str2, "prompt": prompt2
                    })
            else:
                words = len(text.split())
                needed = words / 2.5
                if needed <= 10:
                    dur = snap_duration(needed)
                    vo_str = f"{char} (deferred — add in post) — \"{text}\""
                    prompt = f"{context_str} Action: {vis_mod} {camera_str} {framing_str} Duration: {dur}s. Audio: {audio_text}. No spoken dialogue in this clip."
                    clips_for_shot.append({
                        "suffix": "", "dur": dur, "refs": used_refs, "vo": vo_str, "prompt": prompt
                    })
                else:
                    sents = split_sentences(text)
                    mid = len(sents)//2
                    part1 = " ".join(sents[:mid])
                    part2 = " ".join(sents[mid:])
                    dur1 = snap_duration(len(part1.split())/2.5)
                    dur2 = snap_duration(len(part2.split())/2.5)
                    
                    vo_str1 = f"{char} (deferred — add in post) — \"{part1}\""
                    prompt1 = f"{context_str} Action: {vis_mod} (Part 1). {camera_str} {framing_str} Duration: {dur1}s. Audio: {audio_text}. No spoken dialogue in this clip."
                    clips_for_shot.append({
                        "suffix": "a", "dur": dur1, "refs": used_refs, "vo": vo_str1, "prompt": prompt1
                    })
                    
                    vo_str2 = f"{char} (deferred — add in post) — \"{part2}\""
                    prompt2 = f"{context_str} Action: {vis_mod} (Part 2). {camera_str} {framing_str} Duration: {dur2}s. Audio: {audio_text}. No spoken dialogue in this clip."
                    clips_for_shot.append({
                        "suffix": "b", "dur": dur2, "refs": used_refs, "vo": vo_str2, "prompt": prompt2
                    })

        for c in clips_for_shot:
            all_clips.append({
                "s_idx": s_idx, "sh_idx": sh_idx, "heading": heading,
                "suffix": c["suffix"], "dur": c["dur"], "refs": c["refs"],
                "vo": c["vo"], "prompt": c["prompt"]
            })

total_clips = len(all_clips)
total_runtime = sum(c["dur"] for c in all_clips)

pack_file.write(f"# GOOGLE FLOW VIDEO PROMPT PACK — {title}\n\n")
pack_file.write(f"**Source script:** Script1.md\n")
pack_file.write(f"**Aspect ratio:** {ar}\n")
pack_file.write(f"**Total clips:** {total_clips}  |  **Total runtime:** {total_runtime}s\n")
pack_file.write(f"**Voice-over plan:** {vo_plan}\n")
pack_file.write(f"**Unresolved assets (no reference image, described inline):** {unresolved_str}\n\n")
pack_file.write("---\n\n")

current_scene = -1
for c in all_clips:
    if c["s_idx"] != current_scene:
        current_scene = c["s_idx"]
        pack_file.write(f"## Scene {current_scene+1}: {c['heading']}\n\n")
    
    shot_title = f"Shot {c['sh_idx']+1:02d}"
    pack_file.write(f"### Clip {current_scene+1}.{c['sh_idx']+1}{c['suffix']} — {shot_title}\n")
    pack_file.write(f"**Duration:** {c['dur']}s\n")
    pack_file.write(f"**Aspect ratio:** {ar}\n")
    pack_file.write(f"**References:** {c['refs']}\n")
    pack_file.write(f"**Dialogue / Voice-over:** {c['vo']}\n\n")
    pack_file.write(f"**Prompt:**\n{c['prompt']}\n\n")
    pack_file.write("---\n\n")
    
    clip_filename = f"Scene{current_scene+1:02d}_Shot{c['sh_idx']+1:02d}{c['suffix']}.txt"
    with open(rf'f:\ScriptParser\Script1\VideoPrompts\clips\{clip_filename}', 'w', encoding='utf-8') as cf:
        cf.write(c['prompt'])

pack_file.close()
