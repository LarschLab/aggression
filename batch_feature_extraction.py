import os
import pandas as pd
import numpy as np


# ============================================================
# === CORE TEMPORAL FEATURE FUNCTIONS (unchanged) ============
# ============================================================

def precompute_regression_terms(window):
    t = np.arange(window)
    t_mean = t.mean()
    denom = np.sum((t - t_mean)**2)
    return t, t_mean, denom


def slope(x, t, t_mean, denom):
    return np.sum((t - t_mean) * (x - x.mean())) / denom


def extract_temporal_stats(win, feature_names, t, t_mean, denom):
    out = {}

    for i, col_name in enumerate(feature_names):
        x = win[:, i]

        if np.isnan(x).any():
            out[f"{col_name}_slope"] = np.nan
            out[f"{col_name}_delta"] = np.nan
            out[f"{col_name}_mean"] = np.nan
            out[f"{col_name}_std"] = np.nan
            out[f"{col_name}_max"] = np.nan
            out[f"{col_name}_min"] = np.nan
            continue

        out[f"{col_name}_slope"] = slope(x, t, t_mean, denom)
        out[f"{col_name}_delta"] = x[-1] - x[0]
        out[f"{col_name}_mean"] = x.mean()
        out[f"{col_name}_std"] = x.std()
        out[f"{col_name}_max"] = x.max()
        out[f"{col_name}_min"] = x.min()

    return out


# ============================================================
# === SINGLE-FILE TEMPORAL FEATURE GENERATOR  =====
# ============================================================

def generate_temporal_features_from_csv(
    csv_path,
    feature_columns,
    frame_column="frame",
    window_size=40,
):

    df = pd.read_csv(csv_path)
    df = df.dropna(subset=feature_columns + [frame_column])

    data = df[feature_columns].to_numpy()
    frames = df[frame_column].to_numpy()

    t, t_mean, denom = precompute_regression_terms(window_size)

    results = []
    n = len(df)

    for i in range(window_size - 1, n):
        win = data[i - window_size + 1 : i + 1]

        if np.isnan(win).any():
            continue

        feats = extract_temporal_stats(win, feature_columns, t, t_mean, denom)
        feats["frame"] = frames[i]

        results.append(feats)

    return pd.DataFrame(results)


# ============================================================
# === BATCH PROCESSING =======================================
# ============================================================

input_folder = "D:\\Deeksha\\features_csv"
output_folder = "D:\\Deeksha\\temporal_features"
os.makedirs(output_folder, exist_ok=True)

# same feature list you used
feature_columns = [
    'x1', 'y1',
    'x2', 'y2',
    'inter_animal_distance',
    'speed1', 'speed2',
    'acc1', 'acc2',
    'heading1', 'heading2',
    'relative_heading_1tow2',
    'relative_heading_2tow1'
]

# choose which files to process 
all_files = [f for f in os.listdir(input_folder) if f.endswith("features_with_labels.csv")]

print(f"Found {len(all_files)} files to process.\n")

for filename in all_files:
    print(f"Processing {filename}...") 

    try:
        csv_path = os.path.join(input_folder, filename)

        tf_df = generate_temporal_features_from_csv(
            csv_path=csv_path,
            feature_columns=feature_columns,
            frame_column="frame",
            window_size=40
        )

        save_name = filename.replace("features.csv", "temporal_features.csv")
        save_path = os.path.join(output_folder, save_name)

        tf_df.to_csv(save_path, index=False)
        print(f"  ✔ Saved {len(tf_df)} rows → {save_path}")

    except Exception as e:
        print(f"  ✘ Error processing {filename}: {e}")
