from pathlib import Path
import shutil

flat_folder = Path("D:/Deeksha/idtracker_toml")  # original flat folder
session_root = Path("D:/Deeksha/idtracker_sessions")  # destination

for toml_file in flat_folder.glob("*.toml"):
    stem = toml_file.stem  # e.g., dish1_out_id0_60fps_20250516113903_20250516
    video_file = toml_file.with_suffix(".mp4")
    if not video_file.exists():
        print(f"Video not found for {stem}")
        continue

    target_dir = session_root / stem
    target_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(toml_file, target_dir / toml_file.name)
    shutil.copy2(video_file, target_dir / video_file.name)

print("All sessions organized into subfolders.")
 