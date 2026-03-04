import os
import cv2
import pandas as pd
import subprocess
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import platform


def _get_screen_size():
    """Return (width, height) of primary display."""
    try:
        if platform.system() == "Windows":
            import ctypes
            # Make sure DPI scaling doesn’t mess up values
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass
            user32 = ctypes.windll.user32
            return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
        else:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            w = root.winfo_screenwidth()
            h = root.winfo_screenheight()
            root.destroy()
            return int(w), int(h)
    except Exception:
        return 1920, 1080
    
def select_rois_and_save_csv(video_dir, output_csv):
    data = []
    print("INSTRUCTIONS:\n"
          " - Draw each ROI and press ENTER or SPACE.\n"
          " - Press ESC when done with current video to continue to the next.\n"
          " - You can select 3, 6, or any number of ROIs.\n")

    scr_w, scr_h = _get_screen_size()
    # Keep a small margin so window chrome/taskbar don’t clip the UI
    max_w = int(scr_w * 0.9)
    max_h = int(scr_h * 0.9)

    for root, _, files in os.walk(video_dir):
        for file in sorted(files):
            if not file.lower().endswith(".avi"):
                continue

            video_path = os.path.join(root, file)
            cap = cv2.VideoCapture(video_path)
            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                print(f"Failed to read {video_path}")
                continue

            h, w = frame.shape[:2]
            # Compute scale to fit frame within (max_w, max_h)
            scale = min(max_w / w, max_h / h, 1.0)
            disp_w, disp_h = int(w * scale), int(h * scale)
            frame_disp = frame if scale == 1.0 else cv2.resize(frame, (disp_w, disp_h), interpolation=cv2.INTER_AREA)

            # Create a resizable window (helps if you want to tweak size manually)
            win = "Select ROIs"
            cv2.namedWindow(win, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(win, disp_w, disp_h)

            print(f"\nSelect ROIs for: {video_path} (shown at {int(scale*100)}% of original)")
            rois_scaled = cv2.selectROIs(win, frame_disp, fromCenter=False, showCrosshair=True)
            cv2.destroyAllWindows()

            if rois_scaled is None or len(rois_scaled) == 0:
                print(f"No ROIs selected for {file}. Skipping.")
                continue

            # Map back to original coordinates
            for i, (x, y, rw, rh) in enumerate(rois_scaled):
                x0 = int(round(x / scale))
                y0 = int(round(y / scale))
                w0 = int(round(rw / scale))
                h0 = int(round(rh / scale))

                # Clamp to image bounds (just in case rounding pushes over edges)
                x0 = max(0, min(x0, w - 1))
                y0 = max(0, min(y0, h - 1))
                w0 = max(1, min(w0, w - x0))
                h0 = max(1, min(h0, h - y0))

                data.append({
                    "folder": os.path.basename(root),
                    "video": file,
                    "dish_id": f"dish{i+1}",
                    "x": x0, "y": y0, "w": w0, "h": h0
                })

    if data:
        df = pd.DataFrame(data)
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        df.to_csv(output_csv, index=False)
        print(f"\nROI data saved to: {output_csv}")
    else:
        print("\nNo ROIs were selected. CSV not saved.")


# ------------------------ STEP 2: GPU-Accelerated Conversion ------------------------
def convert_avi_to_mp4_ffmpeg(input_path, output_path):
    if os.path.exists(output_path):
        print(f"Already converted: {output_path}")
        return

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        "ffmpeg", "-y", "-i", input_path,   # removed problematic CUDA flag
        "-c:v", "libx264", "-preset", "fast",
        "-crf", "23",  # quality/size trade-off
        output_path
    ]
    print(f"Converting {input_path} → {output_path}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if not os.path.exists(output_path):
        print(f"FFmpeg failed to create output. Error:\n{result.stderr}")
        raise RuntimeError("Conversion failed for: " + input_path)
    else:
        print(f"Converted: {output_path}")



# ------------------------ STEP 3: Parallel Cropping ------------------------
def crop_single_dish_video(video_path, fps, dish_info, base_name, output_dir):
    x, y, w, h = map(int, [dish_info['x'], dish_info['y'], dish_info['w'], dish_info['h']])
    dish_id = dish_info['dish_id']
    output_path = os.path.join(output_dir, f"{dish_id}_{base_name}.mp4")
    cap = cv2.VideoCapture(video_path)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    pbar = tqdm(total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), desc=f"{dish_id}_{base_name}", leave=False)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cropped = frame[y:y+h, x:x+w]
        out.write(cropped)
        pbar.update(1)
    cap.release()
    out.release()
    pbar.close()


def crop_dishes_parallel(video_path, roi_rows, output_dir):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    tasks = [(video_path, fps, row, base_name, output_dir) for _, row in roi_rows.iterrows()]
    with Pool(min(len(tasks), cpu_count())) as pool:
        pool.starmap(crop_single_dish_video, tasks)

# ------------------------ FULL PIPELINE ------------------------
def run_full_pipeline(video_folder, roi_csv="dish_rois.csv", formatted_dir=None):
    if formatted_dir is None:
        formatted_dir = os.path.join(video_folder, "formatted")
    os.makedirs(formatted_dir, exist_ok=True)

    df = pd.read_csv(roi_csv)
    grouped = df.groupby("video")  # No folder column needed

    for video, roi_rows in grouped:
        avi_path = os.path.join(video_folder, video)
        base_name = os.path.splitext(video)[0]
        mp4_path = os.path.join(formatted_dir, base_name + ".mp4")

        if not os.path.exists(avi_path):
            print(f"Skipping missing file: {avi_path}")
            continue
 
        convert_avi_to_mp4_ffmpeg(avi_path, mp4_path)
        crop_dishes_parallel(mp4_path, roi_rows, formatted_dir)

    print("Done: All videos converted and cropped.")
  



# ------------------------ MAIN ENTRY ------------------------
if __name__ == "__main__":
    # STEP 0: Set path to .avi videos (grouped in subfolders)
    
    
    video_root = "\\\\nasdcsr.unil.ch\\RECHERCHE\\FAC\\FBM\\CIG\\jlarsch\\default\\D2c\\Deeksha\\Aggression_assay\\AA_200mm_150mm_AB_TL_30dpf_starvation_20251127\\raw_data"
    roi_csv_path = "\\\\nasdcsr.unil.ch\\RECHERCHE\\FAC\\FBM\\CIG\\jlarsch\\default\\D2c\\Deeksha\\Aggression_assay\\AA_200mm_150mm_AB_TL_30dpf_starvation_20251127\\dish_rois.csv"

    # STEP 1: Run ROI selection manually once (then comment it out)
    # select_rois_and_save_csv(video_root, roi_csv_path)

    # # # # STEP 2–3: Convert & crop everything
    run_full_pipeline(video_root, roi_csv_path)
  