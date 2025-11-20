#GUI for manual fight annotation frame-by-frame

import cv2
import pandas as pd
import os

# --- CONFIGURATION ---
video_path = "/Volumes/jlarsch/default/D2c/Deeksha/Territory_assay/TA_200mm_30dpf_AB_pattern_vs_nopattern/analysis/cropped_fight_1.mp4"
tracking_csv = "/Volumes/jlarsch/default/D2c/Deeksha/Territory_assay/TA_200mm_30dpf_AB_pattern_vs_nopattern/idtracker/session_cropped_fight_annotated_1/trajectories/trajectories_csv/trajectories.csv"  
output_csv = "/Volumes/jlarsch/default/D2c/Deeksha/Territory_assay/TA_200mm_30dpf_AB_pattern_vs_nopattern/analysis/labeled_fights.csv"
fps = 60  

# --- Load tracking data if available ---
tracking_df = None
if tracking_csv and os.path.exists(tracking_csv):
    tracking_df = pd.read_csv(tracking_csv)
    tracking_df["frame"] = (tracking_df["time"] * fps).round().astype(int)
    tracking_df = tracking_df.set_index("frame")

# --- Initialize OpenCV ---
cap = cv2.VideoCapture(video_path)
frame_idx = 0
labels = []

print("Instructions:")
print("  [f] = fight, [n] = no fight, [u] = undo, [q] = quit and save")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Overlay tracking if available
    if tracking_df is not None and frame_idx in tracking_df.index:
        row = tracking_df.loc[frame_idx]
        for i in [1, 2]:
            x, y = row.get(f"x{i}"), row.get(f"y{i}")
            if pd.notnull(x) and pd.notnull(y):
                color = (0, 0, 255) if i == 1 else (0, 255, 255)
                cv2.circle(frame, (int(x), int(y)), 4, color, -1)

    # Show frame number and last label
    label_text = f"Frame: {frame_idx}"
    if labels:
        label_text += f" | Last label: {labels[-1][1]}"
    cv2.putText(frame, label_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    cv2.imshow("Fight Labeling Tool", frame)
    key = cv2.waitKey(0) & 0xFF

    if key == ord('f') or key == ord('n'):
        label_value = 1 if key == ord('f') else 0
        # Remove any existing label for this frame
        labels = [(f, l) for f, l in labels if f != frame_idx]
        labels.append((frame_idx, label_value))
        frame_idx += 1

    elif key == ord('u'):
        if labels:
            frame_idx = labels.pop()[0]
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            print(f"Moved back to frame {frame_idx}")
        else:
            print("Nothing to undo.")

    elif key == ord('q'):
        print("Quitting and saving labels...")
        break
    else:
        print("Invalid key. Use [f], [n], [u], or [q].")

cap.release()
cv2.destroyAllWindows()

# --- Save labels to CSV ---
if labels:
    df = pd.DataFrame(labels, columns=["frame", "label"])
    df.to_csv(output_csv, index=False)
    print(f"Saved {len(labels)} labeled frames to {output_csv}")
else:
    print("No labels saved.")
