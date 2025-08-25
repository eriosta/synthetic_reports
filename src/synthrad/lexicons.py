import random

LOBES = ["RUL", "RML", "RLL", "LUL", "LLL"]
SIDE_FROM_LOBE = {"RUL":"right", "RML":"right middle", "RLL":"right lower", "LUL":"left upper", "LLL":"left lower"}

ARTIFACTS = [
    "Motion degradation from respiratory artifact limits fine detail.",
    "Beam-hardening streak artifact from contrast in great vessels mildly limits evaluation.",
    "Suboptimal inspiration with dependent atelectasis."
]

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
        "Liver homogeneous without focal mass.",
        "Spleen normal in size.",
        "Adrenal glands normal without nodules.",
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

NODE_STATIONS = ["2R","4R","2L","4L","7","10R","10L","11R","11L"]
NODE_PHRASES = [
    "Enlarged {station} lymph node measuring {size} mm in short-axis.",
    "Subcentimeter {station} node measuring {size} mm short-axis."
]

MET_SITES = ["adrenal_right", "adrenal_left", "liver", "bone", "brain", "contralateral_lung", "pleura"]
MET_PHRASES = {
    "adrenal_right": ["Right adrenal nodule {size} mm, indeterminate but suspicious in oncologic context."],
    "adrenal_left": ["Left adrenal nodule {size} mm, suspicious for metastasis."],
    "liver": ["Low-attenuation hepatic lesion {size} mm, suspicious for metastasis."],
    "bone": ["Sclerotic osseous focus {size} mm in a vertebral body, concerning for metastasis."],
    "brain": ["Note: intracranial imaging not included on this exam; known brain lesion {size} mm from prior study referenced."],
    "contralateral_lung": ["Contralateral pulmonary nodule {size} mm, suspicious."],
    "pleura": ["Pleural-based soft tissue nodule {size} mm concerning for pleural metastatic deposit."]
}

# Different radiologist writing styles
RADIOLOGIST_STYLES = {
    "concise": {
        "normal_mediastinum": ["Mediastinum normal."],
        "normal_great_vessels": ["Great vessels normal."],
        "normal_abdomen": ["Abdomen unremarkable."],
        "normal_bones": ["Bones unremarkable."],
        "artifact_phrases": ["Motion artifact present.", "Beam hardening artifact."]
    },
    "detailed": {
        "normal_mediastinum": [
            "Mediastinum demonstrates normal contours without evidence of mass or lymphadenopathy.",
            "Cardiomediastinal silhouette is within normal limits with no mediastinal widening."
        ],
        "normal_great_vessels": [
            "Thoracic aorta demonstrates normal caliber without evidence of aneurysm, dissection, or other abnormality.",
            "Great vessels appear normal in caliber and course without evidence of vascular pathology."
        ],
        "normal_abdomen": [
            "Upper abdominal structures demonstrate normal appearance without focal abnormality.",
            "Liver, spleen, and adrenal glands appear normal in size and echogenicity."
        ],
        "normal_bones": [
            "Osseous structures demonstrate normal alignment and density without evidence of fracture or destructive lesion.",
            "Bones appear normal without evidence of metastatic disease or other osseous pathology."
        ],
        "artifact_phrases": [
            "Motion artifact from respiratory variation limits fine detail evaluation in some areas.",
            "Beam hardening artifact from contrast material in great vessels mildly limits evaluation."
        ]
    },
    "clinical": {
        "normal_mediastinum": [
            "No mediastinal mass or significant lymphadenopathy.",
            "Mediastinum appears stable without concerning findings."
        ],
        "normal_great_vessels": [
            "Aorta and great vessels appear stable.",
            "No significant vascular abnormality identified."
        ],
        "normal_abdomen": [
            "Upper abdomen appears stable.",
            "No significant abdominal abnormality on limited evaluation."
        ],
        "normal_bones": [
            "No acute fracture or aggressive osseous lesion.",
            "Bones appear stable without concerning findings."
        ],
        "artifact_phrases": [
            "Some respiratory motion artifact.",
            "Mild beam hardening artifact from contrast."
        ]
    }
}

def pick(seq): return random.choice(seq)
