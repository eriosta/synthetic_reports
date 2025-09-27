# SynthRad: Synthetic Radiology Report Generator

Generate realistic **lung cancer CT chest reports** with TNM staging, follow-up tracking, and RECIST response assessment.

## 🚀 Quick Start

```bash
# Install
pip install -e .

# Generate 10 reports
synthrad --n 10 --out ./reports

# Generate with follow-up studies
synthrad --n 5 --follow-up --studies-per-patient 3 --out ./timeline_reports
```

## ✨ Features

- **TNM Staging**: Realistic T/N/M categories with staging rationale
- **Follow-up Tracking**: Baseline + follow-up studies with RECIST response (CR/PR/SD/PD)
- **RadLex Integration**: Hierarchical anatomic mapping (optional)
- **Multiple Formats**: Text reports + structured JSON + JSONL export
- **Deterministic**: Reproducible results with seed control

## 📁 Project Structure

```
synthetic_reports/
├── src/synthrad/     # Core generator code
├── notebooks/        # Jupyter notebooks for analysis
├── tools/           # Utility scripts
├── tests/           # Test suite
└── rad_nlp.py       # RadGraph NLP analysis
```

## 🛠 Installation

### Basic Installation
```bash
git clone <repository-url>
cd synthetic_reports
pip install -e .
```

### With Optional Dependencies
```bash
# For notebook analysis
pip install -r notebooks/requirements.txt

# For RadGraph NLP analysis
pip install radgraph
```

## 📖 Usage

### Command Line

```bash
# Basic generation
synthrad --n 10 --out ./reports

# Advanced staging
synthrad --n 5 --stage-dist "I:0.2,II:0.3,III:0.4,IV:0.1" --out ./staged_reports

# Follow-up with response tracking
synthrad --n 5 --follow-up --studies-per-patient 3 --jsonl cohort.jsonl --out ./timeline

# Specific lobe focus
synthrad --n 10 --lobe RUL --out ./rul_reports
```

### Python API

```python
from synthrad import generator as gen

# Generate single case
case = gen.generate_case(
    seed=42,
    stage_dist={"I": 0.3, "II": 0.3, "III": 0.3, "IV": 0.1}
)

# Generate report text
report = gen.generate_report(case)
print(report)

# Save to files
gen.write_case(case, "./output", "case_001")
```

## ⚙️ Key Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--n` | Number of patients | `--n 10` |
| `--stage-dist` | Stage distribution | `"I:0.3,II:0.3,III:0.3,IV:0.1"` |
| `--follow-up` | Enable follow-up studies | `--follow-up` |
| `--studies-per-patient` | Max studies per patient | `--studies-per-patient 3` |
| `--lobe` | Force specific lobe | `--lobe RUL` |
| `--jsonl` | Export JSONL file | `--jsonl cohort.jsonl` |

## 📊 Output Formats

### Text Report
```
FINDINGS:
There is a 34 mm spiculated mass in the right upper lobe...

IMPRESSION:
1. Right upper lobe mass, concerning for primary lung neoplasm.
2. Right hilar lymph node enlargement.
```

### JSON Sidecar
```json
{
  "primary": {"lobe": "RUL", "size_mm": 34},
  "nodes": [{"station": "4R", "short_axis_mm": 12}],
  "tnm": {"T": "T2a", "N": "N2", "M": "M0", "stage_group": "IIB"}
}
```

### JSONL Export (RECIST)
```json
{
  "patient_id": "P0000",
  "timepoint": 0,
  "overall_response": "SD",
  "lesions": [{"lesion_id": "primary_RUL", "baseline_mm": 34}]
}
```

## 🔬 RadGraph NLP Analysis

Analyze generated reports with RadGraph:

```python
from rad_nlp import run_radgraph, bucket_findings

# Analyze report
report = "RUL mass with spiculated margins. No pleural effusion."
annotations = run_radgraph([report])
buckets = bucket_findings(annotations)

print(f"Present: {len(buckets['present'])}")
print(f"Absent: {len(buckets['absent'])}")
```

## 📓 Notebooks

The `notebooks/` directory contains:
- **cohort.ipynb**: Multi-visit patient timeline generation
- Analysis tools for report quality assessment
- Statistical analysis and visualization

## 🏥 Clinical Features

### TNM Staging
- **T Category**: Based on size, location, and invasion
- **N Category**: IASLC nodal station mapping
- **M Category**: Distant metastasis assessment
- **Stage Group**: AJCC 8th edition staging

### RECIST Response
- **CR**: Complete disappearance of target lesions
- **PR**: ≥30% decrease in sum of diameters
- **SD**: Neither PR nor PD criteria met
- **PD**: ≥20% increase or new lesions

### Anatomic Mapping
- **RadLex Integration**: Hierarchical anatomic relationships
- **IASLC Stations**: Standardized nodal station mapping
- **Lobar Specificity**: RUL, RML, RLL, LUL, LLL

## 🔧 Advanced Configuration

### Stage Distributions
```bash
# Early-stage focused
--stage-dist "I:0.4,II:0.3,III:0.2,IV:0.1"

# Advanced-stage focused  
--stage-dist "I:0.1,II:0.2,III:0.4,IV:0.3"
```

### Response Distributions
```bash
# Optimistic (more responses)
--response-dist "CR:0.2,PR:0.4,SD:0.3,PD:0.1"

# Conservative (more stable disease)
--response-dist "CR:0.05,PR:0.2,SD:0.5,PD:0.25"
```

## 🚨 Troubleshooting

### Common Issues
```bash
# Import errors
pip install -e .

# Missing dependencies
pip install pydantic>=2.5 requests>=2.25.0

# RadLex API issues
export BIOPORTAL_API_KEY="your_api_key_here"
```

## 📝 Notes

- All content is **synthetic and non-PHI**
- Designed for **TNM extraction pipeline testing**
- **Deterministic** by seed for reproducible results
- **RECIST-compliant** response tracking
- **RadLex mapping** requires BioPortal API key

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

[Add your license information here]