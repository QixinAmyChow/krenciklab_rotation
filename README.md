# krenciklab_rotation

GCaMP calcium imaging analysis pipeline for astrocyte Ca²⁺ event detection. Runs NoRMCorre drift correction → AQuA2 event detection → aqua2kit quantification as independent SLURM jobs.

---

## Pipeline overview

```
data/tiff/<exp>/          raw TIFFs
       │
       ▼  run_normcorre.sh
data/tiff/<exp>_mc/       motion-corrected TIFFs
       │
       ▼  run_aqua2.sh
data/results/<exp>/       per-recording results (AVI, label map, CSVs, .mat)
       │
       ▼  run_quantify.sh
data/results/<exp>_summary.xlsx
```

---

## Usage

**Run all stages** (submits three chained SLURM jobs):
```bash
bash run_pipeline.sh config_3.11.26.sh
```

**Run a single stage** (e.g. to resubmit after a failure):
```bash
sbatch run_normcorre.sh config_3.11.26.sh
sbatch run_aqua2.sh     config_3.11.26.sh
sbatch run_quantify.sh  config_3.11.26.sh
```

**Add a new experiment** — copy and edit a config file:
```bash
cp config_3.11.26.sh config_<new_exp>.sh
# edit the 7 variables inside, then:
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
| `LIF` | Leica `.lif` source file (used to read acquisition fps) |
| `SAMPLES` | Path for the auto-generated `samples_<exp>.json` |
| `SUMMARY` | Path for the final `_summary.xlsx` output |

---

## Stage details

### Stage 1 — NoRMCorre (`run_normcorre.m`)
Rigid drift correction on every TIFF in `TIFF_IN/`. Skips reference images (`green_and_red`). Writes corrected uint16 TIFFs to `TIFF_MC/`. SLURM: 6 h, 64 G.

### Stage 2 — AQuA2 (`run_aqua2.m`)
Runs AQuA2 event detection on each TIFF in `TIFF_MC/`. Reads acquisition fps from the `.lif` XML header. Per recording, writes to `RESULTS/<name>_results/`:

| Output | Description |
|---|---|
| `_AQuA2.mat` | Full AQuA2 result struct |
| `_AQuA2_Movie.avi` | Colored event overlay with burned-in timestamp |
| `_label_map.tif` | uint16 spatial map — pixel value = event index; open in Fiji with glasbey LUT → Analyze Particles to show labels |
| `_Ch1.csv`, curves, regions, risingMaps | Feature tables |

SLURM: 12 h, 64 G.

### Stage 3 — Quantify (`run_quantify.sh`)
Scans `RESULTS/` for completed `*_results/` folders, auto-assigns condition labels from filenames (`atp` → ATP, `stopped` → stopped, otherwise spontaneous), writes `samples_<exp>.json`, and runs `aqua2kit quantify` to produce the summary spreadsheet. SLURM: 1 h, 8 G.

---

## Python package — `aqua2kit`

Install once:
```bash
pip install -e .
```

| Module | Role |
|---|---|
| `cli.py` | `aqua2kit quantify <samples.json>` CLI entry point |
| `aqua2_io.py` | Loads AQuA2 `.mat` result files |
| `quantify.py` | Aggregates event counts and features across recordings |
| `lif_io.py` | Reads Leica LIF metadata |
| `plot.py` | Figure helpers |

---

## Data layout

```
data/
├── *.lif                          Leica source files (fps metadata lives here)
├── tiff/
│   ├── <exp>/                     Raw exported TIFFs
│   └── <exp>_mc/                  NoRMCorre-corrected TIFFs
└── results/
    ├── <exp>/
    │   └── <name>_results/        Per-recording AQuA2 outputs
    └── <exp>_summary.xlsx         Final summary
```

## Experiments

| Config | Description |
|---|---|
| `config_3.11.26.sh` | d14 162D-9A GCaMP8s, 20× — spontaneous, ATP, stopped-responding |
| `config_4.26.26.sh` | d14 post-FACS monolayer, ATP stimulation, 6 reps |
