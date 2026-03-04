import cv2
import numpy as np
import os

# ------------------------------------------------------------
# 1. TRIMMING FUNCTION (before combining)
# ------------------------------------------------------------
def trim_video(input_path, output_path, start_sec, end_sec):
    """Trim video between start_sec and end_sec and save to output_path."""
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Compute frame indices
    start_frame = int(start_sec * fps)
    end_frame = int(end_sec * fps)

    if start_frame >= total_frames:
        raise ValueError(f"Start time exceeds video length for {input_path}")

    end_frame = min(end_frame, total_frames - 1)

    # Setup writer
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    for f in range(start_frame, end_frame):
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)

    cap.release()
    out.release()
    print(f"Trimmed video saved to {output_path}")


# ------------------------------------------------------------
# 2. COMBINE FUNCTION
# ------------------------------------------------------------
def create_synthetic_session(video_left, video_right, output_path):
    cap_left = cv2.VideoCapture(video_left)
    cap_right = cv2.VideoCapture(video_right)

    # FPS
    fps_left = cap_left.get(cv2.CAP_PROP_FPS)
    fps_right = cap_right.get(cv2.CAP_PROP_FPS)

    if fps_left != fps_right:
        print(f"WARNING: FPS mismatch ({fps_left} vs {fps_right}). Using left video FPS.")
    fps = fps_left

    # Frame sizes
    w_left = int(cap_left.get(cv2.CAP_PROP_FRAME_WIDTH))
    h_left = int(cap_left.get(cv2.CAP_PROP_FRAME_HEIGHT))

    w_right = int(cap_right.get(cv2.CAP_PROP_FRAME_WIDTH))
    h_right = int(cap_right.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Resize right video to match left height
    if h_left != h_right:
        scale = h_left / h_right
        new_w_right = int(w_right * scale)
    else:
        new_w_right = w_right

    # Title bar height
    title_h = 40

    # Output video size
    out_width = w_left + new_w_right
    out_height = h_left + title_h

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (out_width, out_height))

    print("\nCreating synthetic 2-fish session...")
    print(f"Output size: {out_width} x {out_height}")

    # --------------------------------------------------------
    # Shorten titles (only keep substring starting from 'session')
    # --------------------------------------------------------
    def shorten(name):
        key = "session"
        idx = name.lower().find(key)
        return name[idx:] if idx != -1 else name

    raw_left = os.path.basename(video_left)
    raw_right = os.path.basename(video_right)

    name_left = shorten(raw_left)
    name_right = shorten(raw_right)

    # --------------------------------------------------------
    # Frame loop
    # --------------------------------------------------------
    while True:
        ret_left, frame_left = cap_left.read()
        ret_right, frame_right = cap_right.read()

        if not ret_left or not ret_right:
            break

        # Resize right frame (if needed)
        if h_left != h_right:
            frame_right = cv2.resize(frame_right, (new_w_right, h_left))

        # Concatenate videos horizontally
        combined_videos = np.hstack((frame_left, frame_right))

        # Create title bar
        title_bar = np.zeros((title_h, out_width, 3), dtype=np.uint8)

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        color = (255, 255, 255)

        # Left title
        cv2.putText(
            title_bar,
            name_left,
            (10, int(title_h * 0.7)),
            font,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA
        )

        # Right title
        cv2.putText(
            title_bar,
            name_right,
            (w_left + 10, int(title_h * 0.7)),
            font,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA
        )

        # Stack title bar on top
        full_frame = np.vstack((title_bar, combined_videos))
        out.write(full_frame)

    cap_left.release()
    cap_right.release()
    out.release()

    print(f"\nDone! Saved synthetic video to:\n{output_path}\n")


# ------------------------------------------------------------
# 3. EXAMPLE USAGE
# ------------------------------------------------------------
v1 = "D:\Deeksha\idmatcherai_trial_dish1_setup2\dish1_out_id2_60fps_20251108135030_idmatcherai_setup2_1.mp4"
v2 = "D:\Deeksha\idmatcherai_trial_dish1_setup2\dish1_out_id2_60fps_20251108140635_idmatcherai_setup2_2.mp4"

out = "D:\Deeksha\idmatcherai_trial_dish1_setup2\synthetic_combined_5min.mp4"

# --- Trim both videos to 1 minute (0–60 seconds) ---
trimmed_v1 = v1.replace(".mp4", "_trimmed1min.mp4")
trimmed_v2 = v2.replace(".mp4", "_trimmed1min.mp4")

trim_video(v1, trimmed_v1, start_sec=0, end_sec=300)
trim_video(v2, trimmed_v2, start_sec=0, end_sec=300)

# --- Combine the trimmed videos ---
create_synthetic_session(trimmed_v1, trimmed_v2, out)
 