import random

# -----------------------
# Core anatomy dictionaries
# -----------------------
LOBES = ["RUL", "RML", "RLL", "LUL", "LLL"]
SIDE_FROM_LOBE = {
    "RUL": "right upper lobe",
    "RML": "right middle lobe",
    "RLL": "right lower lobe",
    "LUL": "left upper lobe",
    "LLL": "left lower lobe",
}

ARTIFACTS = [
    "Motion degradation from respiratory artifact limits fine detail.",
    "Beam-hardening streak artifact from contrast in great vessels mildly limits evaluation.",
    "Suboptimal inspiration with dependent atelectasis."
]

# Kept for optional use
NORMAL_BETS = {
    "mediastinum": [
        "Cardiomediastinal contours within normal limits.",
        "No mediastinal mass."
    ],
    "pleura": [
        "No pleural effusion or pneumothorax.",
        "No pleural thickening."
    ],
    "great_vessels": [
        "Thoracic aorta normal caliber without aneurysm or dissection."
    ],
    "abdomen_incidental": [
        "Liver homogeneous in attenuation without focal mass.",
        "Spleen normal in size.",
        "Adrenal glands without nodules.",
        "Kidneys enhance symmetrically without hydronephrosis."
    ],
}

PRIMARY_FEATURE_PHRASES = {
    "spiculation": ["spiculated margins", "irregular, spiculated contour"],
    "cavitation": ["internal cavitation", "central cavitary change"],
    "pleural_inv_suspected": ["pleural abutment with stranding, invasion not excluded", "broad-based pleural contact, possible invasion"],
    "chest_wall_invasion": ["erosion of adjacent rib compatible with chest wall invasion"],
    "atelectasis": ["associated segmental atelectasis", "adjacent volume loss"]
}

# Canonical feature mapper to avoid duplicated wording
FEATURE_CANON = {
    "spiculation": "spiculated margins",
    "cavitation": "internal cavitation",
    "pleural_inv_suspected": "pleural abutment; invasion not excluded",
    "chest_wall_invasion": "erosion of adjacent rib compatible with chest wall invasion",
    "atelectasis": "adjacent volume loss",
}

def feature_text(features: list[str]) -> str:
    """Return a comma-separated canonical feature string or 'smooth margins' if none."""
    texts = [FEATURE_CANON[f] for f in features if f in FEATURE_CANON]
    seen = set()
    dedup = []
    for t in texts:
        if t not in seen:
            seen.add(t)
            dedup.append(t)
    return ", ".join(dedup) if dedup else "smooth margins"

NODE_STATIONS = ["1R","1L","2R","2L","3A","3P","4R","4L","5","6","7","8","9","10R","10L","11R","11L","12R","12L"]

# Station metadata with human-friendly labels and N-groups
STATION_METADATA = {
    # N2 mediastinal
    "2R": {"label": "right upper paratracheal", "group": "N2"},
    "2L": {"label": "left upper paratracheal", "group": "N2"},
    "3A": {"label": "prevascular", "group": "N2"},
    "3P": {"label": "retrotracheal", "group": "N2"},
    "4R": {"label": "right lower paratracheal", "group": "N2"},
    "4L": {"label": "left lower paratracheal", "group": "N2"},
    "5":  {"label": "subaortic (aortopulmonary window)", "group": "N2"},
    "6":  {"label": "para-aortic", "group": "N2"},
    "7":  {"label": "subcarinal", "group": "N2"},
    "8":  {"label": "para-esophageal", "group": "N2"},
    "9":  {"label": "pulmonary ligament", "group": "N2"},
    # N1 hilar/intrapulmonary
    "10R":{"label": "right hilar", "group": "N1"},
    "10L":{"label": "left hilar", "group": "N1"},
    "11R":{"label": "right interlobar", "group": "N1"},
    "11L":{"label": "left interlobar", "group": "N1"},
    "12R":{"label": "right lobar", "group": "N1"},
    "12L":{"label": "left lobar", "group": "N1"},
}

def station_label(station: str) -> tuple[str, str]:
    """Return human-friendly label and N-group for a station, defaults if unknown."""
    meta = STATION_METADATA.get(station, {"label": f"station {station}", "group": "N?"})
    return meta["label"], meta["group"]

def mm_desc(size_mm: int) -> str:
    """Return a realistic adjective for node phrases and tiny lesions."""
    return "subcentimeter" if size_mm < 10 else f"{size_mm} mm"

def node_phrase(station: str, short_axis_mm: int, style="detailed") -> str:
    """Distinct style-aware node phrasing with anatomy labels and size-pathology semantics."""
    # normalize style aliases
    alias = {
        "oncology": "detailed",
        "clinical": "concise",
        "academic": "detailed",
        "narrative": "detailed"
    }
    style = alias.get(style, style)

    label, group = station_label(station)
    mm_txt = mm_desc(short_axis_mm)
    pathologic = short_axis_mm >= 10

    if style == "concise":
        # terse, telegraphic; explicit SA and optional pathology tag
        if pathologic:
            return f"{station} node {mm_txt} short axis (pathologic)."
        else:
            return f"{station} node {mm_txt} short axis."

    # detailed: full sentence, includes anatomic label + parenthetical station
    if pathologic:
        return f"Enlarged {label} ({station}) lymph node measuring {mm_txt} in short axis."
    else:
        return f"{label} ({station}) lymph node {mm_txt} in short axis."

# Legacy examples (not used directly now, but kept for reference)
NODE_PHRASES = [
    "Enlarged {station} lymph node measuring {size} mm in short-axis.",
    "Subcentimeter {station} node measuring {size} mm short-axis."
]

# -----------------------
# Metastatic sites & phrases
# -----------------------
MET_SITES = [
    "adrenal_right", "adrenal_left", "liver", "bone", "brain",
    "contralateral_lung", "pleura", "peritoneum", "omentum", "retroperitoneal_nodes"
]

MET_PHRASES = {
    "adrenal_right": ["Right adrenal nodule {size} mm, indeterminate but suspicious in oncologic context."],
    "adrenal_left": ["Left adrenal nodule {size} mm, suspicious for metastasis."],
    "liver": ["Low-attenuation hepatic lesion {size} mm, suspicious for metastasis."],
    "bone": ["Sclerotic osseous focus {size} mm in a vertebral body, concerning for metastasis."],
    "brain": ["Note: intracranial imaging not included on this exam; known brain lesion {size} mm from prior study referenced."],
    "contralateral_lung": ["Contralateral pulmonary nodule {size} mm, suspicious."],
    "pleura": ["Pleural-based soft tissue nodule {size} mm concerning for pleural metastatic deposit."],
    "peritoneum": ["Peritoneal nodularity {size} mm suspicious for carcinomatosis."],
    "omentum": ["Omental soft tissue nodule {size} mm, suspicious for metastasis."],
    "retroperitoneal_nodes": ["Retroperitoneal lymph node {size} mm short-axis, suspicious."]
}

LIVER_DETAIL_PHRASES = [
    "Low-attenuation lesion {size} mm without definite washout, suspicious in oncologic context.",
    "Arterial phase hyperenhancing focus {size} mm, washout not assessed; metastasis not excluded."
]

# -----------------------
# Two realistic radiologist styles
# -----------------------
RADIOLOGIST_STYLES = {
    "concise": {
        "normal_mediastinum": ["No pathologic mediastinal adenopathy."],
        "normal_pleura": ["No pleural effusion."],
        "normal_great_vessels": ["Great vessels normal."],
        "normal_abdomen": [
            "Liver homogeneous in attenuation without focal mass.",
            "Adrenal glands without nodules."
        ],
        "normal_bones": ["No destructive osseous lesion."],
        "artifact_phrases": ["Motion artifact present.", "Beam-hardening artifact."],
        "primary_lesion_phrases": [
            "{side} mass {size} mm, {features}.",
            "{side} pulmonary mass {size} mm with {features}."
        ],
        "node_phrases": [
            "{station} node {size} mm short axis."
        ],
        "metastasis_phrases": [
            "{site} lesion {size} mm, suspicious for metastasis.",
            "{site} nodule {size} mm, suspicious."
        ]
    },

    "detailed": {
        "normal_mediastinum": [
            "Mediastinum demonstrates normal contours without evidence of mass or pathologic lymphadenopathy.",
            "No mediastinal mass or pathologic adenopathy identified."
        ],
        "normal_pleura": [
            "Pleural spaces clear without effusion.",
            "No pleural effusion."
        ],
        "normal_great_vessels": [
            "Thoracic aorta and great vessels normal in caliber and course without aneurysm or dissection.",
            "Aorta and great vessels without significant abnormality."
        ],
        "normal_abdomen": [
            "Liver homogeneous in attenuation without focal mass.",
            "No focal hepatic lesion.",
            "Spleen normal in size.",
            "Adrenal glands without nodules."
        ],
        "normal_bones": [
            "Osseous structures without fracture or destructive lesion.",
            "No aggressive osseous lesion."
        ],
        "artifact_phrases": [
            "Respiratory motion limits fine detail evaluation in some areas.",
            "Beam hardening from intravascular contrast mildly limits evaluation.",
            "Mild respiratory motion artifact.",
            "Minor beam hardening from contrast."
        ],
        "primary_lesion_phrases": [
            "There is a {size} mm mass in the {side} demonstrating {features}.",
            "A {size} mm pulmonary mass is identified in the {side} with {features}.",
            "There is a {size} mm {side} pulmonary mass with {features}."
        ],
        "node_phrases": [
            "Enlarged {station} lymph node measuring {size} mm in short axis."
        ],
        "metastasis_phrases": [
            "A {size} mm lesion is present in the {site}, suspicious for metastasis.",
            "{site} metastasis {size} mm is present.",
            "{site} lesion {size} mm, compatible with metastasis."
        ]
    }
}

# -----------------------
# Comparison / RECIST / PET utilities
# -----------------------
def fmt_mm(mm: int) -> str:
    return f"{mm} mm" if mm < 100 else f"{mm/10:.1f} cm"

def compare_size(curr_mm: int, prior_mm: int|None) -> str:
    if prior_mm is None:
        return "baseline measurement."
    delta = curr_mm - prior_mm
    pct = (delta/prior_mm)*100 if prior_mm else 0
    if abs(pct) < 20:
        change = "stable"
    elif pct >= 20:
        change = "increased"
    else:
        change = "decreased"
    return f"{change} (now {fmt_mm(curr_mm)}, was {fmt_mm(prior_mm)}; Δ {delta:+} mm, {pct:+.0f}%)."

def recist_overall_response(sum_curr: int, sum_prior: int|None, new_lesions: bool=False) -> str:
    if new_lesions:
        return "Progressive disease (new lesions)."
    if sum_prior is None:
        return "Baseline (no prior)."
    pct = (sum_curr - sum_prior)/sum_prior*100 if sum_prior else 0
    if pct <= -30:
        return "Partial response."
    if pct < 20:
        return "Stable disease."
    return "Progressive disease (≥20% increase)."

# PET-CT phrases
PET_PHRASES = {
    "normal": [
        "Physiologic uptake in brain, myocardium, liver, spleen, and bowel.",
        "Physiologic brown fat activity may be present."
    ],
    "lesion": [
        "{site} FDG-avid lesion SUVmax {suv:.1f}, corresponding to {size} mm on CT.",
        "Hypermetabolic {site} (SUVmax {suv:.1f}); CT measures {size} mm."
    ],
    "nodes": [
        "FDG-avid {station} node SUVmax {suv:.1f}, {size} mm short-axis."
    ],
    "refs": [
        "Reference liver SUVmean {liver:.1f}, mediastinal blood pool SUVmean {mbp:.1f}."
    ],
    "pitfalls": [
        "No focal uptake in laryngeal muscles or brown fat to confound interpretation.",
        "No suspicious FDG-avid bone lesions."
    ]
}

def percist_summary(tumor_suv: float, tumor_suv_prior: float|None, new_lesions: bool=False) -> str:
    if new_lesions:
        return "Progressive metabolic disease (new FDG-avid lesions)."
    if tumor_suv_prior is None:
        return "Baseline metabolic assessment."
    change = (tumor_suv - tumor_suv_prior)/tumor_suv_prior*100
    if change <= -30:
        return "Partial metabolic response."
    if change < 30:
        return "Stable metabolic disease."
    return "Progressive metabolic disease."

# Technique strings
TECHNIQUE_CT_CAP = "CT chest, abdomen, and pelvis with IV contrast. No oral contrast. Axial images with multiplanar reconstructions."
TECHNIQUE_PET_CT = "Whole-body FDG PET-CT from skull base to mid-thigh. Low-dose CT for attenuation correction and anatomic correlation."

# Random helpers
def pick(seq, rng=None):
    rng = rng or random
    return rng.choice(seq)

def make_rng(seed=None):
    r = random.Random()
    if seed is not None:
        r.seed(seed)
    return r