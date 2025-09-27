from __future__ import annotations

import argparse, os, random, datetime, json, math
from typing import Dict, List, Optional, Tuple

from .lexicons import (
    LOBES, SIDE_FROM_LOBE, ARTIFACTS, NORMAL_BETS, PRIMARY_FEATURE_PHRASES,
    NODE_STATIONS, NODE_PHRASES, MET_SITES, MET_PHRASES, LIVER_DETAIL_PHRASES,
    RADIOLOGIST_STYLES, PET_PHRASES, TECHNIQUE_CT_CAP, TECHNIQUE_PET_CT,
    mm_desc, node_phrase, fmt_mm, compare_size, recist_overall_response,
    percist_summary, pick, make_rng, feature_text,
    select_recist_targets, calculate_sld, classify_nontarget_lesions,
    RECIST_TARGET_RULES, RECIST_THRESHOLDS
)
from .schema import Case, Meta, Primary, Node, Met, TNM
from .radlex_config import get_config

# --- TNM logic for NSCLC (simplified, IASLC 8th-ish) ---

def t_category(size_mm: int, chest_wall_inv: bool, main_bronchus: bool, carina_inv: bool,
               separate_nodules_same_lobe: bool, separate_nodules_other_ipsi_lobe: bool,
               diaphragm_inv: bool) -> Tuple[str, List[str]]:
    reasons = []
    if carina_inv:
        reasons.append("T4 due to carina involvement")
        return "T4", reasons
    if diaphragm_inv or chest_wall_inv:
        reasons.append("T3 due to chest wall/diaphragm invasion")
        tcat = "T3"
    else:
        if size_mm <= 10:
            tcat = "T1a"; reasons.append("T1a because ≤10 mm")
        elif size_mm <= 20:
            tcat = "T1b"; reasons.append("T1b because >10–20 mm")
        elif size_mm <= 30:
            tcat = "T1c"; reasons.append("T1c because >20–30 mm")
        elif size_mm <= 50:
            tcat = "T2a"; reasons.append("T2a because >30–50 mm")
        elif size_mm <= 70:
            tcat = "T2b"; reasons.append("T2b because >50–70 mm")
        else:
            tcat = "T3"; reasons.append("T3 because >70 mm")
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
    t_major = int(T[1]) if len(T) > 1 and T[1].isdigit() else 4
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
    if stage_hint in ("I","II"):
        size = rng.randint(12, 48)
    elif stage_hint == "III":
        size = rng.randint(25, 75)
    else:
        size = rng.randint(15, 65)
    feats = []
    if rng.random() < 0.55: feats.append("spiculation")
    if rng.random() < 0.12: feats.append("cavitation")
    if rng.random() < 0.22: feats.append("atelectasis")
    if rng.random() < 0.18: feats.append("pleural_inv_suspected")
    chest_wall_inv = rng.random() < 0.08 and lobe in ("RLL","LLL")
    if chest_wall_inv: feats.append("chest_wall_invasion")
    p = Primary(lobe=lobe, size_mm=size, features=feats)
    main_bronchus = rng.random() < 0.07 and lobe in ("RUL","RML","RLL")
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
    n_ct = 0
    if stage_hint in ("II","III"): n_ct = rng.randint(1, 3)
    if stage_hint == "IV": n_ct = rng.randint(0, 2)

    available_stations = list(NODE_STATIONS)
    for _ in range(n_ct):
        if not available_stations:
            break
        st = rng.choice(available_stations); available_stations.remove(st)
        sz = rng.randint(8, 18)
        nodes.append(Node(station=st, short_axis_mm=sz))
    ncat, nreasons = n_category(nodes)
    return nodes, nreasons

def sample_mets(stage_hint: Optional[str], rng: random.Random) -> Tuple[List[Met], List[str]]:
    mets = []
    if stage_hint in ("I","II") and rng.random() < 0.93:
        return [], ["No definite distant metastases identified"]
    if stage_hint == "III" and rng.random() < 0.85:
        return [], ["No definite distant metastases identified"]
    num_mets = rng.randint(1, 2)
    available_sites = list(MET_SITES)
    for _ in range(num_mets):
        if not available_sites:
            break
        site = rng.choice(available_sites); available_sites.remove(site)
        size = rng.randint(6, 28)
        mets.append(Met(site=site, size_mm=size))
    mcat, mreasons = m_category(mets)
    return mets, mreasons

def stage_hint_from_dist(dist: Dict[str, float], rng: random.Random) -> str:
    r = rng.random(); acc = 0.0
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

def format_primary(p: Primary, radiologist_style: str = "concise") -> str:
    side = SIDE_FROM_LOBE[p.lobe]
    feats = feature_text(p.features)  # canonical, de-duplicated
    # normalize style key
    style_key = {"oncology": "oncology_narrative"}.get(radiologist_style, radiologist_style)
    style_dict = RADIOLOGIST_STYLES.get(style_key, RADIOLOGIST_STYLES["detailed"])
    templates = style_dict.get("primary_lesion_phrases", ["{side} pulmonary mass {size} mm with {features}."])
    template = random.choice(templates)
    return template.format(size=p.size_mm, side=side, features=feats)

def format_nodes(nodes: List[Node], radiologist_style: str = "concise") -> List[str]:
    lines = []
    if not nodes:
        return ["No pathologically enlarged lymph nodes by size criteria."]
    station_groups = {}
    for nd in nodes:
        station_groups.setdefault(nd.station, []).append(nd)
    for station, station_nodes in station_groups.items():
        if len(station_nodes) == 1:
            nd = station_nodes[0]
            lines.append(node_phrase(nd.station, nd.short_axis_mm, style=radiologist_style))
        else:
            sizes = [nd.short_axis_mm for nd in station_nodes]
            size_str = ", ".join(f"{size} mm" for size in sizes)
            lines.append(f"Multiple {station} lymph nodes measuring {size_str} in short axis.")
    return lines

def format_mets(mets: List[Met], radiologist_style: str = "concise") -> List[str]:
    lines = []
    if not mets:
        return ["No definite distant metastases identified."]
    site_groups = {}
    for m in mets:
        site_groups.setdefault(m.site, []).append(m)
    for site, site_mets in site_groups.items():
        if len(site_mets) == 1:
            m = site_mets[0]
            if site == "liver":
                lines.append(random.choice(LIVER_DETAIL_PHRASES).format(size=m.size_mm))
            else:
                if radiologist_style in RADIOLOGIST_STYLES and "metastasis_phrases" in RADIOLOGIST_STYLES[radiologist_style]:
                    template = random.choice(RADIOLOGIST_STYLES[radiologist_style]["metastasis_phrases"])
                    site_name = site.replace("_", " ")
                    lines.append(template.format(site=site_name, size=m.size_mm))
                else:
                    templs = MET_PHRASES.get(m.site, ["Indeterminate lesion {size} mm."])
                    lines.append(random.choice(templs).format(size=m.size_mm))
        else:
            largest_size = max(m.size_mm for m in site_mets)
            if site == "liver":
                base_line = random.choice(LIVER_DETAIL_PHRASES).format(size=largest_size)
            elif radiologist_style in RADIOLOGIST_STYLES and "metastasis_phrases" in RADIOLOGIST_STYLES[radiologist_style]:
                template = random.choice(RADIOLOGIST_STYLES[radiologist_style]["metastasis_phrases"])
                base_line = template.format(site=site.replace("_"," "), size=largest_size)
            else:
                templs = MET_PHRASES.get(site, ["Indeterminate lesion {size} mm."])
                base_line = random.choice(templs).format(size=largest_size)
            if len(site_mets) > 1:
                base_line += f" Additional {len(site_mets)-1} similar lesions at this site."
            lines.append(base_line)
    return lines

def generate_accession_number(rng: random.Random) -> str:
    year = rng.randint(2020, 2025)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    random_digits = rng.randint(100000, 999999)
    return f"{year}{month:02d}{day:02d}{random_digits}"

def generate_case(seed: int = 0, stage_dist: Dict[str,float] | None = None, lobe: Optional[str] = None,
                  patient_id: Optional[str] = None, visit_number: int = 1, radiologist_style: Optional[str] = None) -> Case:
    rng = random.Random(seed)
    stage_dist = stage_dist or {"I":0.25, "II":0.25, "III":0.30, "IV":0.20}
    hint = stage_hint_from_dist(stage_dist, rng)
    accession_number = generate_accession_number(rng)

    # Choose one of the three styles by default
    styles = list(RADIOLOGIST_STYLES.keys())
    if radiologist_style is None:
        radiologist_style = rng.choice(styles)

    comparison_date = None if visit_number == 1 else synth_compare_date(rng)

    meta = Meta(
        comparison_date=comparison_date,
        patient_id=patient_id,
        visit_number=visit_number,
        accession_number=accession_number,
        radiologist_style=radiologist_style
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
    """
    Determine RECIST 1.1 response status between baseline and follow-up cases.
    """
    # Get target lesions for both cases
    baseline_targets = select_recist_targets(baseline_case.primary, baseline_case.nodes, baseline_case.mets)
    follow_up_targets = select_recist_targets(follow_up_case.primary, follow_up_case.nodes, follow_up_case.mets)
    
    # Calculate SLD for both cases
    baseline_sld = calculate_sld(baseline_targets)
    follow_up_sld = calculate_sld(follow_up_targets)
    
    # Check for new lesions (simplified - any new lesions in follow-up)
    baseline_lesion_ids = {target["lesion_id"] for target in baseline_targets}
    follow_up_lesion_ids = {target["lesion_id"] for target in follow_up_targets}
    new_lesions = len(follow_up_lesion_ids - baseline_lesion_ids) > 0
    
    # Check for non-target progression (simplified - any new non-target lesions)
    baseline_nontargets = classify_nontarget_lesions(baseline_case.primary, baseline_case.nodes, baseline_case.mets, baseline_targets)
    follow_up_nontargets = classify_nontarget_lesions(follow_up_case.primary, follow_up_case.nodes, follow_up_case.mets, follow_up_targets)
    
    baseline_nontarget_ids = {nt["lesion_id"] for nt in baseline_nontargets}
    follow_up_nontarget_ids = {nt["lesion_id"] for nt in follow_up_nontargets}
    nontarget_progression = len(follow_up_nontarget_ids - baseline_nontarget_ids) > 0
    
    # Use RECIST 1.1 response assessment
    return recist_overall_response(follow_up_sld, baseline_sld, nontarget_progression, new_lesions)

def generate_follow_up_case(baseline_case: Case, seed: int, days_later: int = 90) -> Case:
    rng = random.Random(seed)
    study_date = datetime.datetime.now() - datetime.timedelta(days=rng.randint(0, 365))
    comparison_date = study_date.strftime("%Y-%m-%d")
    accession_number = generate_accession_number(rng)
    radiologist_style = rng.choice(list(RADIOLOGIST_STYLES.keys()))
    meta = Meta(
        comparison_date=comparison_date,
        patient_id=baseline_case.meta.patient_id,
        visit_number=baseline_case.meta.visit_number + 1,
        accession_number=accession_number,
        radiologist_style=radiologist_style
    )
    response_type = rng.choices(["PR", "SD", "PD", "CR"], weights=[0.3, 0.4, 0.2, 0.1])[0]
    if baseline_case.primary:
        if response_type == "CR":
            primary = None
        elif response_type == "PR":
            reduction = rng.uniform(0.3, 0.7)
            new_size = max(5, int(baseline_case.primary.size_mm * (1 - reduction)))
            primary = Primary(
                lobe=baseline_case.primary.lobe,
                size_mm=new_size,
                features=baseline_case.primary.features[:rng.randint(0, len(baseline_case.primary.features))]
            )
        elif response_type == "PD":
            increase = rng.uniform(0.2, 0.5)
            new_size = int(baseline_case.primary.size_mm * (1 + increase))
            primary = Primary(
                lobe=baseline_case.primary.lobe,
                size_mm=new_size,
                features=baseline_case.primary.features + (["cavitation"] if rng.random() < 0.3 else [])
            )
        else:
            change = rng.uniform(-0.1, 0.1)
            new_size = max(5, int(baseline_case.primary.size_mm * (1 + change)))
            primary = Primary(
                lobe=baseline_case.primary.lobe,
                size_mm=new_size,
                features=baseline_case.primary.features
            )
    else:
        primary = None

    nodes = []
    mets = []
    if response_type in ["PR", "CR"]:
        nodes = baseline_case.nodes[:rng.randint(0, max(1, len(baseline_case.nodes)//2))]
        mets = baseline_case.mets[:rng.randint(0, max(1, len(baseline_case.mets)//2))]
    elif response_type == "PD":
        nodes = baseline_case.nodes + [Node(station=rng.choice(NODE_STATIONS), short_axis_mm=rng.randint(8, 18)) for _ in range(rng.randint(0, 2))]
        mets = baseline_case.mets + [Met(site=rng.choice(MET_SITES), size_mm=rng.randint(6, 28)) for _ in range(rng.randint(0, 1))]
    else:
        nodes = baseline_case.nodes
        mets = baseline_case.mets

    if primary:
        T, _ = t_category(primary.size_mm, "chest_wall_invasion" in primary.features, False, False, False, False, False)
    else:
        T = "T0"
    N, _ = n_category(nodes)
    M, _ = m_category(mets)
    stage = stage_group(T, N, M)
    tnm = TNM(T=T, N=N, M=M, stage_group=stage)
    response_status = determine_response_status(baseline_case, Case(meta=meta, primary=primary, nodes=nodes, mets=mets, tnm=tnm, rationale=[]))
    return Case(meta=meta, primary=primary, nodes=nodes, mets=mets, tnm=tnm, rationale=[], response_status=response_status)

def generate_follow_up_case_with_date(baseline_case: Case, seed: int, study_date: datetime.datetime,
                                      comparison_date: str, response_dist: Dict[str,float] = None) -> Case:
    rng = random.Random(seed)
    accession_number = generate_accession_number(rng)
    radiologist_style = rng.choice(list(RADIOLOGIST_STYLES.keys()))
    meta = Meta(
        comparison_date=comparison_date,
        patient_id=baseline_case.meta.patient_id,
        visit_number=baseline_case.meta.visit_number + 1,
        accession_number=accession_number,
        radiologist_style=radiologist_style
    )
    if response_dist:
        response_types = list(response_dist.keys())
        weights = list(response_dist.values())
        response_type = rng.choices(response_types, weights=weights)[0]
    else:
        response_type = rng.choices(["PR", "SD", "PD", "CR"], weights=[0.3, 0.4, 0.2, 0.1])[0]

    if baseline_case.primary:
        if response_type == "CR":
            primary = None
        elif response_type == "PR":
            reduction = rng.uniform(0.3, 0.7)
            new_size = max(5, int(baseline_case.primary.size_mm * (1 - reduction)))
            primary = Primary(
                lobe=baseline_case.primary.lobe,
                size_mm=new_size,
                features=baseline_case.primary.features[:rng.randint(0, len(baseline_case.primary.features))]
            )
        elif response_type == "PD":
            increase = rng.uniform(0.2, 0.5)
            new_size = int(baseline_case.primary.size_mm * (1 + increase))
            primary = Primary(
                lobe=baseline_case.primary.lobe,
                size_mm=new_size,
                features=baseline_case.primary.features + (["cavitation"] if rng.random() < 0.3 else [])
            )
        else:
            change = rng.uniform(-0.1, 0.1)
            new_size = max(5, int(baseline_case.primary.size_mm * (1 + change)))
            primary = Primary(
                lobe=baseline_case.primary.lobe,
                size_mm=new_size,
                features=baseline_case.primary.features
            )
    else:
        primary = None

    nodes = []
    mets = []
    if response_type in ["PR", "CR"]:
        nodes = baseline_case.nodes[:rng.randint(0, max(1, len(baseline_case.nodes)//2))]
        mets = baseline_case.mets[:rng.randint(0, max(1, len(baseline_case.mets)//2))]
    elif response_type == "PD":
        nodes = baseline_case.nodes + [Node(station=rng.choice(NODE_STATIONS), short_axis_mm=rng.randint(8, 18)) for _ in range(rng.randint(0, 2))]
        mets = baseline_case.mets + [Met(site=rng.choice(MET_SITES), size_mm=rng.randint(6, 28)) for _ in range(rng.randint(0, 1))]
    else:
        nodes = baseline_case.nodes
        mets = baseline_case.mets

    if primary:
        T, _ = t_category(primary.size_mm, "chest_wall_invasion" in primary.features, False, False, False, False, False)
    else:
        T = "T0"
    N, _ = n_category(nodes)
    M, _ = m_category(mets)
    stage = stage_group(T, N, M)
    tnm = TNM(T=T, N=N, M=M, stage_group=stage)
    response_status = determine_response_status(baseline_case, Case(meta=meta, primary=primary, nodes=nodes, mets=mets, tnm=tnm, rationale=[]))
    return Case(meta=meta, primary=primary, nodes=nodes, mets=mets, tnm=tnm, rationale=[], response_status=response_status)

def generate_patient_timeline(patient_id: str, seed: int, stage_dist: Dict[str,float],
                              lobe: Optional[str] = None, max_studies: int = 5,
                              response_dist: Dict[str,float] = None) -> tuple[List[Case], List[datetime.datetime]]:
    rng = random.Random(seed)
    num_follow_ups = rng.randint(1, max_studies)
    total_studies = 1 + num_follow_ups
    baseline_case = generate_case(
        seed=rng.randint(0, 10_000_000),
        stage_dist=stage_dist,
        lobe=lobe,
        patient_id=patient_id,
        visit_number=1
    )
    cases = [baseline_case]
    current_case = baseline_case
    study_dates = []
    baseline_date = datetime.datetime.now() - datetime.timedelta(days=rng.randint(365, 730))
    study_dates.append(baseline_date)

    for visit_num in range(2, total_studies + 1):
        days_interval = rng.randint(30, 180)
        new_study_date = study_dates[-1] + datetime.timedelta(days=days_interval)
        study_dates.append(new_study_date)
        follow_up_case = generate_follow_up_case_with_date(
            current_case,
            seed=rng.randint(0, 10_000_000),
            study_date=new_study_date,
            comparison_date=study_dates[-2].strftime("%Y-%m-%d"),
            response_dist=response_dist
        )
        follow_up_case.meta.visit_number = visit_num
        follow_up_case.meta.patient_id = patient_id
        cases.append(follow_up_case)
        current_case = follow_up_case

    return cases, study_dates

def generate_report(case: Case, modality: str = "CT", include_recist: bool = True, prior_findings: dict = None) -> str:
    lines = []
    # normalize style dict access (aliases)
    style_name = case.meta.radiologist_style or "detailed"
    alias = {"clinical": "concise", "academic": "detailed", "narrative": "oncology_narrative", "oncology": "oncology_narrative"}
    style_name = alias.get(style_name, style_name)
    style_dict = RADIOLOGIST_STYLES.get(style_name, RADIOLOGIST_STYLES["detailed"])
    
    # Generate lesion change data for narrative integration
    lesion_changes = {}
    if prior_findings and case.meta.visit_number > 1:
        # Generate current lesion IDs deterministically
        current_lesions = {}
        
        # Primary tumor
        if case.primary:
            lesion_id = f"lung-{case.primary.lobe}-longest-1"
            current_lesions[lesion_id] = {
                "type": "primary",
                "size_mm": case.primary.size_mm,
                "site": case.primary.lobe
            }
        
        # Lymph nodes
        for i, node in enumerate(case.nodes):
            lesion_id = f"ln-{node.station}-shortaxis-{i+1}"
            current_lesions[lesion_id] = {
                "type": "node",
                "size_mm": node.short_axis_mm,
                "site": node.station
            }
        
        # Metastases
        for i, met in enumerate(case.mets):
            lesion_id = f"{met.site.replace('_', '-')}-longest-{i+1}"
            current_lesions[lesion_id] = {
                "type": "metastasis",
                "size_mm": met.size_mm,
                "site": met.site
            }
        
        # Calculate changes for narrative integration
        for lesion_id, prior_data in prior_findings.items():
            if lesion_id in current_lesions:
                current_size = current_lesions[lesion_id]["size_mm"]
                prior_size = prior_data["size_mm"]
                
                if prior_size == 0:
                    change_desc = "new"
                else:
                    delta = current_size - prior_size
                    pct_change = (delta / prior_size) * 100
                    
                    if pct_change >= 20:
                        change_desc = "increased"
                    elif pct_change <= -20:
                        change_desc = "decreased"
                    else:
                        change_desc = "stable"
                
                lesion_changes[lesion_id] = {
                    "current_size": current_size,
                    "prior_size": prior_size,
                    "change_desc": change_desc,
                    "delta": delta,
                    "pct_change": pct_change
                }
            else:
                # Lesion resolved
                lesion_changes[lesion_id] = {
                    "resolved": True,
                    "prior_size": prior_data["size_mm"]
                }
        
        # Check for new lesions
        for lesion_id, current_data in current_lesions.items():
            if lesion_id not in prior_findings:
                lesion_changes[lesion_id] = {
                    "new": True,
                    "current_size": current_data["size_mm"]
                }

    # TECHNIQUE
    if modality.upper().startswith("PET"):
        lines.append("TECHNIQUE: FDG PET-CT from skull base to mid-thigh. Low-dose CT for attenuation correction and localization.")
        lines.append("Reference SUVs: liver SUVmean 2.1, mediastinal blood pool SUVmean 1.7.")
    else:
        lines.append("TECHNIQUE: CT chest, abdomen, and pelvis with IV contrast. Axial images with multiplanar reconstructions.")

    # COMPARISON
    lines.append(f"COMPARISON: {case.meta.comparison_date}." if case.meta.comparison_date else "COMPARISON: None.")
    lines.append("")
    lines.append("FINDINGS:")

    # Lungs/Primary
    if case.primary:
        # use shared primary formatter (canonical features)
        primary_text = format_primary(case.primary, radiologist_style=style_name)
        
        # Add interval change if available
        lesion_id = f"lung-{case.primary.lobe}-longest-1"
        if lesion_id in lesion_changes:
            change_data = lesion_changes[lesion_id]
            if change_data.get("new"):
                primary_text += " (new finding)."
            elif change_data.get("resolved"):
                primary_text += f" (resolved, was {change_data['prior_size']} mm)."
            else:
                change_desc = change_data["change_desc"]
                if change_desc == "stable":
                    primary_text += f" (stable, was {change_data['prior_size']} mm)."
                else:
                    delta = change_data["delta"]
                    primary_text += f" ({change_desc} from {change_data['prior_size']} mm, Δ {delta:+} mm)."
        else:
            primary_text += " (baseline measurement)."
        
        # Optional S/I reference
        if random.random() < 0.3:
            primary_text += f" (S{random.randint(1,5)}/I{random.randint(100,300)})"
        lines.append(f"Lungs/Primary: {primary_text}")
    else:
        lines.append("Lungs/Primary: Clear lungs without focal mass or suspicious nodules.")

    # Mediastinum/Lymph nodes
    if case.nodes:
        lines.append("Mediastinum/Lymph nodes:")
        for i, node in enumerate(case.nodes):
            node_text = node_phrase(node.station, node.short_axis_mm, style=style_name)
            
            # Add interval change if available
            lesion_id = f"ln-{node.station}-shortaxis-{i+1}"
            if lesion_id in lesion_changes:
                change_data = lesion_changes[lesion_id]
                if change_data.get("new"):
                    node_text += " (new finding)."
                elif change_data.get("resolved"):
                    node_text += f" (resolved, was {change_data['prior_size']} mm)."
                else:
                    change_desc = change_data["change_desc"]
                    if change_desc == "stable":
                        node_text += f" (stable, was {change_data['prior_size']} mm)."
                    else:
                        delta = change_data["delta"]
                        node_text += f" ({change_desc} from {change_data['prior_size']} mm, Δ {delta:+} mm)."
            else:
                node_text += " (baseline measurement)."
            
            lines.append(f"  {node_text}")
    else:
        lines.append(f"Mediastinum/Lymph nodes: {random.choice(style_dict.get('normal_mediastinum', ['No pathologic mediastinal adenopathy.']))}")

    # Pleura
    lines.append(f"Pleura: {random.choice(style_dict.get('normal_pleura', ['No pleural effusion.']))}")

    # Abdomen/Pelvis
    lines.append("Abdomen/Pelvis:")
    ap_lines = []

    # Metastases (abdominal/pelvic relevant)
    if case.mets:
        for i, met in enumerate(case.mets):
            if met.site in ["adrenal_right", "adrenal_left", "liver", "peritoneum", "omentum", "retroperitoneal_nodes"]:
                site_name = met.site.replace("_", " ")
                met_phrases = style_dict.get("metastasis_phrases", ["{site} nodule {size} mm, suspicious for metastasis."])
                met_template = random.choice(met_phrases)
                met_text = met_template.format(site=site_name, size=met.size_mm)
                
                # Add interval change if available
                lesion_id = f"{met.site.replace('_', '-')}-longest-{i+1}"
                if lesion_id in lesion_changes:
                    change_data = lesion_changes[lesion_id]
                    if change_data.get("new"):
                        met_text += " (new finding)."
                    elif change_data.get("resolved"):
                        met_text += f" (resolved, was {change_data['prior_size']} mm)."
                    else:
                        change_desc = change_data["change_desc"]
                        if change_desc == "stable":
                            met_text += f" (stable, was {change_data['prior_size']} mm)."
                        else:
                            delta = change_data["delta"]
                            met_text += f" ({change_desc} from {change_data['prior_size']} mm, Δ {delta:+} mm)."
                else:
                    met_text += " (baseline measurement)."
                
                ap_lines.append("  " + met_text)

    # Normal abdomen (skip liver-normal if liver met already described)
    has_liver_met = any(m.site == "liver" for m in case.mets)
    for normal in style_dict.get("normal_abdomen", [
        "Liver homogeneous in attenuation without focal mass.",
        "Adrenal glands without nodules.",
        "No peritoneal nodularity."
    ]):
        if "Liver" in normal and has_liver_met:
            continue
        ap_lines.append("  " + normal)

    lines.extend(ap_lines if ap_lines else ["  No acute abnormality in the abdomen or pelvis."])

    # Bones
    lines.append(f"Bones: {random.choice(style_dict.get('normal_bones', ['No destructive osseous lesion.']))}")

    # Artifacts (optional)
    if random.random() < 0.4:
        lines.append(f"Artifacts: {random.choice(style_dict.get('artifact_phrases', ['Mild respiratory motion artifact.']))}")

    # IMPRESSION
    lines.append("")
    lines.append("IMPRESSION:")

    if case.primary:
        side = SIDE_FROM_LOBE[case.primary.lobe]
        feats = feature_text(case.primary.features)
        lines.append(f"- Primary {side} pulmonary neoplasm {case.primary.size_mm} mm with {feats}; baseline measurement.")

    # Nodes
    if case.nodes:
        pathologic_nodes = [n for n in case.nodes if n.short_axis_mm >= 10]
        if pathologic_nodes:
            stations = [n.station for n in pathologic_nodes]
            lines.append(f"- Nodal disease involving stations {', '.join(stations)}.")
        else:
            lines.append(f"- {random.choice(style_dict.get('normal_mediastinum', ['No pathologic mediastinal adenopathy.']))}")
    else:
        lines.append(f"- {random.choice(style_dict.get('normal_mediastinum', ['No pathologic mediastinal adenopathy.']))}")

    # Mets
    if case.mets:
        # Summarize sites succinctly with sizes
        site_summaries = []
        for m in case.mets:
            site_summaries.append(f"{m.site.replace('_',' ')} ({m.size_mm} mm)")
        lines.append(f"- Distant metastatic disease involving " + ", ".join(site_summaries) + ".")
    else:
        lines.append("- No definite distant metastases identified.")

    return "\n".join(lines)

def write_case(case: Case, outdir: str, stem: str, use_radlex: bool = True):
    if case.meta.patient_id:
        patient_dir = os.path.join(outdir, case.meta.patient_id)
        study_dir = os.path.join(patient_dir, f"study_{case.meta.visit_number:02d}")
        os.makedirs(study_dir, exist_ok=True)
        filename = f"{case.meta.accession_number}" if case.meta.accession_number else stem
    else:
        os.makedirs(outdir, exist_ok=True)
        study_dir = outdir
        filename = stem

    report = generate_report(case)

    # Write TXT
    txt_path = os.path.join(study_dir, f"{filename}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report)

    combined_data = {
        "meta": case.meta.model_dump(),
        "clinical_data": {
            "primary": case.primary.model_dump() if case.primary else None,
            "nodes": [node.model_dump() for node in case.nodes],
            "mets": [met.model_dump() for met in case.mets],
            "tnm": case.tnm.model_dump(),
            "rationale": case.rationale,
            "response_status": case.response_status
        }
    }

    if use_radlex:
        try:
            import datetime
            study_date = datetime.datetime.now().strftime("%Y-%m-%d")
            anatomic_mapping = {
                "patient_id": case.meta.patient_id or "unknown",
                "study_date": study_date,
                "body_regions": {
                    "thorax": {
                        "lungs": {
                            "right_lung": {"findings": [], "subregions": {}},
                            "left_lung": {"findings": [], "subregions": {}}
                        },
                        "mediastinum": {"lymph_nodes": {"findings": [], "subregions": {}}},
                        "pleura": {"findings": [], "subregions": {}}
                    }
                },
                "lesions": [],
                "lymph_nodes": [],
                "metastases": [],
                "artifacts": []
            }
            if case.primary:
                lung_side = "right_lung" if case.primary.lobe in ["RUL","RML","RLL"] else "left_lung"
                laterality = "right" if lung_side == "right_lung" else "left"
                anatomic_mapping["body_regions"]["thorax"]["lungs"][lung_side]["findings"].append({
                    "type": "primary_tumor",
                    "location": case.primary.lobe,
                    "size_mm": case.primary.size_mm,
                    "radlex_id": None
                })
                anatomic_mapping["lesions"].append({
                    "finding_type": "primary_tumor",
                    "anatomic_location": {
                        "name": case.primary.lobe,
                        "radlex_id": None,
                        "radlex_label": "lung mass",
                        "parent_location": lung_side,
                        "level": "lobe",
                        "laterality": laterality,
                        "position": None
                    },
                    "size_mm": case.primary.size_mm,
                    "features": case.primary.features,
                    "radlex_id": None,
                    "radlex_label": "lung mass",
                    "confidence": 1.0,
                    "target_lesion": True
                })
            for node in case.nodes:
                anatomic_mapping["body_regions"]["thorax"]["mediastinum"]["lymph_nodes"]["findings"].append({
                    "type": "lymph_node",
                    "station": node.station,
                    "size_mm": node.short_axis_mm,
                    "radlex_id": None
                })
                anatomic_mapping["lymph_nodes"].append({
                    "finding_type": "lymph_node",
                    "anatomic_location": {
                        "name": node.station,
                        "radlex_id": None,
                        "radlex_label": "mediastinal lymph node",
                        "parent_location": "mediastinal_lymph_nodes",
                        "level": "station",
                        "laterality": "right" if node.station.endswith("R") else "left" if node.station.endswith("L") else "central",
                        "position": None
                    },
                    "size_mm": node.short_axis_mm,
                    "features": [],
                    "radlex_id": None,
                    "radlex_label": "mediastinal lymph node",
                    "confidence": 1.0,
                    "target_lesion": node.short_axis_mm >= 10
                })
            for met in case.mets:
                anatomic_mapping["metastases"].append({
                    "finding_type": "metastasis",
                    "anatomic_location": {
                        "name": met.site,
                        "radlex_id": None,
                        "radlex_label": "metastasis",
                        "parent_location": "extrathoracic",
                        "level": "organ",
                        "laterality": None,
                        "position": None
                    },
                    "size_mm": met.size_mm,
                    "features": [],
                    "radlex_id": None,
                    "radlex_label": "metastasis",
                    "confidence": 1.0,
                    "target_lesion": met.size_mm >= 10
                })
            combined_data["anatomic_mapping"] = anatomic_mapping
        except Exception as e:
            print(f"Warning: Failed to create anatomic map for {case.meta.accession_number}: {e}")
            combined_data["anatomic_mapping"] = {
                "body_regions": {},
                "lesions": [],
                "lymph_nodes": [],
                "metastases": [],
                "artifacts": []
            }
    else:
        combined_data["anatomic_mapping"] = {
            "body_regions": {},
            "lesions": [],
            "lymph_nodes": [],
            "metastases": [],
            "artifacts": []
        }

    json_path = os.path.join(study_dir, f"{filename}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2)

def parse_stage_dist(arg: str) -> Dict[str,float]:
    parts = [p for p in arg.split(',') if p]
    out = {}
    for p in parts:
        k,v = p.split(':')
        out[k.strip()] = float(v)
    s = sum(out.values())
    if s <= 0: raise ValueError("stage distribution must sum > 0")
    for k in out:
        out[k] /= s
    return out

def parse_response_dist(arg: str) -> Dict[str,float]:
    parts = [p for p in arg.split(',') if p]
    out = {}
    for p in parts:
        k,v = p.split(':')
        out[k.strip()] = float(v)
    s = sum(out.values())
    if s <= 0: raise ValueError("response distribution must sum > 0")
    for k in out:
        out[k] /= s
    return out

def case_to_recist_jsonl(cases: List[Case], study_dates: List[datetime.datetime] = None) -> List[dict]:
    """
    Convert cases to RECIST 1.1 compliant JSONL format.
    """
    jsonl_data = []
    for i, case in enumerate(cases):
        # Get RECIST 1.1 compliant target and non-target lesions
        targets = select_recist_targets(case.primary, case.nodes, case.mets)
        nontargets = classify_nontarget_lesions(case.primary, case.nodes, case.mets, targets)
        
        # Calculate SLD for target lesions only
        sld_mm = calculate_sld(targets)
        
        # Build lesions list with proper RECIST 1.1 classification
        lesions = []
        
        # Add target lesions
        for target in targets:
            lesion_entry = {
                "lesion_id": target["lesion_id"],
                "kind": target["type"],
                "organ": target["organ"],
                "rule": target["measurement_type"],
                "baseline_mm": target["size_mm"] if case.meta.visit_number == 1 else None,
                "follow_mm": target["size_mm"] if case.meta.visit_number > 1 else None,
                "size_mm_current": target["size_mm"],
                "target": True,
                "suspicious": True
            }
            
            # Add organ-specific fields
            if target["type"] == "primary":
                lesion_entry["location"] = case.primary.lobe
                lesion_entry["margin"] = "spiculated" if "spiculation" in case.primary.features else "smooth"
                lesion_entry["enhancement"] = "enhancing"
                lesion_entry["necrosis"] = "cavitation" in case.primary.features
            elif target["type"] == "node":
                lesion_entry["station"] = target["station"]
                lesion_entry["margin"] = "smooth"
                lesion_entry["enhancement"] = "enhancing"
                lesion_entry["necrosis"] = False
            elif target["type"] == "metastasis":
                lesion_entry["location"] = target["organ"]
                lesion_entry["margin"] = "smooth"
                lesion_entry["enhancement"] = "enhancing"
                lesion_entry["necrosis"] = False
            
            lesions.append(lesion_entry)
        
        # Add non-target lesions
        for nontarget in nontargets:
            lesion_entry = {
                "lesion_id": nontarget["lesion_id"],
                "kind": nontarget["type"],
                "organ": nontarget["organ"],
                "rule": "longest" if nontarget["type"] != "node" else "short_axis",
                "baseline_mm": nontarget["size_mm"] if case.meta.visit_number == 1 else None,
                "follow_mm": nontarget["size_mm"] if case.meta.visit_number > 1 else None,
                "size_mm_current": nontarget["size_mm"],
                "target": False,
                "suspicious": True,
                "reason": nontarget["reason"]
            }
            
            # Add organ-specific fields
            if nontarget["type"] == "primary":
                lesion_entry["location"] = case.primary.lobe
                lesion_entry["margin"] = "spiculated" if "spiculation" in case.primary.features else "smooth"
                lesion_entry["enhancement"] = "enhancing"
                lesion_entry["necrosis"] = "cavitation" in case.primary.features
            elif nontarget["type"] == "node":
                lesion_entry["station"] = nontarget["station"]
                lesion_entry["margin"] = "smooth"
                lesion_entry["enhancement"] = "enhancing"
                lesion_entry["necrosis"] = False
            elif nontarget["type"] == "metastasis":
                lesion_entry["location"] = nontarget["organ"]
                lesion_entry["margin"] = "smooth"
                lesion_entry["enhancement"] = "enhancing"
                lesion_entry["necrosis"] = False
            
            lesions.append(lesion_entry)
        
        # Determine study date
        if study_dates and i < len(study_dates):
            study_date = study_dates[i].strftime("%Y-%m-%d")
        else:
            if case.meta.visit_number == 1:
                study_date = (datetime.datetime.now() - datetime.timedelta(days=random.randint(365, 730))).strftime("%Y-%m-%d")
            else:
                baseline_days_ago = random.randint(365, 730)
                follow_up_days_ago = baseline_days_ago - (case.meta.visit_number - 1) * random.randint(30, 180)
                study_date = (datetime.datetime.now() - datetime.timedelta(days=follow_up_days_ago)).strftime("%Y-%m-%d")

        # Create RECIST 1.1 compliant entry
        entry = {
            "patient_id": case.meta.patient_id,
            "timepoint": case.meta.visit_number - 1,
            "study_date": study_date,
            "baseline_sld_mm": sld_mm if case.meta.visit_number == 1 else None,
            "current_sld_mm": sld_mm,
            "nadir_sld_mm": None,
            "overall_response": case.response_status or "SD",
            "target_lesions": len(targets),
            "nontarget_lesions": len(nontargets),
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
    ap.add_argument("--stage-dist", type=str, default="I:0.25,II:0.25,III:0.30,IV:0.20", help="Stage distribution")
    ap.add_argument("--follow-up", action="store_true", help="Generate follow-up cases for each baseline case")
    ap.add_argument("--follow-up-days", type=int, default=90, help="Days between baseline and follow-up (default: 90)")
    ap.add_argument("--studies-per-patient", type=int, default=5, help="Max studies per patient (2-10, default: 5)")
    ap.add_argument("--response-dist", type=str, default="CR:0.1,PR:0.3,SD:0.4,PD:0.2", help="Response distribution (will be normalized)")
    ap.add_argument("--no-radlex", action="store_true", help="Disable RadLex anatomic mapping (enabled by default)")
    ap.add_argument("--legacy-mode", action="store_true", help="Use legacy flat file structure")
    ap.add_argument("--jsonl", type=str, default=None, help="Output JSONL file for React app (e.g., cohort_labels.jsonl)")
    args = ap.parse_args()

    if args.studies_per_patient < 2 or args.studies_per_patient > 10:
        print("Error: studies-per-patient must be between 2 and 10")
        return

    rng = random.Random(args.seed)
    dist = parse_stage_dist(args.stage_dist)
    response_dist = parse_response_dist(args.response_dist)
    use_radlex = not args.no_radlex

    all_cases = []
    all_study_dates = []

    for i in range(args.n):
        patient_id = f"P{i:04d}"

        if args.legacy_mode:
            baseline_case = generate_case(
                seed=rng.randint(0,10_000_000),
                stage_dist=dist,
                lobe=args.lobe,
                patient_id=patient_id,
                visit_number=1
            )
            write_case(baseline_case, args.out, f"{patient_id}_baseline", use_radlex)

            if args.follow_up:
                follow_up_case = generate_follow_up_case(
                    baseline_case,
                    seed=rng.randint(0,10_000_000),
                    days_later=args.follow_up_days
                )
                write_case(follow_up_case, args.out, f"{patient_id}_followup", use_radlex)
        else:
            cases, study_dates = generate_patient_timeline(
                patient_id=patient_id,
                seed=rng.randint(0, 10_000_000),
                stage_dist=dist,
                lobe=args.lobe,
                max_studies=args.studies_per_patient,
                response_dist=response_dist
            )
            for case in cases:
                write_case(case, args.out, case.meta.accession_number, use_radlex)
            all_cases.extend(cases)
            all_study_dates.extend(study_dates)

    if args.jsonl and all_cases:
        jsonl_data = case_to_recist_jsonl(all_cases, all_study_dates)
        jsonl_path = os.path.join(args.out, args.jsonl)
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for entry in jsonl_data:
                f.write(json.dumps(entry) + "\n")
        print(f"Created JSONL file: {jsonl_path}")

if __name__ == "__main__":
    main()