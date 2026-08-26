#!/usr/bin/env python3
"""
generate_pack.py — Generic Google Flow prompt pack generator.

Usage:
    python generate_pack.py <script_name_or_folder> [--ar 16:9]
"""
import sys
import os

# Delegate to the skills script or run directly
skills_script = os.path.join(".agents", "skills", "flow-clip-prompt-generator", "scripts", "generate_pack.py")
if os.path.exists(skills_script):
    import importlib.util
    spec = importlib.util.spec_from_file_location("generate_pack", skills_script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if __name__ == "__main__":
        mod.main()
