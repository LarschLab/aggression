from pathlib import Path
import re

# --- USER SETTINGS ---
BASE_DIR = Path(r"\\\\nasdcsr.unil.ch\\RECHERCHE\\FAC\\FBM\\CIG\\jlarsch\\default\\D2c\\Deeksha\\Aggression_assay\\AA_200mm_150mm_AB_30dpf_starvation_20251108\\raw_data\\formatted")
NEW_BASE = Path(r"D:\\Deeksha\\idtracker_toml")
RECURSIVE = True   # set False if you only want top-level files
BACKUP = True      # saves a .bak before modifying

# ----------------------------------------------------------
# Regex to capture: video_paths = ["something"]
VIDEO_RE = re.compile(r'^(video_paths\s*=\s*\[)([^\]]*)(\])', re.MULTILINE)

toml_files = sorted(BASE_DIR.rglob("*.toml") if RECURSIVE else BASE_DIR.glob("*.toml"))

if not toml_files:
    print(f"No TOML files found in {BASE_DIR}")
else:
    for toml in toml_files:
        text = toml.read_text(encoding="utf-8")

        # Extract original file name (usually from the original path) 
        match = re.search(r'video_paths\s*=\s*\["([^"]+)"\]', text)
        if not match:
            print(f"[WARN] No video_paths found in {toml.name}, skipping.")
            continue

        old_path = Path(match.group(1))
        filename = old_path.name  # keep the original video file name
        new_path = NEW_BASE / filename

        # Escape backslashes for TOML string
        new_path_str = str(new_path).replace("\\", "\\\\")
        new_line = f'video_paths = ["{new_path_str}"]'

        new_text = VIDEO_RE.sub(new_line, text, count=1)

        if BACKUP:
            toml.with_suffix(".toml.bak").write_text(text, encoding="utf-8")

        toml.write_text(new_text, encoding="utf-8")
        print(f"✔ Updated {toml.name} → {new_path}")

print("✅ All TOML files processed.")
