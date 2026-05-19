# krenciklab_rotation

GCaMP calcium imaging analysis pipeline for astrocyte Ca²⁺ event detection. Runs NoRMCorre drift correction → AQuA2 event detection → AVI overlay generation + aqua2kit quantification as independent SLURM jobs.

---

## Pipeline overview

```
data/tiff/<exp>/          raw TIFFs
       │
       ▼  run_normcorre.sh       (Stage 1 — MATLAB)
data/tiff/<exp>_mc/       motion-corrected TIFFs
       │
       ▼  run_aqua2.sh           (Stage 2 — MATLAB)
data/results/<exp>/       per-recording: .mat, CSVs, label map
       │
       ├──▶  run_make_avi.sh     (Stage 3 — MATLAB, parallel with Stage 4)
       │     per-recording AVI with colored event overlay + timestamp
       │
       └──▶  run_quantify.sh     (Stage 4 — Python, parallel with Stage 3)
             data/results/<exp>_summary.xlsx
```

Stages 3 and 4 both depend on Stage 2 and run in parallel.

---

## Usage

**Run all stages** (submits four chained SLURM jobs):
```bash
bash run_pipeline.sh config_3.11.26.sh
```

**Run a single stage** (e.g. to resubmit after a failure):
```bash
sbatch run_normcorre.sh  config_3.11.26.sh
sbatch run_aqua2.sh      config_3.11.26.sh
sbatch run_make_avi.sh   config_3.11.26.sh
sbatch run_quantify.sh   config_3.11.26.sh
```

**Regenerate AVIs only** (from existing `.mat` files):
```bash
sbatch run_make_avi.sh config_3.11.26.sh
```

**Add a new experiment** — copy and edit a config file:
```bash
cp config_3.11.26.sh config_<new_exp>.sh
# edit the variables inside, then:
bash run_pipeline.sh config_<new_exp>.sh
```

---

## Config files

Each experiment has one config file that defines all paths. Nothing else needs to change.

| Variable | Description |
|---|---|
| `ROOT` | Absolute path to this repo |
| `EXP` | Experiment identifier (used in dir names) |
| `TIFF_IN` | Raw TIFF input directory |
| `TIFF_MC` | Motion-corrected TIFF output directory |
| `RESULTS` | AQuA2 results directory |
| `LIF` | Leica `.lif` source file (used by Stage 3 to read acquisition fps) |
| `SAMPLES` | Path for the auto-generated `samples_<exp>.json` |
| `SUMMARY` | Path for the final `_summary.xlsx` output |

---

## Stage details

### Stage 1 — NoRMCorre (`src/run_normcorre.m`)
Rigid drift correction on every TIFF in `TIFF_IN/`. Skips reference images (`green_and_red`). Writes corrected uint16 TIFFs to `TIFF_MC/`. SLURM: 6 h, 64 G.

### Stage 2 — AQuA2 (`src/run_aqua2.m`)
Runs AQuA2 event detection on each TIFF in `TIFF_MC/`. Per recording, writes to `RESULTS/<name>_results/`:

| Output | Description |
|---|---|
| `_AQuA2.mat` | Full AQuA2 result struct |
| `_label_map.tif` | uint16 spatial map — pixel value = event index; open in Fiji with glasbey LUT |
| `_Ch1.csv`, curves, regions, risingMaps | Feature tables |

SLURM: 12 h, 64 G.

### Stage 3 — AVI overlay (`src/make_avi.m`)
Loads each `_AQuA2.mat`, builds a colored per-event overlay using AQuA2's `plt.regionMapWithData`, and writes a Motion JPEG AVI with a burned-in timestamp. Frame rate is read from the `.lif` file by Python (`aqua2kit.lif_io.read_fps`) and passed to MATLAB. SLURM: 4 h, 32 G.

### Stage 4 — Quantify (`run_quantify.sh`)
Scans `RESULTS/` for completed `*_results/` folders, auto-assigns condition labels from filenames (`atp` → ATP, `stopped` → stopped, otherwise spontaneous), writes `samples_<exp>.json`, and runs `aqua2kit quantify` to produce the summary spreadsheet. SLURM: 1 h, 8 G.

---

## Source layout

```
src/
├── run_normcorre.m    Stage 1 — NoRMCorre drift correction
├── run_aqua2.m        Stage 2 — AQuA2 event detection
├── make_avi.m         Stage 3 — AVI overlay generation
└── aqua2kit/          Stage 4 — Python quantification package
    ├── lif_io.py      LIF→TIFF conversion; read_fps() for frame rate
    ├── aqua2_io.py    Load AQuA2 .mat result files
    ├── quantify.py    Aggregate event counts and features
    ├── plot.py        Figure helpers
    └── cli.py         aqua2kit CLI entry point
```

Install the Python package once:
```bash
pip install -e .
```

---

## Data layout

```
data/
├── *.lif                          Leica source files (fps metadata)
├── tiff/
│   ├── <exp>/                     Raw exported TIFFs
│   └── <exp>_mc/                  NoRMCorre-corrected TIFFs
└── results/
    ├── <exp>/
    │   └── <name>_results/        Per-recording AQuA2 outputs
    └── <exp>_summary.xlsx         Final summary
```

---

## Experiments

| Config | Description |
|---|---|
| `config_3.11.26.sh` | d14 162D-9A GCaMP8s, 20× — spontaneous, ATP, stopped-responding |
| `config_4.26.26.sh` | d14 post-FACS monolayer, ATP stimulation, 6 reps |
