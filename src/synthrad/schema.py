from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class Meta(BaseModel):
    modality: Literal["CT chest with IV contrast"] = "CT chest with IV contrast"
    comparison_date: Optional[str] = None
    prior_therapy: List[str] = []
    patient_id: Optional[str] = None
    visit_number: int = 1  # 1 = baseline, 2 = follow-up, etc.
    accession_number: Optional[str] = None
    radiologist_style: Optional[str] = None  # Different writing styles
    radlex_complexity: Optional[str] = None  # RadLex enhancement level used

class Primary(BaseModel):
    lobe: str
    size_mm: int
    features: List[str] = []  # e.g., spiculation, cavitation, pleural_inv_suspected, chest_wall_invasion, atelectasis

class Node(BaseModel):
    station: str  # e.g., 4R, 2L, 7, 10R
    short_axis_mm: int

class Met(BaseModel):
    site: str  # e.g., adrenal_right, liver, brain, bone
    size_mm: int

class TNM(BaseModel):
    T: str
    N: str
    M: str
    stage_group: str

class Case(BaseModel):
    meta: Meta
    primary: Optional[Primary] = None
    nodes: List[Node] = []
    mets: List[Met] = []
    tnm: TNM
    rationale: List[str] = []
    response_status: Optional[str] = None  # SD, PD, CR, PR
