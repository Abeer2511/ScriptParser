#!/usr/bin/env python3
"""
scan_nametags.py — cross-reference the Images/{Character,Location,Prop,Frame}
folders against the asset names found by parse_script.py, so every prompt can
reference a real, usable Google Flow nametag (`@nametag`) instead of a guess.

Usage:
    python scan_nametags.py <script_data.json> <images_root_dir> <output.json>

<images_root_dir> is the folder that directly contains Character/ Location/
Prop/ Frame/ subfolders.

A "nametag" is the image's filename without its extension, taken literally —
this script never renames or reformats it, since that string is exactly what
the user pastes into Google Flow as `@nametag`.

Output JSON:
    {
      "matched": {asset_name: {"nametag":, "file":, "category":}},
      "ambiguous": {asset_name: [{"nametag":, "file":}, ...]},
      "unmatched_assets": [asset_name, ...],   # no image found at all
      "unmatched_images": {"Character":[...], "Location":[...], "Prop":[...]},
      "frame_files": {"Character":..., ...}    # not applicable; see frame_index
      "frame_index": [filename, ...],          # raw listing, for shot-level matching later
    }
"""
import sys
import os
import json
import re
import difflib

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def normalize(s):
    s = s.lower()
    s = s.replace("'s", "").replace("’s", "")
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def list_images(folder):
    if not os.path.isdir(folder):
        return []
    out = []
    for fn in sorted(os.listdir(folder)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() in IMG_EXTS:
            out.append((stem, fn))
    return out


def match_category(asset_names, folder):
    """Return matched, ambiguous, unmatched_assets, unmatched_images for one category folder."""
    images = list_images(folder)  # list of (stem, filename)
    norm_index = {}
    for stem, fn in images:
        norm_index.setdefault(normalize(stem), []).append((stem, fn))

    matched = {}
    ambiguous = {}
    unmatched_assets = []
    used_files = set()

    for asset in asset_names:
        na = normalize(asset)
        candidates = norm_index.get(na, [])
        if len(candidates) == 1:
            stem, fn = candidates[0]
            matched[asset] = {"nametag": stem, "file": fn}
            used_files.add(fn)
            continue
        if len(candidates) > 1:
            ambiguous[asset] = [{"nametag": s, "file": f} for s, f in candidates]
            continue

        # Fuzzy fallback: near-identical strings only (typo/minor-formatting
        # level). Deliberately NOT substring containment — "Patent Office"
        # is a substring of "Patent Office Sub-Basement" but they are
        # different places, and silently matching one to the other's image
        # would be worse than leaving it unmatched. Require both a high
        # similarity ratio AND comparable length.
        fuzzy_hits = []
        for stem, fn in images:
            ni = normalize(stem)
            if not ni or not na:
                continue
            length_ratio = min(len(na), len(ni)) / max(len(na), len(ni))
            similarity = difflib.SequenceMatcher(None, na, ni).ratio()
            if length_ratio >= 0.75 and similarity >= 0.92:
                fuzzy_hits.append((stem, fn))
        if len(fuzzy_hits) == 1:
            stem, fn = fuzzy_hits[0]
            matched[asset] = {"nametag": stem, "file": fn}
            used_files.add(fn)
        elif len(fuzzy_hits) > 1:
            ambiguous[asset] = [{"nametag": s, "file": f} for s, f in fuzzy_hits]
        else:
            unmatched_assets.append(asset)

    unmatched_images = [fn for stem, fn in images if fn not in used_files]
    return matched, ambiguous, unmatched_assets, unmatched_images


def main():
    if len(sys.argv) != 4:
        print("Usage: python scan_nametags.py <script_data.json> <images_root_dir> <output.json>")
        sys.exit(1)

    script_json_path, images_root, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

    with open(script_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    character_names = [c["name"] for c in data.get("characters", [])]
    location_names = data.get("locations", [])
    prop_names = data.get("props", [])

    result = {"matched": {}, "ambiguous": {}, "unmatched_assets": [], "unmatched_images": {}}

    for category, names, subfolder in [
        ("Character", character_names, "Character"),
        ("Location", location_names, "Location"),
        ("Prop", prop_names, "Prop"),
    ]:
        folder = os.path.join(images_root, subfolder)
        matched, ambiguous, unmatched_assets, unmatched_images = match_category(names, folder)
        for asset, info in matched.items():
            info["category"] = category
            result["matched"][asset] = info
        for asset, cands in ambiguous.items():
            for c in cands:
                c["category"] = category
            result["ambiguous"][asset] = cands
        result["unmatched_assets"].extend(unmatched_assets)
        result["unmatched_images"][category] = unmatched_images

    # Frame folder has no fixed name list to match against (frames key off
    # shot identity, not a declared asset). Just give a raw listing back so
    # the calling skill can correlate by shot title / scene+shot number.
    frame_folder = os.path.join(images_root, "Frame")
    frame_files = [fn for _, fn in list_images(frame_folder)]
    result["frame_index"] = frame_files

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Matched: {len(result['matched'])}  Ambiguous: {len(result['ambiguous'])}  "
          f"Unmatched assets: {len(result['unmatched_assets'])}  Frame images found: {len(frame_files)}")
    if result["ambiguous"]:
        print("\nAmbiguous (needs user's pick):")
        for a, cands in result["ambiguous"].items():
            print(f"  - {a}: " + ", ".join(c['nametag'] for c in cands))
    if result["unmatched_assets"]:
        print("\nNo image found for:")
        for a in result["unmatched_assets"]:
            print(f"  - {a}")


if __name__ == "__main__":
    main()