from pathlib import Path
import os


base_dir = Path("D:\Deeksha\idtracker_toml_20251108")
if not base_dir.exists():
    raise SystemExit(f"[ERROR] Base directory not found: {base_dir}")

print(f"[INFO] Scanning TOML files in: {base_dir}")

changed_count = 0
file_count = 0

# OPTION A: files directly in base_dir (your current layout)
toml_iter = base_dir.glob("*.toml")

# OPTION B: uncomment this line instead to search recursively
# toml_iter = base_dir.rglob("*.toml")

for toml_file in toml_iter:
    file_count += 1
    text = toml_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Pass 1: remove stray closing bracket lines on their own
    cleaned_lines = [line for line in lines if line.strip() != "]"]

    # Pass 2: ensure roi_list is closed before background_subtraction_stat
    fixed_lines = [] 
    inside_roi_list = False
    roi_closed = False

    for line in cleaned_lines:
        stripped = line.strip()

        # start of roi_list (e.g., 'roi_list = [')
        if stripped.startswith("roi_list") and stripped.endswith("["):
            inside_roi_list = True
            fixed_lines.append(line)
            continue

        # if background_subtraction_stat appears before closing the list, close it
        if inside_roi_list and "background_subtraction_stat" in stripped:
            fixed_lines.append("]")
            roi_closed = True
            inside_roi_list = False

        fixed_lines.append(line)

    # If list was opened but never closed, close it at the end
    if inside_roi_list and not roi_closed:
        fixed_lines.append("]")

    new_text = "\n".join(fixed_lines)

    if new_text != text:
        toml_file.write_text(new_text, encoding="utf-8")
        changed_count += 1
        print(f"[FIXED] {toml_file.name}")

print(f"[DONE] Examined {file_count} TOML files; changed {changed_count}.")
