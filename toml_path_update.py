from pathlib import Path
import re

base_dir = Path("D:\Deeksha\idtracker_toml_20251108")

tomls = list(base_dir.glob("*.toml"))

if not tomls:
    print("[INFO] No TOML files found.")
    raise SystemExit

for toml_file in tomls:

    # --- derive matching video ---
    stem = toml_file.stem
    video_candidates = list(base_dir.glob(stem + "*.mp4"))

    if not video_candidates:
        print(f"[SKIP] No video found for {toml_file.name}")
        continue

    video = video_candidates[0]
    full_new_path = str(video.resolve()).replace("\\", "/")
 
    lines = toml_file.read_text(encoding="utf-8").splitlines()
    updated_lines = []
    replaced = False

    for line in lines:
        if line.strip().startswith("video_paths"):
            updated_lines.append(f'video_paths = ["{full_new_path}"]')
            replaced = True
        elif re.match(r'^\s*["\'].*\.mp4["\']\s*[,]?$', line):
            continue
        else:
            updated_lines.append(line)

    if not replaced:
        updated_lines.insert(0, f'video_paths = ["{full_new_path}"]')

    toml_file.write_text("\n".join(updated_lines), encoding="utf-8")
    print(f"[FIXED] {toml_file.name} → {video.name}")

print("[DONE]")
