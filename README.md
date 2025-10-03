# SynthRad: Synthetic Radiology Report Generator

Generate realistic **lung cancer CT chest reports** with TNM staging, follow-up tracking, RECIST response assessment, and **ontology-focused RadLex integration**.

## Quick Start

```bash
# Install
pip install -e .

# Generate 10 reports with ontology configs
synthrad --n 10 --out ./reports

# Generate with follow-up studies and JSONL export
synthrad --n 5 --follow-up --studies-per-patient 3 --jsonl cohort.jsonl --out ./timeline_reports

# Run analysis dashboard
streamlit run analysis.py
```

## Features

- **TNM Staging**: Realistic T/N/M categories with AJCC 8th edition staging
- **Follow-up Tracking**: Baseline + follow-up studies with RECIST response (CR/PR/SD/PD)
- **Ontology Integration**: RadLex-anchored graph JSON configurations
- **Multiple Formats**: Text reports + structured JSON + JSONL export + ontology configs
- **Analysis Dashboard**: Streamlit-based visualization and analysis
- **Deterministic**: Reproducible results with seed control

## Project Structure

```
synthetic_reports/
├── src/synthrad/                    # Core generator code
│   ├── generator.py                 # Main generation logic
│   ├── ontology_config_generator.py # RadLex-anchored configs
│   ├── radlex_resolver.py          # Enhanced RadLex resolver
│   ├── anatomic_mapper.py          # Anatomical mapping
│   └── schema.py                   # Data schemas
├── notebooks/                       # Jupyter notebooks
│   └── cohort.ipynb                # Multi-visit timeline generation
├── tools/                          # Utility scripts
├── tests/                          # Test suite
├── analysis.py                     # Streamlit analysis dashboard
└── ONTOLOGY_INTEGRATION.md         # Detailed ontology documentation
```

## Installation

### Basic Installation
```bash
git clone <repository-url>
cd synthetic_reports
pip install -e .
```

### With Optional Dependencies
```bash
# For analysis dashboard
pip install streamlit plotly pandas

# For RadLex integration (optional)
export BIOPORTAL_API_KEY="your_api_key_here"
```

## Usage

### Command Line

```bash
# Basic generation
synthrad --n 10 --out ./reports

# Advanced staging with ontology configs
synthrad --n 5 --stage-dist "I:0.2,II:0.3,III:0.4,IV:0.1" --out ./staged_reports

# Follow-up with response tracking and JSONL export
synthrad --n 5 --follow-up --studies-per-patient 3 --jsonl cohort.jsonl --out ./timeline

# Specific lobe focus
synthrad --n 10 --lobe RUL --out ./rul_reports
```

### Python API

```python
from synthrad import generator as gen
from synthrad.ontology_config_generator import OntologyConfigGenerator

# Generate single case
case = gen.generate_case(
    seed=42,
    stage_dist={"I": 0.3, "II": 0.3, "III": 0.3, "IV": 0.1}
)

# Generate report text
report = gen.generate_report(case)
print(report)

# Generate ontology config
ontology_gen = OntologyConfigGenerator(use_radlex=True)
config = ontology_gen.generate_ontology_config(case_data, "P0000", "2024-07-27", 0)

# Save to files
gen.write_case(case, "./output", "case_001")
```

### Analysis Dashboard

```bash
# Launch interactive analysis dashboard
streamlit run analysis.py
```

## Output Formats

### 1. Text Report
```
FINDINGS:
There is a 34 mm spiculated mass in the right upper lobe...

IMPRESSION:
1. Right upper lobe mass, concerning for primary lung neoplasm.
2. Right hilar lymph node enlargement.
```

### 2. JSONL Export (RECIST)
```json
{
  "patient_id": "P0000",
  "timepoint": 0,
  "study_date": "2024-07-27",
  "overall_response": "SD",
  "staging": {"T": "T2a", "N": "N2", "M": "M0", "stage_group": "IIB"},
  "lesions": [{"lesion_id": "primary_RUL", "baseline_mm": 34}]
}
```

### 3. Ontology Configuration (RadLex-anchored)
```json
{
  "graph_id": "P0000_t0",
  "patient_id": "P0000",
  "nodes": [
    {
      "id": "lesion:primary_RML",
      "type": "lesion",
      "category": "primary_tumor",
      "anatomy": {
        "text": "right middle lobe of lung",
        "radlex": {"label": "right middle lobe of lung", "rid": "RID13171"}
      },
      "target_status": "target"
    }
  ],
  "edges": [
    {
      "from": "lesion:primary_RML",
      "to": "anatomy:right_middle_lobe_of_lung",
      "relation": "located_in"
    }
  ]
}
```

## Clinical Standards

### TNM Staging (AJCC 8th Edition)
- **T Category**: Based on size, location, and invasion
- **N Category**: IASLC nodal station mapping (1R/1L, 4R/4L, 7, 10R/10L)
- **M Category**: Distant metastasis assessment
- **Stage Groups**: I, II, IIIA, IIIB, IV

### RECIST 1.1 Response
- **CR**: Complete disappearance of target lesions
- **PR**: ≥30% decrease in sum of diameters
- **SD**: Neither PR nor PD criteria met
- **PD**: ≥20% increase or new lesions

### RadLex Ontology Integration
- **Search-first strategy**: Exact matching before fuzzy search
- **Context-aware resolution**: Anatomical context for disambiguation
- **Persistent lesion UIDs**: Enables temporal tracking
- **Graph relationships**: Explicit edges between entities
- **Offline mode**: Works without API access using seeded concepts

## Advanced Configuration

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

## Analysis & Visualization

### Streamlit Dashboard
The `analysis.py` dashboard provides:
- **Patient timeline visualization**: Lesion tracking over time
- **TNM staging display**: Stage progression visualization
- **RECIST response analysis**: Response assessment tracking
- **Interactive exploration**: Patient selection and study comparison

### Graph Queries (Ontology Configs)
```python
# Find all lesions in right lung
right_lung_lesions = [
    node for node in config.nodes 
    if (node.get('type') == 'lesion' and 
        'right' in node.get('anatomy', {}).get('text', ''))
]

# Find all target lesions
target_lesions = [
    node for node in config.nodes 
    if (node.get('type') == 'lesion' and 
        node.get('target_status') == 'target')
]
```

## Troubleshooting

### Common Issues
```bash
# Import errors
pip install -e .

# Missing dependencies
pip install pydantic>=2.5 requests>=2.25.0 streamlit plotly

# RadLex API issues (optional)
export BIOPORTAL_API_KEY="your_api_key_here"
```

## Key Notes

- All content is **synthetic and non-PHI**
- Designed for **TNM extraction pipeline testing** and **AI benchmarking**
- **Deterministic** by seed for reproducible results
- **RECIST-compliant** response tracking
- **RadLex mapping** requires BioPortal API key (optional)
- **Ontology configs** enable graph-based analysis and FHIR compatibility

## Documentation

- **`ONTOLOGY_INTEGRATION.md`**: Detailed RadLex integration guide
- **`notebooks/cohort.ipynb`**: Multi-visit timeline generation examples
- **`tests/`**: Comprehensive test suite

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**MIT License Summary:**
- Commercial use allowed
- Modification allowed  
- Distribution allowed
- Private use allowed
- License and copyright notice required

**Important Note:** This software generates synthetic data for research and benchmarking purposes only. It is not intended for clinical use or to replace professional medical judgment.