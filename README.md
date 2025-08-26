# SynthRad: Synthetic Radiology Report Generator

Synthetic *oncology-grade* CT chest radiology reports for **lung cancer**, designed to feed your TNM extraction pipeline.

## Project Structure

```
synthetic_reports/
├── configs/          # Configuration files (samples, research, custom)
├── tools/            # Utility tools (builders, generators, utils)
├── docs/             # Documentation (guides only)
├── examples/         # Example scripts and demos
├── src/              # Source code
└── tests/            # Test files
```

📁 **configs/** - Organized configuration files  
🔧 **tools/** - Utility tools and scripts  
📚 **docs/** - Comprehensive documentation  
💡 **examples/** - Working examples and demos  

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed organization.

- Realistic structure: `FINDINGS` and `IMPRESSION` sections, common artifacts, comparisons, and normal-by-exception phrasing.
- TNM-aware controls: pick T/N/M distributions, lobar location, histology hints, post-treatment changes, etc.
- **Response tracking**: Generate baseline and follow-up reports with response status (SD, PD, CR, PR) following RECIST criteria.
- **Variable follow-up studies**: Each patient gets 1 baseline + 1-N follow-up studies (where N is the max you specify).
- **JSONL export**: Generate `cohort_labels.jsonl` files compatible with RECIST visualization apps.
- Emits both **free-text report** and a parallel **structured JSON** (lesion list + TNM + staging rationale) for evaluation.
- Deterministic by seed.

## Quick start

### Interactive Configuration Builder

Create custom configurations interactively:

```bash
python tools/builders/config_builder.py
```

This provides a guided interface to create:
- Single configurations
- Configuration sets
- Sample configurations
- Research configurations

### Key Configuration Types

The system includes 3 main configuration types that showcase all major features:

**1. Baseline Generation** - Single CT scans with TNM staging
```bash
# Generate 10 baseline cases with balanced stage distribution
python tools/generators/generate.py --configs configs/samples/config.json --names baseline_standard
```

**2. Follow-up Tracking** - Multiple studies per patient with response assessment
```bash
# Generate baseline + follow-up studies with response tracking (CR/PR/SD/PD)
python tools/generators/generate.py --configs configs/samples/config.json --names followup_standard
```

**3. RadLex Anatomic Mapping** - Hierarchical anatomic mapping with RadLex integration
```bash
# Generate reports with anatomic mapping
python tools/generators/generate.py --configs configs/samples/config.json --names anatomic_mapping
```

### Key Features

✅ **Type Safety** - Validated configuration objects with clear error messages  
✅ **Multiple Formats** - Support for JSON and YAML configuration files  
✅ **Tagging System** - Organize configurations with tags for easy filtering  
✅ **Interactive Builder** - Guided creation of configurations  
✅ **Validation** - Automatic validation of all parameters and distributions  
✅ **Flexible Filtering** - Run specific configurations by name or tags  
✅ **Parallel Execution** - Run multiple configurations simultaneously  
✅ **Clean Output** - Each configuration gets its own organized output directory  

### Essential Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `num_patients` | Number of patients to generate | `10` |
| `stage_distribution` | Cancer stage distribution | `"I:0.3,II:0.3,III:0.3,IV:0.1"` |
| `follow_up` | Generate follow-up studies | `true` |
| `use_radlex` | Anatomic mapping enabled | `true` |

## All Available Arguments

Here's a comprehensive list of all command-line arguments you can customize:

### Core Arguments
- `--n <number>`: Number of patients to generate (default: 5)
- `--out <directory>`: Output directory (default: "./out")
- `--seed <number>`: Random seed for deterministic generation (default: 0)
- `--legacy-mode`: Use legacy flat file structure instead of organized directories

### Tumor and Staging Control
- `--lobe <lobe>`: Force primary lobe location (choices: RUL, RML, RLL, LUL, LLL)
- `--stage-dist <distribution>`: Stage distribution (default: "I:0.25,II:0.25,III:0.30,IV:0.20")
  - Example: `--stage-dist "I:0.2,II:0.25,III:0.35,IV:0.2"`

### Follow-up and Response Tracking
- `--follow-up`: Generate follow-up cases for each baseline case
- `--follow-up-days <days>`: Days between baseline and follow-up (default: 90)
- `--studies-per-patient <number>`: Maximum studies per patient, 2-10 (default: 5)
  - Each patient gets 1 baseline + 1-{max} follow-up studies
- `--response-dist <distribution>`: Response distribution (default: "CR:0.1,PR:0.3,SD:0.4,PD:0.2")
  - Example: `--response-dist "CR:0.2,PR:0.4,SD:0.3,PD:0.1"`

### RadLex Anatomic Mapping
- `--no-radlex`: Disable RadLex anatomic mapping (enabled by default)
  - By default, anatomic mapping is enabled
  - Use `--no-radlex` to disable anatomic mapping
  - Creates hierarchical anatomic maps when enabled

### Output Formats
- `--jsonl <filename>`: Output JSONL file for React app (e.g., "cohort_labels.jsonl")

### Distribution Format Examples

**Stage Distribution:**
```bash
# Balanced distribution
--stage-dist "I:0.25,II:0.25,III:0.30,IV:0.20"

# Early-stage focused
--stage-dist "I:0.4,II:0.3,III:0.2,IV:0.1"

# Advanced-stage focused
--stage-dist "I:0.1,II:0.2,III:0.4,IV:0.3"
```

**Response Distribution:**
```bash
# Standard distribution
--response-dist "CR:0.1,PR:0.3,SD:0.4,PD:0.2"

# Optimistic (more responses)
--response-dist "CR:0.2,PR:0.4,SD:0.3,PD:0.1"

# Conservative (more stable disease)
--response-dist "CR:0.05,PR:0.2,SD:0.5,PD:0.25"
```

**RadLex Anatomic Mapping:**
```bash
# Enable anatomic mapping (default)
# No flag needed

# Disable anatomic mapping
--no-radlex
```

### Complete Example Commands

```bash
# Basic generation
python -m synthrad --n 10 --seed 42 --out ./basic_reports

# Advanced staging with specific lobe
python -m synthrad --n 5 --lobe RUL --stage-dist "I:0.1,II:0.2,III:0.4,IV:0.3" --out ./advanced_staging

# Follow-up with custom intervals
python -m synthrad --n 3 --follow-up --follow-up-days 60 --studies-per-patient 4 --out ./followup_reports

# Optimistic response tracking
python -m synthrad --n 5 --follow-up --response-dist "CR:0.2,PR:0.4,SD:0.3,PD:0.1" --out ./optimistic_reports

# RadLex anatomic mapping enabled (default)
python -m synthrad --n 10 --out ./anatomic_reports

# Complete pipeline with JSONL export
python -m synthrad --n 5 --follow-up --studies-per-patient 3 --jsonl cohort.jsonl --out ./complete_pipeline

# Legacy mode with flat file structure
python -m synthrad --n 3 --legacy-mode --out ./legacy_reports
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

## RadLex Anatomic Mapping

This project includes RadLex ontology integration for **hierarchical anatomic mapping**. Instead of text enhancement, RadLex is used to create structured, machine-readable anatomic relationships.

### Quick RadLex Setup

1. Get a free API key from [BioPortal](https://bioportal.bioontology.org/)
2. Set environment variable: `export BIOPORTAL_API_KEY="your_key"`

### RadLex Anatomic Mapping Features

- **Hierarchical Structure**: Body regions → Organs → Sub-organs → Specific locations
- **Structured Data**: Machine-readable anatomic relationships
- **Clinical Decision Support**: Target vs non-target lesion classification
- **TNM Staging Automation**: Structured data for automated staging
- **Follow-up Tracking**: Track lesions across studies by anatomic location
- **Multi-modal Integration**: Map findings to imaging coordinates
- **Configurable**: Simple enable/disable option

See [docs/guides/ANATOMIC_MAPPING_GUIDE.md](docs/guides/ANATOMIC_MAPPING_GUIDE.md) for detailed documentation.

## Notes

- All content is synthetic and non-PHI.
- Intended to exercise **TNM staging extraction**, not to generate perfect prose.
- You can tune verbosity and normal-by-exception ratios via flags.
- Response tracking follows simplified RECIST criteria for realistic oncology workflows.
- RadLex anatomic mapping is optional and requires a BioPortal API key.
- Test outputs and cache files are automatically excluded via `.gitignore`.

