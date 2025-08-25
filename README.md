# synrad-lung

Synthetic *oncology-grade* CT chest radiology reports for **lung cancer**, designed to feed your TNM extraction pipeline.

- Realistic structure: `FINDINGS` and `IMPRESSION` sections, common artifacts, comparisons, and normal-by-exception phrasing.
- TNM-aware controls: pick T/N/M distributions, lobar location, histology hints, post-treatment changes, etc.
- **Response tracking**: Generate baseline and follow-up reports with response status (SD, PD, CR, PR) following RECIST criteria.
- **Variable follow-up studies**: Each patient gets 1 baseline + 1-N follow-up studies (where N is the max you specify).
- **JSONL export**: Generate `cohort_labels.jsonl` files compatible with RECIST visualization apps.
- Emits both **free-text report** and a parallel **structured JSON** (lesion list + TNM + staging rationale) for evaluation.
- Deterministic by seed.

## Quick start

```bash
# Generate baseline cases only
pip install -e .
python -m synthrad --n 5 --stage-dist I:0.2,II:0.25,III:0.35,IV:0.2 --seed 7 --out ./out

# Generate baseline cases with follow-up reports (includes response status)
python -m synthrad --n 5 --follow-up --stage-dist I:0.2,II:0.25,III:0.35,IV:0.2 --seed 7 --out ./out

# Generate follow-up cases with custom interval (e.g., 60 days)
python -m synthrad --n 5 --follow-up --follow-up-days 60 --stage-dist I:0.2,II:0.25,III:0.35,IV:0.2 --seed 7 --out ./out

# Generate with variable follow-up studies (1-4 studies per patient)
python -m synthrad --n 5 --studies-per-patient 4 --response-dist CR:0.05,PR:0.2,SD:0.3,PD:0.45 --seed 7 --out ./out

# Generate with optimistic response distribution (more responses)
python -m synthrad --n 5 --studies-per-patient 4 --response-dist CR:0.2,PR:0.4,SD:0.3,PD:0.1 --seed 7 --out ./out

# Generate with JSONL output for React app
python -m synthrad --n 5 --studies-per-patient 4 --seed 42 --out ./out --jsonl cohort_labels.jsonl
```

This writes `*.txt` and matching `*.json` sidecars under `./out`.

## Design

- `synthrad/generator.py` – main entry (also a CLI).
- `synthrad/lexicons.py` – realistic vocab and style variants.
- `synthrad/schema.py` – JSON schema + pydantic models (optional at runtime).
- Artifacts include: **beam-hardening**, motion, suboptimal inspiration; typical benign/incidental findings are sprinkled to keep text realistic within ~1 SD of a tertiary-center staging report.
- Nodal stations use IASLC map (e.g., 2R, 4R, 7, 10L/10R). Sizes use **short-axis** for nodes; tumors use **long-axis** in **mm**.

## Output JSON (sidecar)

```json
{
  "meta": {
    "modality": "CT chest with IV contrast",
    "comparison_date": "2024-03-07",
    "prior_therapy": ["chemoradiation"]
  },
  "primary": {
    "lobe": "RUL",
    "size_mm": 34,
    "features": ["spiculation", "pleural_inv_suspected"]
  },
  "nodes": [{"station": "4R", "short_axis_mm": 12}],
  "mets": [{"site": "adrenal_right", "size_mm": 14}],
  "tnm": {"T": "T2a", "N": "N2", "M": "M1b", "stage_group": "IV"},
  "rationale": ["T2a because >30–50 mm", "N2: ipsilateral mediastinal (4R) >10 mm", "M1b: single extrathoracic metastasis"]
}
```

## Response Status Definitions

- **CR (Complete Response)**: Complete disappearance of all target lesions
- **PR (Partial Response)**: ≥30% decrease in sum of diameters of target lesions
- **SD (Stable Disease)**: Neither sufficient shrinkage for PR nor sufficient increase for PD
- **PD (Progressive Disease)**: ≥20% increase in sum of diameters of target lesions or appearance of new lesions

## JSONL Export Format

The `--jsonl` option generates a JSONL (JSON Lines) file compatible with RECIST visualization applications. Each line contains:

```json
{
  "patient_id": "P0000",
  "timepoint": 0,
  "study_date": "2024-01-02",
  "baseline_sld_mm": 94,
  "current_sld_mm": null,
  "nadir_sld_mm": null,
  "overall_response": "SD",
  "lesions": [
    {
      "lesion_id": "primary_RLL",
      "kind": "primary",
      "organ": "lung",
      "location": "RLL",
      "rule": "longest",
      "baseline_mm": 55,
      "follow_mm": null,
      "size_mm_current": 55,
      "margin": "spiculated",
      "enhancement": "enhancing",
      "necrosis": false,
      "suspicious": true,
      "target": true
    }
  ]
}
```

**Key fields:**
- `patient_id`: Unique patient identifier
- `timepoint`: 0 = baseline, 1+ = follow-up studies
- `study_date`: YYYY-MM-DD format
- `baseline_sld_mm`: Sum of longest diameters at baseline (null for follow-ups)
- `current_sld_mm`: Current sum of longest diameters (null for baseline)
- `overall_response`: CR, PR, SD, or PD
- `lesions`: Array of individual lesions with size measurements

## Notes

- All content is synthetic and non-PHI.
- Intended to exercise **TNM staging extraction**, not to generate perfect prose.
- You can tune verbosity and normal-by-exception ratios via flags.
- Response tracking follows simplified RECIST criteria for realistic oncology workflows.

