from __future__ import annotations

import argparse, os, random, datetime, json, math
from typing import Dict, List, Optional, Tuple

from .lexicons import LOBES, SIDE_FROM_LOBE, ARTIFACTS, NORMAL_BETS, PRIMARY_FEATURE_PHRASES, NODE_STATIONS, NODE_PHRASES, MET_SITES, MET_PHRASES, RADIOLOGIST_STYLES, pick
from .schema import Case, Meta, Primary, Node, Met, TNM
from .radlex_lexicons import get_radlex_lexicons
from .radlex_config import get_config, PREDEFINED_CONFIGS

# --- TNM logic for NSCLC (simplified, IASLC 8th-ish) ---

def t_category(size_mm: int, chest_wall_inv: bool, main_bronchus: bool, carina_inv: bool, separate_nodules_same_lobe: bool, separate_nodules_other_ipsi_lobe: bool, diaphragm_inv: bool) -> Tuple[str, List[str]]:
    reasons = []
    if carina_inv:
        reasons.append("T4 due to carina involvement")
        return "T4", reasons
    if diaphragm_inv or chest_wall_inv:
        reasons.append("T3 due to chest wall/diaphragm invasion")
        tcat = "T3"
    else:
        if size_mm <= 10:
            tcat = "T1a"
            reasons.append("T1a because ≤10 mm")
        elif size_mm <= 20:
            tcat = "T1b"
            reasons.append("T1b because >10–20 mm")
        elif size_mm <= 30:
            tcat = "T1c"
            reasons.append("T1c because >20–30 mm")
        elif size_mm <= 50:
            tcat = "T2a"
            reasons.append("T2a because >30–50 mm")
        elif size_mm <= 70:
            tcat = "T2b"
            reasons.append("T2b because >50–70 mm")
        else:
            tcat = "T3"
            reasons.append("T3 because >70 mm")
    if main_bronchus:
        reasons.append("Involves main bronchus → at least T2")
        if tcat.startswith("T1"):
            tcat = "T2a"
    if separate_nodules_same_lobe:
        reasons.append("Separate tumor nodule(s) in same lobe → T3")
        tcat = "T3"
    if separate_nodules_other_ipsi_lobe:
        reasons.append("Separate tumor nodule in different ipsilateral lobe → T4")
        tcat = "T4"
    return tcat, reasons

def n_category(nodes: List[Node]) -> Tuple[str, List[str]]:
    reasons = []
    max_station = None
    max_size = 0
    # quick map: N1 = 10/11; N2 = 2/4/7; N3 = contralateral or supraclav (not modeled), treat 2L/4L as ipsilateral if primary left, here we don't know side; simplify to: any 2/4/7 => N2
    n2_stations = {"2R","4R","2L","4L","7"}
    n1_stations = {"10R","11R","10L","11L"}
    has_n2 = False; has_n1 = False
    for nd in nodes:
        sz = nd.short_axis_mm
        if nd.station in n2_stations and sz >= 10:
            has_n2 = True
            reasons.append(f"N2: station {nd.station} short-axis ≥10 mm ({sz} mm)")
        if nd.station in n1_stations and sz >= 10:
            has_n1 = True
            reasons.append(f"N1: station {nd.station} short-axis ≥10 mm ({sz} mm)")
        if sz > max_size:
            max_size = sz; max_station = nd.station
    if has_n2:
        return "N2", reasons or [f"N2 due to {max_station} {max_size} mm"]
    if has_n1:
        return "N1", reasons or [f"N1 due to {max_station} {max_size} mm"]
    return "N0", ["No pathologically enlarged lymph nodes by size criteria"]

def m_category(mets: List[Met]) -> Tuple[str, List[str]]:
    if not mets:
        return "M0", ["No definite distant metastases identified"]
    # crude: one extrathoracic site → M1b; pleural/contralateral lung could be M1a; multiple extrathoracic → M1c
    extrathoracic = [m for m in mets if m.site not in ("pleura","contralateral_lung")]
    pleural_or_contra = [m for m in mets if m.site in ("pleura","contralateral_lung")]
    reasons = []
    if pleural_or_contra and not extrathoracic:
        reasons.append("M1a: pleural/contralateral lung disease")
        return "M1a", reasons
    if len(extrathoracic) == 1:
        reasons.append("M1b: single extrathoracic metastasis")
        return "M1b", reasons
    else:
        reasons.append("M1c: multiple extrathoracic metastases")
        return "M1c", reasons

def stage_group(T: str, N: str, M: str) -> str:
    if M.startswith("M1"):
        return "IV"
    # very simplified grouping
    t_major = int(T[1]) if T[1].isdigit() else 4
    if N == "N0":
        if t_major <= 1: return "I"
        if t_major == 2: return "II"
        return "III"
    if N == "N1":
        if t_major <= 2: return "II"
        return "III"
    return "III"

# --- text generation helpers ---

def mm(val): return f"{val} mm"

def sample_primary(lobe: Optional[str], stage_hint: Optional[str], rng: random.Random) -> Tuple[Primary, List[str]]:
    lobe = lobe or rng.choice(LOBES)
    # size by stage hint
    if stage_hint in ("I","II"):
        size = rng.randint(12, 48)
    elif stage_hint == "III":
        size = rng.randint(25, 75)
    else:  # IV – size can be anything
        size = rng.randint(15, 65)
    feats = []
    if rng.random() < 0.55: feats.append("spiculation")
    if rng.random() < 0.12: feats.append("cavitation")
    if rng.random() < 0.22: feats.append("atelectasis")
    if rng.random() < 0.18: feats.append("pleural_inv_suspected")
    chest_wall_inv = rng.random() < 0.08 and lobe in ("RLL","LLL")
    if chest_wall_inv: feats.append("chest_wall_invasion")
    p = Primary(lobe=lobe, size_mm=size, features=feats)
    # airway flags for T
    main_bronchus = rng.random() < 0.07 and lobe in ("RUL","RML","RLL")  # crude
    carina_inv = rng.random() < 0.02
    sep_same = rng.random() < 0.06
    sep_other = rng.random() < 0.04
    diaphragm_inv = rng.random() < 0.03 and lobe in ("RLL","LLL")
    tcat, treasons = t_category(size, chest_wall_inv, main_bronchus, carina_inv, sep_same, sep_other, diaphragm_inv)
    return p, treasons

def sample_nodes(stage_hint: Optional[str], rng: random.Random) -> Tuple[List[Node], List[str]]:
    nodes = []
    if stage_hint in ("I",) and rng.random() < 0.85:
        return [], ["No pathologically enlarged lymph nodes by size criteria"]
    # expected number of nodes
    n_ct = 0
    if stage_hint in ("II","III"): n_ct = rng.randint(1, 3)
    if stage_hint == "IV": n_ct = rng.randint(0, 2)
    
    # Ensure unique stations
    available_stations = list(NODE_STATIONS)  # Create a copy to avoid modifying the original
    for _ in range(n_ct):
        if not available_stations:  # If we run out of unique stations, stop
            break
        st = rng.choice(available_stations)
        available_stations.remove(st)  # Remove to ensure uniqueness
        sz = rng.randint(8, 18)  # mix of subcm and enlarged
        nodes.append(Node(station=st, short_axis_mm=sz))
    ncat, nreasons = n_category(nodes)
    return nodes, nreasons

def sample_mets(stage_hint: Optional[str], rng: random.Random) -> Tuple[List[Met], List[str]]:
    mets = []
    if stage_hint in ("I","II") and rng.random() < 0.93:
        return [], ["No definite distant metastases identified"]
    if stage_hint == "III" and rng.random() < 0.85:
        return [], ["No definite distant metastases identified"]
    # otherwise add 1–2 mets with unique sites
    num_mets = rng.randint(1, 2)
    available_sites = list(MET_SITES)  # Create a copy to avoid modifying the original
    for _ in range(num_mets):
        if not available_sites:  # If we run out of unique sites, stop
            break
        site = rng.choice(available_sites)
        available_sites.remove(site)  # Remove to ensure uniqueness
        size = rng.randint(6, 28)
        mets.append(Met(site=site, size_mm=size))
    mcat, mreasons = m_category(mets)
    return mets, mreasons

def stage_hint_from_dist(dist: Dict[str, float], rng: random.Random) -> str:
    # dist like {"I":0.25, "II":0.3, "III":0.3, "IV":0.15}
    r = rng.random()
    acc = 0.0
    for k in ("I","II","III","IV"):
        acc += dist.get(k, 0.0)
        if r <= acc:
            return k
    return "III"

def synth_compare_date(rng: random.Random) -> str:
    base = datetime.date.today() - datetime.timedelta(days=rng.randint(20, 420))
    return base.isoformat()

def artifact_line(rng: random.Random) -> Optional[str]:
    if rng.random() < 0.5:
        return rng.choice(ARTIFACTS)
    return None

def format_primary(p: Primary) -> str:
    side = SIDE_FROM_LOBE[p.lobe]
    phrases = []
    feat_texts = []
    for f in p.features:
        feat_texts.extend(PRIMARY_FEATURE_PHRASES.get(f, []))
    if feat_texts:
        feat_str = " ".join(random.sample(feat_texts, k=min(2, len(feat_texts))))
    else:
        feat_str = "smooth margins"
    return f"{p.size_mm} mm {side} lobe mass with {feat_str}."

def format_nodes(nodes: List[Node]) -> List[str]:
    lines = []
    if not nodes:
        lines = ["No pathologically enlarged lymph nodes by size criteria."]
        return lines
    
    # Group nodes by station to avoid duplicate station descriptions
    station_groups = {}
    for nd in nodes:
        if nd.station not in station_groups:
            station_groups[nd.station] = []
        station_groups[nd.station].append(nd)
    
    # Format each station group
    for station, station_nodes in station_groups.items():
        if len(station_nodes) == 1:
            # Single node at this station
            nd = station_nodes[0]
            templ = random.choice(NODE_PHRASES)
            lines.append(templ.format(station=nd.station, size=nd.short_axis_mm))
        else:
            # Multiple nodes at the same station (shouldn't happen with current logic, but handle gracefully)
            sizes = [nd.short_axis_mm for nd in station_nodes]
            size_str = ", ".join(f"{size} mm" for size in sizes)
            lines.append(f"Multiple {station} lymph nodes measuring {size_str} in short-axis.")
    
    return lines

def format_mets(mets: List[Met]) -> List[str]:
    lines = []
    if not mets:
        lines = ["No definite distant metastases identified."]
        return lines
    
    # Group metastases by site to avoid duplicate site descriptions
    site_groups = {}
    for m in mets:
        if m.site not in site_groups:
            site_groups[m.site] = []
        site_groups[m.site].append(m)
    
    # Format each site group
    for site, site_mets in site_groups.items():
        if len(site_mets) == 1:
            # Single metastasis at this site
            m = site_mets[0]
            templs = MET_PHRASES.get(m.site, ["Indeterminate lesion {size} mm."])
            lines.append(random.choice(templs).format(size=m.size_mm))
        else:
            # Multiple metastases at the same site (shouldn't happen with current logic, but handle gracefully)
            # Since templates expect {size}, we'll use the largest size and add a note
            largest_size = max(m.size_mm for m in site_mets)
            templs = MET_PHRASES.get(site, ["Indeterminate lesion {size} mm."])
            base_line = random.choice(templs).format(size=largest_size)
            if len(site_mets) > 1:
                base_line += f" Additional {len(site_mets)-1} similar lesions at this site."
            lines.append(base_line)
    
    return lines

def generate_accession_number(rng: random.Random) -> str:
    """Generate a unique accession number"""
    # Format: YYYYMMDD + 6 random digits
    year = rng.randint(2020, 2025)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    random_digits = rng.randint(100000, 999999)
    return f"{year}{month:02d}{day:02d}{random_digits}"

def generate_case(seed: int = 0, stage_dist: Dict[str,float] | None = None, lobe: Optional[str] = None, prior_therapy: Optional[List[str]] = None, patient_id: Optional[str] = None, visit_number: int = 1, radiologist_style: Optional[str] = None, radlex_complexity: Optional[str] = None) -> Case:
    rng = random.Random(seed)
    stage_dist = stage_dist or {"I":0.25, "II":0.25, "III":0.30, "IV":0.20}
    hint = stage_hint_from_dist(stage_dist, rng)
    
    # Generate accession number
    accession_number = generate_accession_number(rng)
    
    # Choose radiologist style if not specified
    if radiologist_style is None:
        radiologist_style = rng.choice(list(RADIOLOGIST_STYLES.keys()))
    
    # For baseline study (visit_number=1), no comparison date
    # For follow-up studies, generate a comparison date
    comparison_date = None if visit_number == 1 else synth_compare_date(rng)
    
    meta = Meta(
        comparison_date=comparison_date, 
        prior_therapy=prior_therapy or ([] if rng.random()<0.7 else ["chemoradiation"]),
        patient_id=patient_id,
        visit_number=visit_number,
        accession_number=accession_number,
        radiologist_style=radiologist_style,
        radlex_complexity=radlex_complexity
    )
    primary, t_reasons = sample_primary(lobe, hint, rng)
    nodes, n_reasons = sample_nodes(hint, rng)
    mets, m_reasons = sample_mets(hint, rng)
    T, _ = t_category(primary.size_mm, "chest_wall_invasion" in primary.features, False, False, False, False, False)
    N, _ = n_category(nodes)
    M, _ = m_category(mets)
    stage = stage_group(T,N,M)
    rationale = []
    rationale.extend(t_reasons); rationale.extend(n_reasons); rationale.extend(m_reasons)
    tnm = TNM(T=T, N=N, M=M, stage_group=stage)
    return Case(meta=meta, primary=primary, nodes=nodes, mets=mets, tnm=tnm, rationale=rationale)

def determine_response_status(baseline_case: Case, follow_up_case: Case) -> str:
    """Determine response status based on changes from baseline to follow-up"""
    if not baseline_case.primary or not follow_up_case.primary:
        return "SD"  # Stable disease if no primary to compare
    
    # Calculate size change
    size_change_pct = ((follow_up_case.primary.size_mm - baseline_case.primary.size_mm) / baseline_case.primary.size_mm) * 100
    
    # Count nodes and mets changes
    baseline_nodes = len(baseline_case.nodes)
    follow_up_nodes = len(follow_up_case.nodes)
    baseline_mets = len(baseline_case.mets)
    follow_up_mets = len(follow_up_case.mets)
    
    # RECIST criteria (simplified)
    if size_change_pct <= -30 and follow_up_nodes <= baseline_nodes and follow_up_mets <= baseline_mets:
        return "PR"  # Partial Response
    elif size_change_pct >= 20 or follow_up_nodes > baseline_nodes or follow_up_mets > baseline_mets:
        return "PD"  # Progressive Disease
    elif size_change_pct <= -100:  # Complete disappearance
        return "CR"  # Complete Response
    else:
        return "SD"  # Stable Disease

def generate_follow_up_case(baseline_case: Case, seed: int, days_later: int = 90, radlex_complexity: Optional[str] = None) -> Case:
    """Generate a follow-up case based on the baseline case"""
    rng = random.Random(seed)
    
    # Generate study date (current date for this study)
    study_date = datetime.datetime.now() - datetime.timedelta(days=rng.randint(0, 365))
    
    # For follow-up studies, the comparison date should be the date of the previous study
    # Since baseline has no comparison date, we'll use the study date as comparison
    comparison_date = study_date.strftime("%Y-%m-%d")
    
    # Generate new accession number
    accession_number = generate_accession_number(rng)
    
    # Choose radiologist style
    radiologist_style = rng.choice(list(RADIOLOGIST_STYLES.keys()))
    
    # Create new meta with follow-up info
    meta = Meta(
        comparison_date=comparison_date,
        prior_therapy=baseline_case.meta.prior_therapy + ["chemotherapy", "immunotherapy"],
        patient_id=baseline_case.meta.patient_id,
        visit_number=baseline_case.meta.visit_number + 1,
        accession_number=accession_number,
        radiologist_style=radiologist_style,
        radlex_complexity=radlex_complexity
    )
    
    # Determine response type
    response_type = rng.choices(["PR", "SD", "PD", "CR"], weights=[0.3, 0.4, 0.2, 0.1])[0]
    
    # Modify the primary tumor based on response probability
    if baseline_case.primary:
        if response_type == "CR":
            # Complete response - no primary tumor
            primary = None
        elif response_type == "PR":
            # Partial response - reduce size by 30-70%
            reduction = rng.uniform(0.3, 0.7)
            new_size = max(5, int(baseline_case.primary.size_mm * (1 - reduction)))
            primary = Primary(
                lobe=baseline_case.primary.lobe,
                size_mm=new_size,
                features=baseline_case.primary.features[:rng.randint(0, len(baseline_case.primary.features))]
            )
        elif response_type == "PD":
            # Progressive disease - increase size by 20-50%
            increase = rng.uniform(0.2, 0.5)
            new_size = int(baseline_case.primary.size_mm * (1 + increase))
            primary = Primary(
                lobe=baseline_case.primary.lobe,
                size_mm=new_size,
                features=baseline_case.primary.features + (["cavitation"] if rng.random() < 0.3 else [])
            )
        else:  # SD
            # Stable disease - minimal change
            change = rng.uniform(-0.1, 0.1)
            new_size = max(5, int(baseline_case.primary.size_mm * (1 + change)))
            primary = Primary(
                lobe=baseline_case.primary.lobe,
                size_mm=new_size,
                features=baseline_case.primary.features
            )
    else:
        primary = None
    
    # Modify nodes and mets based on response
    nodes = []
    mets = []
    
    # Simplified node/mets changes based on response
    if response_type in ["PR", "CR"]:
        # Reduce or eliminate nodes/mets
        nodes = baseline_case.nodes[:rng.randint(0, len(baseline_case.nodes)//2)]
        mets = baseline_case.mets[:rng.randint(0, len(baseline_case.mets)//2)]
    elif response_type == "PD":
        # Increase nodes/mets
        nodes = baseline_case.nodes + [Node(station=rng.choice(NODE_STATIONS), short_axis_mm=rng.randint(8, 18)) for _ in range(rng.randint(0, 2))]
        mets = baseline_case.mets + [Met(site=rng.choice(MET_SITES), size_mm=rng.randint(6, 28)) for _ in range(rng.randint(0, 1))]
    else:  # SD
        # Minimal changes
        nodes = baseline_case.nodes
        mets = baseline_case.mets
    
    # Recalculate TNM
    if primary:
        T, _ = t_category(primary.size_mm, "chest_wall_invasion" in primary.features, False, False, False, False, False)
    else:
        T = "T0"
    N, _ = n_category(nodes)
    M, _ = m_category(mets)
    stage = stage_group(T, N, M)
    tnm = TNM(T=T, N=N, M=M, stage_group=stage)
    
    # Determine actual response status
    response_status = determine_response_status(baseline_case, Case(meta=meta, primary=primary, nodes=nodes, mets=mets, tnm=tnm, rationale=[]))
    
    return Case(meta=meta, primary=primary, nodes=nodes, mets=mets, tnm=tnm, rationale=[], response_status=response_status)

def generate_follow_up_case_with_date(baseline_case: Case, seed: int, study_date: datetime.datetime, comparison_date: str, response_dist: Dict[str,float] = None, radlex_complexity: Optional[str] = None) -> Case:
    """Generate a follow-up case with specific study and comparison dates"""
    rng = random.Random(seed)
    
    # Generate new accession number
    accession_number = generate_accession_number(rng)
    
    # Choose radiologist style
    radiologist_style = rng.choice(list(RADIOLOGIST_STYLES.keys()))
    
    # Create new meta with follow-up info
    meta = Meta(
        comparison_date=comparison_date,
        prior_therapy=baseline_case.meta.prior_therapy + ["chemotherapy", "immunotherapy"],
        patient_id=baseline_case.meta.patient_id,
        visit_number=baseline_case.meta.visit_number + 1,
        accession_number=accession_number,
        radiologist_style=radiologist_style,
        radlex_complexity=radlex_complexity
    )
    
    # Determine response type based on distribution
    if response_dist:
        response_types = list(response_dist.keys())
        weights = list(response_dist.values())
        response_type = rng.choices(response_types, weights=weights)[0]
    else:
        # Default distribution
        response_type = rng.choices(["PR", "SD", "PD", "CR"], weights=[0.3, 0.4, 0.2, 0.1])[0]
    
    # Modify the primary tumor based on response probability
    if baseline_case.primary:
        if response_type == "CR":
            # Complete response - no primary tumor
            primary = None
        elif response_type == "PR":
            # Partial response - reduce size by 30-70%
            reduction = rng.uniform(0.3, 0.7)
            new_size = max(5, int(baseline_case.primary.size_mm * (1 - reduction)))
            primary = Primary(
                lobe=baseline_case.primary.lobe,
                size_mm=new_size,
                features=baseline_case.primary.features[:rng.randint(0, len(baseline_case.primary.features))]
            )
        elif response_type == "PD":
            # Progressive disease - increase size by 20-50%
            increase = rng.uniform(0.2, 0.5)
            new_size = int(baseline_case.primary.size_mm * (1 + increase))
            primary = Primary(
                lobe=baseline_case.primary.lobe,
                size_mm=new_size,
                features=baseline_case.primary.features + (["cavitation"] if rng.random() < 0.3 else [])
            )
        else:  # SD
            # Stable disease - minimal change
            change = rng.uniform(-0.1, 0.1)
            new_size = max(5, int(baseline_case.primary.size_mm * (1 + change)))
            primary = Primary(
                lobe=baseline_case.primary.lobe,
                size_mm=new_size,
                features=baseline_case.primary.features
            )
    else:
        primary = None
    
    # Modify nodes and mets based on response
    nodes = []
    mets = []
    
    # Simplified node/mets changes based on response
    if response_type in ["PR", "CR"]:
        # Reduce or eliminate nodes/mets
        nodes = baseline_case.nodes[:rng.randint(0, len(baseline_case.nodes)//2)]
        mets = baseline_case.mets[:rng.randint(0, len(baseline_case.mets)//2)]
    elif response_type == "PD":
        # Increase nodes/mets
        nodes = baseline_case.nodes + [Node(station=rng.choice(NODE_STATIONS), short_axis_mm=rng.randint(8, 18)) for _ in range(rng.randint(0, 2))]
        mets = baseline_case.mets + [Met(site=rng.choice(MET_SITES), size_mm=rng.randint(6, 28)) for _ in range(rng.randint(0, 1))]
    else:  # SD
        # Minimal changes
        nodes = baseline_case.nodes
        mets = baseline_case.mets
    
    # Recalculate TNM
    if primary:
        T, _ = t_category(primary.size_mm, "chest_wall_invasion" in primary.features, False, False, False, False, False)
    else:
        T = "T0"
    N, _ = n_category(nodes)
    M, _ = m_category(mets)
    stage = stage_group(T, N, M)
    tnm = TNM(T=T, N=N, M=M, stage_group=stage)
    
    # Determine actual response status
    response_status = determine_response_status(baseline_case, Case(meta=meta, primary=primary, nodes=nodes, mets=mets, tnm=tnm, rationale=[]))
    
    return Case(meta=meta, primary=primary, nodes=nodes, mets=mets, tnm=tnm, rationale=[], response_status=response_status)

def generate_patient_timeline(patient_id: str, seed: int, stage_dist: Dict[str,float], lobe: Optional[str] = None, max_studies: int = 5, response_dist: Dict[str,float] = None, radlex_dist: Dict[str,float] = None) -> tuple[List[Case], List[datetime.datetime]]:
    """Generate a complete timeline of studies for a single patient"""
    rng = random.Random(seed)
    
    # Randomly choose number of follow-up studies (1 to max_studies)
    num_follow_ups = rng.randint(1, max_studies)
    total_studies = 1 + num_follow_ups  # baseline + follow-ups
    
    # Generate baseline case (no comparison date)
    # Select RadLex config for baseline case
    radlex_config = select_radlex_config(radlex_dist, rng) if radlex_dist else None
    baseline_case = generate_case(
        seed=rng.randint(0, 10_000_000),
        stage_dist=stage_dist,
        lobe=lobe,
        patient_id=patient_id,
        visit_number=1,
        radlex_complexity=radlex_config
    )
    
    cases = [baseline_case]
    current_case = baseline_case
    
    # Track study dates for proper comparison
    study_dates = []
    baseline_date = datetime.datetime.now() - datetime.timedelta(days=rng.randint(365, 730))  # 1-2 years ago
    study_dates.append(baseline_date)
    
    # Generate follow-up studies
    for visit_num in range(2, total_studies + 1):
        # Random interval between studies (30-180 days)
        days_interval = rng.randint(30, 180)
        
        # Calculate new study date
        new_study_date = study_dates[-1] + datetime.timedelta(days=days_interval)
        study_dates.append(new_study_date)
        
        # Generate follow-up case with proper comparison date
        # Select RadLex config for follow-up case
        radlex_config = select_radlex_config(radlex_dist, rng) if radlex_dist else None
        follow_up_case = generate_follow_up_case_with_date(
            current_case,
            seed=rng.randint(0, 10_000_000),
            study_date=new_study_date,
            comparison_date=study_dates[-2].strftime("%Y-%m-%d"),  # Previous study date
            response_dist=response_dist,
            radlex_complexity=radlex_config
        )
        
        # Update visit number and patient ID
        follow_up_case.meta.visit_number = visit_num
        follow_up_case.meta.patient_id = patient_id
        
        cases.append(follow_up_case)
        current_case = follow_up_case
    
    return cases, study_dates

def generate_report(case: Case, radlex_config: Optional[str] = None) -> str:
    lines = []
    lines.append("FINDINGS:")
    
    # Initialize RadLex lexicons if config provided
    radlex_lexicons = None
    if radlex_config and radlex_config in PREDEFINED_CONFIGS:
        try:
            config = PREDEFINED_CONFIGS[radlex_config]
            radlex_lexicons = get_radlex_lexicons(
                use_radlex=True,
                rate_limit_per_second=config.rate_limit_per_second,
                rate_limit_per_minute=config.rate_limit_per_minute
            )
        except Exception as e:
            print(f"Warning: RadLex unavailable, using standard lexicons: {e}")
            radlex_lexicons = None
    
    # Use radiologist-specific artifact phrases
    if case.meta.radiologist_style and case.meta.radiologist_style in RADIOLOGIST_STYLES:
        style = RADIOLOGIST_STYLES[case.meta.radiologist_style]
        if random.random() < 0.5:
            artifact_phrase = random.choice(style["artifact_phrases"])
            # Enhance artifact phrase with RadLex if available
            if radlex_lexicons:
                artifact_phrase = radlex_lexicons.enhance_text_with_radlex(artifact_phrase)
            lines.append(artifact_phrase)
    else:
        art = artifact_line(random.Random())
        if art:
            # Enhance artifact line with RadLex if available
            if radlex_lexicons:
                art = radlex_lexicons.enhance_text_with_radlex(art)
            lines.append(art)
    
    # Only add comparison line if there's a comparison date
    if case.meta.comparison_date:
        lines.append(f"Comparison: {case.meta.comparison_date}.")
    # Lungs
    lines.append("Lungs:")
    if case.primary:
        primary_text = format_primary(case.primary)
        # Enhance primary tumor description with RadLex if available
        if radlex_lexicons:
            primary_text = radlex_lexicons.enhance_text_with_radlex(primary_text)
        lines.append("  " + primary_text)
    else:
        clear_lungs_text = "Clear lungs without focal mass or suspicious nodules."
        # Enhance with RadLex if available
        if radlex_lexicons:
            clear_lungs_text = radlex_lexicons.enhance_text_with_radlex(clear_lungs_text)
        lines.append("  " + clear_lungs_text)
    # Nodes
    lines.append("Lymph nodes:")
    for ln in format_nodes(case.nodes):
        # Enhance lymph node description with RadLex if available
        if radlex_lexicons:
            ln = radlex_lexicons.enhance_text_with_radlex(ln)
        lines.append("  " + ln)
    # Pleura/pleural spaces
    lines.append("Pleura/Pleural spaces: No pleural effusion. ")
    
    # Use radiologist-specific normal findings
    if case.meta.radiologist_style and case.meta.radiologist_style in RADIOLOGIST_STYLES:
        style = RADIOLOGIST_STYLES[case.meta.radiologist_style]
        lines.append("Mediastinum: " + random.choice(style["normal_mediastinum"]))
        lines.append("Great vessels/Aorta: " + random.choice(style["normal_great_vessels"]))
        lines.append("Upper abdomen (limited): " + random.choice(style["normal_abdomen"]))
        lines.append("Bones/Osseous structures: " + random.choice(style["normal_bones"]))
    else:
        # Fallback to original style
        lines.append("Mediastinum: " + random.choice(NORMAL_BETS["mediastinum"]))
        lines.append("Great vessels/Aorta: " + random.choice(NORMAL_BETS["great_vessels"]))
        lines.append("Upper abdomen (limited): " + random.choice(NORMAL_BETS["abdomen_incidental"]))
        lines.append("Bones/Osseous structures: No acute fracture. No aggressive osseous lesion identified on CT field-of-view.")
    
    # Mets statements if present
    for met_line in format_mets(case.mets):
        lines.append("Metastatic survey: " + met_line)
    # Impression
    lines.append("")
    lines.append("IMPRESSION:")
    if case.primary:
        side = SIDE_FROM_LOBE[case.primary.lobe].split()[0]
        impression_text = f"- Primary lung neoplasm in the {SIDE_FROM_LOBE[case.primary.lobe]} lobe measuring approximately {case.primary.size_mm} mm."
        # Enhance impression with RadLex if available
        if radlex_lexicons:
            impression_text = radlex_lexicons.enhance_text_with_radlex(impression_text)
        lines.append(impression_text)
    if case.nodes:
        nodal_text = "- Nodal disease as detailed above."
        # Enhance with RadLex if available
        if radlex_lexicons:
            nodal_text = radlex_lexicons.enhance_text_with_radlex(nodal_text)
        lines.append(nodal_text)
    else:
        no_nodes_text = "- No pathologically enlarged lymph nodes by size criteria."
        # Enhance with RadLex if available
        if radlex_lexicons:
            no_nodes_text = radlex_lexicons.enhance_text_with_radlex(no_nodes_text)
        lines.append(no_nodes_text)
    if case.mets:
        mets_text = "- Findings suspicious for distant metastatic disease as above."
        # Enhance with RadLex if available
        if radlex_lexicons:
            mets_text = radlex_lexicons.enhance_text_with_radlex(mets_text)
        lines.append(mets_text)
    else:
        no_mets_text = "- No definite distant metastases identified."
        # Enhance with RadLex if available
        if radlex_lexicons:
            no_mets_text = radlex_lexicons.enhance_text_with_radlex(no_mets_text)
        lines.append(no_mets_text)
    # TNM and Response Status lines removed for cleaner reports
    
    return "\n".join(lines)

def write_case(case: Case, outdir: str, stem: str, radlex_config: Optional[str] = None):
    # Create hierarchical folder structure: patient_id/study_visit_number/
    if case.meta.patient_id:
        patient_dir = os.path.join(outdir, case.meta.patient_id)
        study_dir = os.path.join(patient_dir, f"study_{case.meta.visit_number:02d}")
        os.makedirs(study_dir, exist_ok=True)
        
        # Use accession number in filename if available
        if case.meta.accession_number:
            filename = f"{case.meta.accession_number}"
        else:
            filename = stem
    else:
        # Fallback to original behavior
        os.makedirs(outdir, exist_ok=True)
        study_dir = outdir
        filename = stem
    
    report = generate_report(case, radlex_config)
    
    # Write both TXT and JSON files
    txt_path = os.path.join(study_dir, f"{filename}.txt")
    json_path = os.path.join(study_dir, f"{filename}.json")
    
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(case.model_dump(), f, indent=2)

def parse_stage_dist(arg: str) -> Dict[str,float]:
    # I:0.2,II:0.25,III:0.35,IV:0.2
    parts = [p for p in arg.split(',') if p]
    out = {}
    for p in parts:
        k,v = p.split(':')
        out[k.strip()] = float(v)
    s = sum(out.values())
    if s <= 0: raise ValueError("stage distribution must sum > 0")
    # normalize
    for k in out:
        out[k] /= s
    return out

def parse_response_dist(arg: str) -> Dict[str,float]:
    # CR:0.1,PR:0.3,SD:0.4,PD:0.2
    parts = [p for p in arg.split(',') if p]
    out = {}
    for p in parts:
        k,v = p.split(':')
        out[k.strip()] = float(v)
    s = sum(out.values())
    if s <= 0: raise ValueError("response distribution must sum > 0")
    # normalize
    for k in out:
        out[k] /= s
    return out

def parse_radlex_dist(arg: str) -> Dict[str,float]:
    # minimal:0.2,standard:0.5,aggressive:0.2,conservative:0.1
    parts = [p for p in arg.split(',') if p]
    out = {}
    for p in parts:
        k,v = p.split(':')
        config_name = k.strip()
        if config_name not in PREDEFINED_CONFIGS:
            raise ValueError(f"Unknown RadLex config: {config_name}. Available: {list(PREDEFINED_CONFIGS.keys())}")
        out[config_name] = float(v)
    s = sum(out.values())
    if s <= 0: raise ValueError("RadLex distribution must sum > 0")
    # normalize
    for k in out:
        out[k] /= s
    return out

def select_radlex_config(radlex_dist: Dict[str, float], rng: random.Random) -> Optional[str]:
    """Select a RadLex configuration based on the distribution."""
    if not radlex_dist:
        return None
    
    # Convert to cumulative distribution
    configs = list(radlex_dist.keys())
    probs = list(radlex_dist.values())
    
    # Select based on probability
    rand_val = rng.random()
    cumulative = 0
    for config, prob in zip(configs, probs):
        cumulative += prob
        if rand_val <= cumulative:
            return config
    
    # Fallback to last config
    return configs[-1] if configs else None

def case_to_recist_jsonl(cases: List[Case], study_dates: List[datetime.datetime] = None) -> List[dict]:
    """Convert generated cases to JSONL format for the React app"""
    jsonl_data = []
    
    for i, case in enumerate(cases):
        # Calculate SLD (Sum of Longest Diameters) for target lesions
        sld_mm = 0
        lesions = []
        
        # Add primary tumor as target lesion
        if case.primary:
            sld_mm += case.primary.size_mm
            lesions.append({
                "lesion_id": f"primary_{case.primary.lobe}",
                "kind": "primary",
                "organ": "lung",
                "location": case.primary.lobe,
                "rule": "longest",
                "baseline_mm": case.primary.size_mm if case.meta.visit_number == 1 else None,
                "follow_mm": case.primary.size_mm if case.meta.visit_number > 1 else None,
                "size_mm_current": case.primary.size_mm,
                "margin": "spiculated" if "spiculation" in case.primary.features else "smooth",
                "enhancement": "enhancing",
                "necrosis": "cavitation" in case.primary.features,
                "suspicious": True,
                "target": True
            })
        
        # Add lymph nodes as target lesions (if short axis >= 10mm)
        for j, node in enumerate(case.nodes):
            if node.short_axis_mm >= 10:  # Target lesions are >= 10mm
                sld_mm += node.short_axis_mm
                lesions.append({
                    "lesion_id": f"ln_{node.station}_{j}",
                    "kind": "ln",
                    "organ": "lymph_node",
                    "station": node.station,
                    "rule": "short_axis",
                    "baseline_mm": node.short_axis_mm if case.meta.visit_number == 1 else None,
                    "follow_mm": node.short_axis_mm if case.meta.visit_number > 1 else None,
                    "size_mm_current": node.short_axis_mm,
                    "margin": "smooth",
                    "enhancement": "enhancing",
                    "necrosis": False,
                    "suspicious": True,
                    "target": True
                })
            else:
                # Non-target lesions
                lesions.append({
                    "lesion_id": f"ln_{node.station}_{j}",
                    "kind": "ln",
                    "organ": "lymph_node",
                    "station": node.station,
                    "rule": "short_axis",
                    "baseline_mm": node.short_axis_mm if case.meta.visit_number == 1 else None,
                    "follow_mm": node.short_axis_mm if case.meta.visit_number > 1 else None,
                    "size_mm_current": node.short_axis_mm,
                    "margin": "smooth",
                    "enhancement": "enhancing",
                    "necrosis": False,
                    "suspicious": True,
                    "target": False
                })
        
        # Add metastases as target lesions (if size >= 10mm)
        for j, met in enumerate(case.mets):
            if met.size_mm >= 10:  # Target lesions are >= 10mm
                sld_mm += met.size_mm
                lesions.append({
                    "lesion_id": f"met_{met.site}_{j}",
                    "kind": "met",
                    "organ": met.site,
                    "location": met.site,
                    "rule": "longest",
                    "baseline_mm": met.size_mm if case.meta.visit_number == 1 else None,
                    "follow_mm": met.size_mm if case.meta.visit_number > 1 else None,
                    "size_mm_current": met.size_mm,
                    "margin": "smooth",
                    "enhancement": "enhancing",
                    "necrosis": False,
                    "suspicious": True,
                    "target": True
                })
            else:
                # Non-target lesions
                lesions.append({
                    "lesion_id": f"met_{met.site}_{j}",
                    "kind": "met",
                    "organ": met.site,
                    "location": met.site,
                    "rule": "longest",
                    "baseline_mm": met.size_mm if case.meta.visit_number == 1 else None,
                    "follow_mm": met.size_mm if case.meta.visit_number > 1 else None,
                    "size_mm_current": met.size_mm,
                    "margin": "smooth",
                    "enhancement": "enhancing",
                    "necrosis": False,
                    "suspicious": True,
                    "target": False
                })
        
        # Use provided study dates or generate them
        if study_dates and i < len(study_dates):
            study_date = study_dates[i].strftime("%Y-%m-%d")
        else:
            # Fallback: generate study date
            if case.meta.visit_number == 1:
                study_date = (datetime.datetime.now() - datetime.timedelta(days=random.randint(365, 730))).strftime("%Y-%m-%d")
            else:
                baseline_days_ago = random.randint(365, 730)
                follow_up_days_ago = baseline_days_ago - (case.meta.visit_number - 1) * random.randint(30, 180)
                study_date = (datetime.datetime.now() - datetime.timedelta(days=follow_up_days_ago)).strftime("%Y-%m-%d")
        
        # Create the JSONL entry
        entry = {
            "patient_id": case.meta.patient_id,
            "timepoint": case.meta.visit_number - 1,  # 0 = baseline, 1 = first follow-up, etc.
            "study_date": study_date,
            "baseline_sld_mm": sld_mm if case.meta.visit_number == 1 else None,
            "current_sld_mm": sld_mm if case.meta.visit_number > 1 else None,
            "nadir_sld_mm": None,  # Would need to be calculated across timeline
            "overall_response": case.response_status or "SD",
            "lesions": lesions
        }
        
        jsonl_data.append(entry)
    
    return jsonl_data

def main():
    ap = argparse.ArgumentParser(description="Generate synthetic lung cancer CT reports with TNM-aware details.")
    ap.add_argument("--n", type=int, default=5, help="Number of patients to generate")
    ap.add_argument("--out", type=str, default="./out", help="Output directory")
    ap.add_argument("--seed", type=int, default=0, help="Random seed (deterministic)")
    ap.add_argument("--lobe", type=str, default=None, choices=[None,"RUL","RML","RLL","LUL","LLL"], help="Force primary lobe (optional)")
    ap.add_argument("--stage-dist", type=str, default="I:0.25,II:0.25,III:0.30,IV:0.20", help="Stage distribution e.g. I:0.2,II:0.25,III:0.35,IV:0.2 (will be normalized)")
    ap.add_argument("--follow-up", action="store_true", help="Generate follow-up cases for each baseline case")
    ap.add_argument("--follow-up-days", type=int, default=90, help="Days between baseline and follow-up (default: 90)")
    ap.add_argument("--studies-per-patient", type=int, default=5, help="Maximum number of studies per patient (2-10, default: 5). Each patient will have 1 baseline + 1-{max} follow-up studies")
    ap.add_argument("--response-dist", type=str, default="CR:0.1,PR:0.3,SD:0.4,PD:0.2", help="Response distribution e.g. CR:0.1,PR:0.3,SD:0.4,PD:0.2 (will be normalized)")
    ap.add_argument("--radlex-dist", type=str, default="standard:1.0", help="RadLex configuration distribution e.g. minimal:0.2,standard:0.5,aggressive:0.2,conservative:0.1 (will be normalized)")
    ap.add_argument("--legacy-mode", action="store_true", help="Use legacy flat file structure")
    ap.add_argument("--jsonl", type=str, default=None, help="Output JSONL file for React app (e.g., cohort_labels.jsonl)")
    args = ap.parse_args()

    # Validate studies per patient
    if args.studies_per_patient < 2 or args.studies_per_patient > 10:
        print("Error: studies-per-patient must be between 2 and 10")
        return

    rng = random.Random(args.seed)
    dist = parse_stage_dist(args.stage_dist)
    response_dist = parse_response_dist(args.response_dist)
    radlex_dist = parse_radlex_dist(args.radlex_dist)
    
    # Collect all cases for JSONL output if requested
    all_cases = []
    all_study_dates = []
    
    for i in range(args.n):
        patient_id = f"P{i:04d}"
        
        if args.legacy_mode:
            # Legacy mode: generate baseline and optional follow-up
            # Select RadLex config for this case
            radlex_config = select_radlex_config(radlex_dist, rng)
            
            baseline_case = generate_case(
                seed=rng.randint(0,10_000_000), 
                stage_dist=dist, 
                lobe=args.lobe,
                patient_id=patient_id,
                visit_number=1,
                radlex_complexity=radlex_config
            )
            write_case(baseline_case, args.out, f"{patient_id}_baseline", radlex_config)
            
            if args.follow_up:
                follow_up_case = generate_follow_up_case(
                    baseline_case, 
                    seed=rng.randint(0,10_000_000),
                    days_later=args.follow_up_days,
                    radlex_complexity=radlex_config
                )
                write_case(follow_up_case, args.out, f"{patient_id}_followup", radlex_config)
        else:
            # New mode: generate complete patient timeline
            cases, study_dates = generate_patient_timeline(
                patient_id=patient_id,
                seed=rng.randint(0, 10_000_000),
                stage_dist=dist,
                lobe=args.lobe,
                max_studies=args.studies_per_patient,
                response_dist=response_dist,
                radlex_dist=radlex_dist
            )
            
            # Write all cases for this patient (RadLex config already selected per case)
            for case in cases:
                write_case(case, args.out, case.meta.accession_number, case.meta.radlex_complexity)
            
            # Collect for JSONL output
            all_cases.extend(cases)
            all_study_dates.extend(study_dates)
    
    # Create JSONL file if requested
    if args.jsonl and all_cases:
        jsonl_data = case_to_recist_jsonl(all_cases, all_study_dates)
        jsonl_path = os.path.join(args.out, args.jsonl)
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for entry in jsonl_data:
                f.write(json.dumps(entry) + "\n")
        print(f"Created JSONL file: {jsonl_path}")

if __name__ == "__main__":
    main()
