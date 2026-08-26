#!/usr/bin/env python3
"""
process_pipeline.py — Unified End-to-End Orchestrator for Google Storyboard to Google Flow Prompts.

Executes all 6 pipeline stages in a single automated run:
  1. .NET Asset & Screenplay Extraction (`dotnet run -- <script_name>`)
  2. Script Data Parsing (`parse_script.py`)
  3. Asset & Nametag Scanning (`scan_nametags.py`)
  4. Character Voice Profiles & Emotive Directives Generation (`VoiceProfiles.md`)
  5. Flow Video Prompt Pack & Clip Generation (`generate_pack.py`)
  6. Automated Quality & Specification Validation (`validate_pack.py`)

Usage:
    python process_pipeline.py [script_name] [--ar 16:9] [--skip-extract] [--all]

Examples:
    python process_pipeline.py WHAT_THE_LIMIT_WAS_FOR
    python process_pipeline.py MAN_WHO_BROKE_TOMORROW --ar 9:16
    python process_pipeline.py --all
"""

import sys
import os
import subprocess
import argparse
import time
from pathlib import Path

# Paths relative to workspace root
WORKSPACE_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = WORKSPACE_ROOT / "Scripts"
EXPORTS_DIR = WORKSPACE_ROOT / "Exports"
SKILL_SCRIPTS_DIR = WORKSPACE_ROOT / ".agents" / "skills" / "flow-clip-prompt-generator" / "scripts"

# Add skill scripts directory to sys.path for direct imports if needed
if str(SKILL_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS_DIR))


def log_header(title):
    width = 75
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def log_step(step_num, total_steps, title):
    print(f"\n[Step {step_num}/{total_steps}] ==> {title}")


def list_available_scripts():
    if not SCRIPTS_DIR.exists():
        return []
    return [p.stem for p in SCRIPTS_DIR.glob("*.json")]


def run_dotnet_extract(script_name):
    """Step 1: Run .NET CLI extractor."""
    print(f"Executing: dotnet run -- \"{script_name}\"")
    cmd = ["dotnet", "run", "--", script_name]
    res = subprocess.run(cmd, cwd=str(WORKSPACE_ROOT), capture_output=True, text=True, encoding="utf-8")
    
    if res.returncode != 0:
        print("[ERROR] .NET extraction failed:")
        print(res.stdout)
        print(res.stderr)
        raise RuntimeError(f".NET extraction failed with exit code {res.returncode}")
    
    print(res.stdout.strip())
    print("[SUCCESS] .NET extraction completed successfully.")


def run_parse_script(script_name):
    """Step 2: Parse script markdown into _script_data.json."""
    from parse_script import main as parse_main
    
    md_path = EXPORTS_DIR / script_name / "Markdowns" / f"{script_name}.md"
    out_json = EXPORTS_DIR / script_name / "VideoPrompts" / "_script_data.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")
    
    print(f"Parsing script: {md_path} -> {out_json}")
    old_argv = sys.argv
    try:
        sys.argv = ["parse_script.py", str(md_path), str(out_json)]
        parse_main()
    finally:
        sys.argv = old_argv
    print("[SUCCESS] Script data parsed successfully.")


def run_scan_nametags(script_name):
    """Step 3: Scan images folder and map asset nametags."""
    from scan_nametags import main as scan_main
    
    script_data = EXPORTS_DIR / script_name / "VideoPrompts" / "_script_data.json"
    images_dir = EXPORTS_DIR / script_name / "Images"
    out_map = EXPORTS_DIR / script_name / "VideoPrompts" / "_nametag_map.json"
    
    print(f"Scanning nametags: {images_dir} -> {out_map}")
    old_argv = sys.argv
    try:
        sys.argv = ["scan_nametags.py", str(script_data), str(images_dir), str(out_map)]
        scan_main()
    finally:
        sys.argv = old_argv
    print("[SUCCESS] Nametags mapped successfully.")


def run_generate_voice_profiles(script_name):
    """Step 4: Generate VoiceProfiles.md."""
    from generate_voice_profiles import generate_voice_profiles
    
    script_export_dir = EXPORTS_DIR / script_name
    print(f"Generating voice profiles for: {script_export_dir}")
    voice_profiles_path = generate_voice_profiles(str(script_export_dir))
    print(f"[SUCCESS] Voice profiles generated at: {voice_profiles_path}")


def run_generate_pack(script_name, aspect_ratio="16:9"):
    """Step 5: Generate master prompt pack and clips."""
    from generate_pack import generate_prompt_pack
    
    script_export_dir = EXPORTS_DIR / script_name
    print(f"Generating prompt pack (Aspect ratio: {aspect_ratio})...")
    master_path, clips_dir, total_clips, total_seconds = generate_prompt_pack(str(script_export_dir), aspect_ratio=aspect_ratio)
    print(f"[SUCCESS] Generated {total_clips} clips ({total_seconds}s total runtime).")
    print(f"  - Master Pack: {master_path}")
    print(f"  - Clips Directory: {clips_dir}")
    return master_path, clips_dir, total_clips, total_seconds


def run_validate_pack(script_name):
    """Step 6: Validate prompt pack."""
    from validate_pack import validate_pack
    
    pack_md = EXPORTS_DIR / script_name / "VideoPrompts" / f"{script_name}-flow-prompts.md"
    nametag_map = EXPORTS_DIR / script_name / "VideoPrompts" / "_nametag_map.json"
    
    print(f"Validating prompt pack: {pack_md}")
    with open(pack_md, "r", encoding="utf-8") as f:
        pack_text = f.read()
    
    import json
    with open(nametag_map, "r", encoding="utf-8") as f:
        nametags = json.load(f)
    
    errors = validate_pack(pack_text, nametags)
    if errors:
        print(f"[FAIL] {len(errors)} validation error(s) found:")
        for err in errors:
            print(f"  - {err}")
        raise ValueError(f"Prompt pack validation failed with {len(errors)} error(s).")
    
    print("[PASS] Pack validation passed with 0 errors!")


def process_single_script(script_name, aspect_ratio="16:9", skip_extract=False):
    """Process a single script through the entire pipeline."""
    start_time = time.time()
    log_header(f"PROCESSING PIPELINE: {script_name}")
    
    total_steps = 5 if skip_extract else 6
    current_step = 1
    
    # Step 1: Extraction
    if not skip_extract:
        log_step(current_step, total_steps, "Extracting Assets & Screenplay (.NET)")
        run_dotnet_extract(script_name)
        current_step += 1
    else:
        print("\n[INFO] Skipping .NET extraction (--skip-extract set).")
    
    # Step 2: Parse
    log_step(current_step, total_steps, "Parsing Script Data")
    run_parse_script(script_name)
    current_step += 1
    
    # Step 3: Scan Nametags
    log_step(current_step, total_steps, "Scanning Images & Mapping Nametags")
    run_scan_nametags(script_name)
    current_step += 1
    
    # Step 4: Voice Profiles
    log_step(current_step, total_steps, "Generating Voice Profiles & Emotive Directives")
    run_generate_voice_profiles(script_name)
    current_step += 1
    
    # Step 5: Video Prompts Pack
    log_step(current_step, total_steps, "Generating Google Flow Prompt Pack & Clips")
    master_path, clips_dir, total_clips, total_seconds = run_generate_pack(script_name, aspect_ratio=aspect_ratio)
    current_step += 1
    
    # Step 6: Validate
    log_step(current_step, total_steps, "Validating Prompt Pack Compliance")
    run_validate_pack(script_name)
    
    elapsed = time.time() - start_time
    
    log_header(f"COMPLETED: {script_name} in {elapsed:.2f}s")
    print(f"  • Total Clips:    {total_clips}")
    print(f"  • Total Runtime:  {total_seconds}s (~{total_seconds//60}m {total_seconds%60}s)")
    print(f"  • Master Pack:    {master_path}")
    print(f"  • Clips Folder:   {clips_dir}")
    print(f"  • Voice Profiles: {EXPORTS_DIR / script_name / 'VoiceProfiles.md'}")
    print(f"  • Screenplay:     {EXPORTS_DIR / script_name / 'Markdowns' / f'{script_name}.md'}")
    print("=" * 75 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Unified End-to-End Orchestrator for Google Storyboard to Google Flow Prompt Packs."
    )
    parser.add_argument(
        "script_name",
        nargs="?",
        default=None,
        help="Name of the script (e.g. WHAT_THE_LIMIT_WAS_FOR or MAN_WHO_BROKE_TOMORROW)"
    )
    parser.add_argument(
        "--ar", "--aspect-ratio",
        dest="aspect_ratio",
        default="16:9",
        choices=["16:9", "9:16", "1:1", "4:3", "21:9"],
        help="Target video aspect ratio (default: 16:9)"
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip the .NET extraction step if Markdown and Images already exist."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all scripts found in the Scripts/ directory."
    )
    
    args = parser.parse_args()
    
    available_scripts = list_available_scripts()
    
    if args.all:
        if not available_scripts:
            print("[ERROR] No .json scripts found in Scripts/ directory.")
            sys.exit(1)
        print(f"Found {len(available_scripts)} scripts to process: {', '.join(available_scripts)}")
        for name in available_scripts:
            process_single_script(name, aspect_ratio=args.aspect_ratio, skip_extract=args.skip_extract)
        return

    script_name = args.script_name
    if not script_name:
        if not available_scripts:
            print("[ERROR] No scripts found in Scripts/ directory.")
            sys.exit(1)
        print("Available scripts in Scripts/:")
        for i, s in enumerate(available_scripts, 1):
            print(f"  {i}. {s}")
        try:
            choice = input(f"\nSelect a script (1-{len(available_scripts)}) [default: 1]: ").strip()
            idx = int(choice) - 1 if choice else 0
            if 0 <= idx < len(available_scripts):
                script_name = available_scripts[idx]
            else:
                print("[ERROR] Invalid selection.")
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(1)

    # Clean up filename if path was passed
    script_name = Path(script_name).stem

    json_path = SCRIPTS_DIR / f"{script_name}.json"
    if not json_path.exists() and not (EXPORTS_DIR / script_name).exists():
        print(f"[ERROR] Script file not found: {json_path}")
        sys.exit(1)

    process_single_script(script_name, aspect_ratio=args.aspect_ratio, skip_extract=args.skip_extract)


if __name__ == "__main__":
    main()
