import json

with open(r'f:\ScriptParser\Script1\VideoPrompts\_script_data.json', encoding='utf-8') as f:
    d = json.load(f)

scenes = d.get('scenes', [])
beats = d.get('full_story_beats', [])

# Align scenes and beats
beat_idx = 0
scene_idx = 0
alignments = [] # List of tuples: (scene, [dialogue_lines_for_this_scene])

while beat_idx < len(beats) and scene_idx < len(scenes):
    b = beats[beat_idx]
    s = scenes[scene_idx]
    
    b_head = b.get('heading', '').strip().lower()
    s_head = s.get('heading', '').strip().lower()
    
    if b_head == s_head:
        if b.get('dialogue'):
            alignments.append((scene_idx, b.get('dialogue')))
        scene_idx += 1
        beat_idx += 1
    else:
        # Try to advance beat if it doesn't match? Or advance scene?
        # Usually one might have extra beats. The prompt says "walk them in order together".
        # Let's assume there's exactly the same number, or we just try to find the next beat with the same heading.
        found = False
        for i in range(beat_idx, len(beats)):
            if beats[i].get('heading', '').strip().lower() == s_head:
                beat_idx = i
                found = True
                break
        if found:
            b = beats[beat_idx]
            if b.get('dialogue'):
                alignments.append((scene_idx, b.get('dialogue')))
            scene_idx += 1
            beat_idx += 1
        else:
            scene_idx += 1

with open(r'f:\ScriptParser\Script1\VideoPrompts\alignment_out.txt', 'w', encoding='utf-8') as out:
    for scene_idx, diag_list in alignments:
        s = scenes[scene_idx]
        out.write(f"Scene {scene_idx+1}: {s.get('heading')}\n")
        
        # Default strategy: just put lines in the first shot, or try to match.
        # For now, just print what we need to assign so I can do it.
        for line in diag_list:
            char = line.get('character')
            text = line.get('text')
            out.write(f"  Line: {char}: '{text}'\n")
        out.write("\n")
