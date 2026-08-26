import json
with open(r'f:\ScriptParser\Script1\VideoPrompts\_script_data.json', encoding='utf-8') as f:
    d = json.load(f)
with open(r'f:\ScriptParser\Script1\VideoPrompts\dialogue_align.txt', 'w', encoding='utf-8') as out:
    out.write('DIALOGUE BEATS:\n')
    for b in d.get('full_story_beats', []):
        if b.get('dialogue'):
            out.write(f"Scene {b.get('scene_id')}: {b.get('speaker')} - {b.get('dialogue')}\n")
