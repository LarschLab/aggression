from pathlib import Path
import subprocess, sys, shutil, datetime

BASE_DIR = Path("D:\Deeksha\idtracker_toml_20251108")
TIMEOUT_SECS = 6 * 3600

if not BASE_DIR.exists():
    raise SystemExit(f"[ERROR] Base dir not found: {BASE_DIR}")

# Find TOMLs (flat or nested)
toml_files = sorted(BASE_DIR.rglob("*.toml"))

# --- Resolve the idtrackerai CLI executable (Windows-friendly) ---
py_dir = Path(sys.executable).parent
candidates = [
    py_dir / "idtrackerai.exe",   # typical on Windows
    py_dir / "idtrackerai",       # just in case
    shutil.which("idtrackerai"),  # if PATH is set
]
idtracker = next((Path(c) if isinstance(c, str) else c for c in candidates if c and Path(c).exists()), None)
if not idtracker:
    raise SystemExit("[ERROR] Couldn't find the 'idtrackerai' CLI in this environment. "
                     "Activate idtrackerai conda env and ensure it's installed (pip/conda).")

# Check whether '--output' is supported by this CLI
help_out = subprocess.run([str(idtracker), "--help"], capture_output=True, text=True)
supports_output = "--output" in (help_out.stdout or "") + (help_out.stderr or "")

summary_log = BASE_DIR / "tracking_summary.log"
with summary_log.open("w", encoding="utf-8") as summary:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not toml_files:
        msg = f"[{ts}] No TOML files found under {BASE_DIR}"
        print(msg); summary.write(msg + "\n"); raise SystemExit(0)

    summary.write(f"[{ts}] Found {len(toml_files)} TOML files\n")

    for toml in toml_files:
        folder = toml.parent
        stem = toml.stem

        # Desired output directory named after the TOML
        out_dir = folder / stem
        i = 1
        while out_dir.exists():
            out_dir = folder / f"{stem}_run{i}"
            i += 1
        out_dir.mkdir(parents=True, exist_ok=False)

        print(f"[RUN] {folder.name} -> {toml.name}  =>  {out_dir.name}")
        summary.write(f"[RUN] {folder} -> {toml.name} => {out_dir}\n")

        # Build command: run in the TOML's folder (so relative video_paths work)
        cmd = [str(idtracker), "--load", str(toml), "--track"]
        if supports_output:
            cmd += ["--output", str(out_dir)]

        try:
            result = subprocess.run(
                cmd,
                cwd=folder,                  # keep CWD where the TOML/video live
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECS,
            )
        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] {out_dir.name}")
            summary.write(f"[TIMEOUT] {out_dir}\n")
            continue

        # Save logs in the out_dir no matter what
        (out_dir / "stdout.txt").write_text(result.stdout or "", encoding="utf-8")
        (out_dir / "stderr.txt").write_text(result.stderr or "", encoding="utf-8")

        if result.returncode == 0:
            print(f"[OK]   {out_dir.name}")
            summary.write(f"[OK]   {out_dir}\n")
        else: 
            tail = "\n".join((result.stderr or "").splitlines()[-20:])
            print(f"[ERR]  {out_dir.name} (exit {result.returncode})\n--- stderr tail ---\n{tail}\n-------------------")
            summary.write(f"[ERR]  {out_dir} (exit {result.returncode})\n")
