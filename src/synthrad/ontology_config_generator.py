"""
Ontology-focused config generator for creating RadLex-anchored graph JSON configs.
Generates structured, ontology-compliant configuration files for each study.
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from .radlex_resolver import create_radlex_resolver
from .anatomic_mapper import AnatomicLocation, LesionFinding


@dataclass
class OntologyConcept:
    """Represents an ontology concept with full metadata."""
    text: str
    radlex: Optional[Dict[str, str]] = None
    parents: List[Dict[str, str]] = None
    laterality: Optional[str] = None
    level: Optional[str] = None
    
    def __post_init__(self):
        if self.parents is None:
            self.parents = []


@dataclass
class Measurement:
    """Represents a measurement with ontology context."""
    type: str  # longest_diameter, short_axis, etc.
    value_mm: float
    method: str = "in-plane"
    rule: str = "RECIST_longest"
    evidence: Optional[str] = None


@dataclass
class LesionNode:
    """Represents a lesion node in the ontology graph."""
    id: str
    lesion_uid: str
    category: str  # primary_tumor, lymph_node, metastasis
    status: str  # active, resolved, new, unevaluable
    anatomy: OntologyConcept
    measurements: List[Measurement]
    attributes: List[Dict[str, Any]]
    target_status: str  # target, non_target
    type: str = "lesion"
    non_target_reason: Optional[str] = None


@dataclass
class AnatomicalNode:
    """Represents an anatomical region node."""
    id: str
    label: OntologyConcept
    type: str = "anatomical_region"


@dataclass
class GraphEdge:
    """Represents a relationship edge in the ontology graph."""
    from_node: str
    to_node: str
    relation: str


@dataclass
class StudyContext:
    """Study context with staging and RECIST information."""
    cancer_type: OntologyConcept
    timepoint: int
    recist: Dict[str, Any]
    staging: Dict[str, Optional[str]]


@dataclass
class OntologyConfig:
    """Complete ontology-focused configuration for a study."""
    graph_id: str
    patient_id: str
    study: Dict[str, Any]
    context: StudyContext
    nodes: List[Dict[str, Any]]
    edges: List[GraphEdge]
    provenance: Dict[str, Any]


class OntologyConfigGenerator:
    """Generates ontology-focused configuration files for studies."""
    
    def __init__(self, use_radlex: bool = True, cache_file: Optional[str] = None):
        self.use_radlex = use_radlex
        self.resolver = None
        
        if use_radlex:
            try:
                self.resolver = create_radlex_resolver(cache_file=cache_file)
            except Exception as e:
                print(f"Warning: RadLex resolver unavailable: {e}")
                self.use_radlex = False
        
        # IASLC nodal station mappings
        self.iaslc_stations = {
            "1R": "right highest mediastinal lymph node (1R)",
            "1L": "left highest mediastinal lymph node (1L)",
            "2R": "right upper paratracheal lymph node (2R)",
            "2L": "left upper paratracheal lymph node (2L)",
            "3": "prevascular lymph node (3)",
            "4R": "right lower paratracheal lymph node (4R)",
            "4L": "left lower paratracheal lymph node (4L)",
            "5": "subaortic lymph node (5)",
            "6": "para-aortic lymph node (6)",
            "7": "subcarinal lymph node (7)",
            "8": "paraesophageal lymph node (8)",
            "9": "pulmonary ligament lymph node (9)",
            "10R": "right hilar lymph node (10R)",
            "10L": "left hilar lymph node (10L)",
            "11R": "right interlobar lymph node (11R)",
            "11L": "left interlobar lymph node (11L)",
            "12R": "right lobar lymph node (12R)",
            "12L": "left lobar lymph node (12L)"
        }
        
        # Lobe mappings
        self.lobe_mappings = {
            "RUL": "right upper lobe of lung",
            "RML": "right middle lobe of lung", 
            "RLL": "right lower lobe of lung",
            "LUL": "left upper lobe of lung",
            "LLL": "left lower lobe of lung"
        }
        
        # Metastatic site mappings
        self.metastatic_sites = {
            "liver": "liver",
            "brain": "brain", 
            "bone": "bone",
            "adrenal_right": "right adrenal gland",
            "adrenal_left": "left adrenal gland",
            "kidney_right": "right kidney",
            "kidney_left": "left kidney"
        }

    def resolve_anatomy(self, term: str, context: List[str] = None) -> OntologyConcept:
        """Resolve anatomical term to ontology concept."""
        if not self.use_radlex or not self.resolver:
            return OntologyConcept(text=term)
        
        concept_data = self.resolver.resolve_with_parents(term, context)
        if concept_data:
            return OntologyConcept(
                text=term,
                radlex={
                    "label": concept_data.get("label"),
                    "rid": concept_data.get("rid"),
                    "iri": concept_data.get("iri")
                },
                parents=concept_data.get("parents", [])
            )
        
        return OntologyConcept(text=term)

    def create_lesion_node(self, lesion_data: Dict[str, Any], lesion_uid: str, 
                          timepoint: int) -> LesionNode:
        """Create a lesion node from lesion data."""
        # Determine category and anatomy
        if lesion_data.get("kind") == "primary":
            category = "primary_tumor"
            lobe = lesion_data.get("lobe", "RML")
            anatomy_text = self.lobe_mappings.get(lobe, lobe)
            anatomy = self.resolve_anatomy(anatomy_text, ["lung", "lobe"])
            anatomy.laterality = "right" if lobe.startswith("R") else "left"
            anatomy.level = "lobe"
        elif lesion_data.get("kind") == "node":
            category = "lymph_node"
            station = lesion_data.get("station", "4L")
            anatomy_text = self.iaslc_stations.get(station, f"mediastinal lymph node station {station}")
            anatomy = self.resolve_anatomy(anatomy_text, ["mediastinum", "lymph node", "station"])
            anatomy.laterality = "right" if station.endswith("R") else ("left" if station.endswith("L") else "central")
            anatomy.level = "station"
        elif lesion_data.get("kind") == "metastasis":
            category = "metastasis"
            site = lesion_data.get("site", "liver")
            anatomy_text = self.metastatic_sites.get(site, site)
            anatomy = self.resolve_anatomy(anatomy_text, ["organ"])
            anatomy.laterality = "right" if "right" in anatomy_text else ("left" if "left" in anatomy_text else None)
            anatomy.level = "organ"
        else:
            category = "unknown"
            anatomy = self.resolve_anatomy("unknown")
        
        # Create measurements
        measurements = []
        if lesion_data.get("size_mm"):
            if category == "primary_tumor":
                measurements.append(Measurement(
                    type="longest_diameter",
                    value_mm=lesion_data["size_mm"],
                    rule="RECIST_longest",
                    evidence=lesion_data.get("evidence")
                ))
            elif category == "lymph_node":
                measurements.append(Measurement(
                    type="short_axis",
                    value_mm=lesion_data["size_mm"],
                    rule="RECIST_short_axis_node",
                    evidence=lesion_data.get("evidence")
                ))
            else:
                measurements.append(Measurement(
                    type="longest_diameter",
                    value_mm=lesion_data["size_mm"],
                    rule="RECIST_longest",
                    evidence=lesion_data.get("evidence")
                ))
        
        # Determine status
        status = "active"
        if lesion_data.get("resolved"):
            status = "resolved"
        elif lesion_data.get("new"):
            status = "new"
        
        # Determine target status
        target_status = "target"
        non_target_reason = None
        if category == "lymph_node" and lesion_data.get("size_mm", 0) < 10:
            target_status = "non_target"
            non_target_reason = "below_threshold"
        
        # Create attributes
        attributes = []
        if lesion_data.get("features"):
            for feature in lesion_data["features"]:
                attributes.append({"name": "morphology", "value": feature})
        
        return LesionNode(
            id=f"lesion:{lesion_data.get('id', 'unknown')}",
            lesion_uid=lesion_uid,
            category=category,
            status=status,
            anatomy=anatomy,
            measurements=measurements,
            attributes=attributes,
            target_status=target_status,
            non_target_reason=non_target_reason
        )

    def create_anatomical_nodes(self, lesions: List[LesionNode]) -> List[AnatomicalNode]:
        """Create anatomical region nodes from lesions."""
        anatomical_regions = {}
        
        for lesion in lesions:
            # Add the specific anatomical structure
            key = lesion.anatomy.text
            if key not in anatomical_regions:
                anatomical_regions[key] = lesion.anatomy.radlex
                
                # Add parent structures
                for parent in lesion.anatomy.parents:
                    if parent.get("label"):
                        parent_key = parent["label"]
                        if parent_key not in anatomical_regions:
                            anatomical_regions[parent_key] = {
                                "label": parent["label"],
                                "rid": parent.get("rid"),
                                "iri": parent.get("iri")
                            }
        
        nodes = []
        for text, radlex_data in anatomical_regions.items():
            nodes.append(AnatomicalNode(
                id=f"anatomy:{text.replace(' ', '_').lower()}",
                label=OntologyConcept(text=text, radlex=radlex_data)
            ))
        
        return nodes

    def create_graph_edges(self, lesions: List[LesionNode], 
                          anatomical_nodes: List[AnatomicalNode]) -> List[GraphEdge]:
        """Create graph edges between lesions and anatomical structures."""
        edges = []
        
        # Create mapping of anatomical text to node IDs
        anatomy_to_id = {}
        for node in anatomical_nodes:
            anatomy_to_id[node.label.text] = node.id
        
        for lesion in lesions:
            # Connect lesion to its anatomical location
            if lesion.anatomy.text in anatomy_to_id:
                edges.append(GraphEdge(
                    from_node=lesion.id,
                    to_node=anatomy_to_id[lesion.anatomy.text],
                    relation="located_in"
                ))
            
            # Connect anatomical structures hierarchically
            for parent in lesion.anatomy.parents:
                if parent.get("label") in anatomy_to_id:
                    edges.append(GraphEdge(
                        from_node=anatomy_to_id[lesion.anatomy.text],
                        to_node=anatomy_to_id[parent["label"]],
                        relation="part_of"
                    ))
        
        return edges

    def generate_ontology_config(self, case_data: Dict[str, Any], patient_id: str, 
                                study_date: str, timepoint: int) -> OntologyConfig:
        """Generate complete ontology configuration for a study."""
        
        # Create study info
        study_info = {
            "study_id": f"{patient_id}_{study_date}_CT-CAP",
            "modality": "CT",
            "body_regions": ["RID1243"],  # chest-abdomen-pelvis placeholder
            "contrast": True,
            "study_date": study_date,
            "report_sections": {
                "technique": case_data.get("technique", ""),
                "comparison": case_data.get("comparison", "None."),
                "findings": case_data.get("findings", ""),
                "impression": case_data.get("impression", "")
            }
        }
        
        # Create context
        cancer_type = self.resolve_anatomy("non-small cell lung carcinoma", ["cancer"])
        context = StudyContext(
            cancer_type=cancer_type,
            timepoint=timepoint,
            recist={
                "baseline_sld_mm": case_data.get("baseline_sld_mm"),
                "current_sld_mm": case_data.get("current_sld_mm"),
                "nadir_sld_mm": case_data.get("nadir_sld_mm"),
                "overall_response": case_data.get("overall_response", "Baseline")
            },
            staging={
                "T": case_data.get("staging", {}).get("t_stage"),
                "N": case_data.get("staging", {}).get("n_stage"),
                "M": case_data.get("staging", {}).get("m_stage"),
                "stage_group": case_data.get("staging", {}).get("stage_group")
            }
        )
        
        # Create lesion nodes
        lesions = []
        lesion_counter = 1
        
        # Process lesions from the lesions array
        for lesion_data in case_data.get("lesions", []):
            # Map the lesion data to the expected format
            mapped_lesion = {
                "id": lesion_data.get("lesion_id", f"lesion_{lesion_counter}"),
                "kind": lesion_data.get("kind", "unknown"),
                "lobe": lesion_data.get("location"),
                "station": lesion_data.get("station"),
                "site": lesion_data.get("organ"),
                "size_mm": lesion_data.get("size_mm_current"),
                "features": [],
                "evidence": None,
                "resolved": lesion_data.get("kind") == "unknown" and lesion_data.get("size_mm_current", 0) == 0,
                "new": lesion_data.get("baseline_mm") is None and lesion_data.get("size_mm_current", 0) > 0
            }
            
            # Add features if available
            if lesion_data.get("margin"):
                mapped_lesion["features"].append(lesion_data["margin"])
            if lesion_data.get("necrosis"):
                mapped_lesion["features"].append("necrosis")
            if lesion_data.get("suspicious"):
                mapped_lesion["features"].append("suspicious")
            
            # Create lesion UID based on type
            if mapped_lesion["kind"] == "primary":
                lesion_uid = f"L-{patient_id}-PRIMARY-{lesion_counter:03d}"
            elif mapped_lesion["kind"] == "node":
                lesion_uid = f"L-{patient_id}-LN-{mapped_lesion.get('station', 'UNK')}-{lesion_counter:03d}"
            elif mapped_lesion["kind"] == "metastasis":
                lesion_uid = f"L-{patient_id}-MET-{mapped_lesion.get('site', 'UNK')}-{lesion_counter:03d}"
            else:
                lesion_uid = f"L-{patient_id}-UNK-{lesion_counter:03d}"
            
            lesion_node = self.create_lesion_node(mapped_lesion, lesion_uid, timepoint)
            lesions.append(lesion_node)
            lesion_counter += 1
        
        # Create anatomical nodes
        anatomical_nodes = self.create_anatomical_nodes(lesions)
        
        # Create edges
        edges = self.create_graph_edges(lesions, anatomical_nodes)
        
        # Add study observation edges
        study_id = f"study:{study_info['study_id']}"
        for lesion in lesions:
            edges.append(GraphEdge(
                from_node=lesion.id,
                to_node=study_id,
                relation="observed_in"
            ))
        
        # Combine all nodes
        all_nodes = []
        for lesion in lesions:
            lesion_dict = asdict(lesion)
            lesion_dict["anatomy"] = asdict(lesion.anatomy)
            lesion_dict["measurements"] = [asdict(m) for m in lesion.measurements]
            all_nodes.append(lesion_dict)
        
        for node in anatomical_nodes:
            node_dict = asdict(node)
            node_dict["label"] = asdict(node.label)
            all_nodes.append(node_dict)
        
        # Add study node
        all_nodes.append({
            "id": study_id,
            "type": "study",
            "study_info": study_info
        })
        
        # Create provenance
        provenance = {
            "source_report_id": f"rep-{patient_id}-{study_date}",
            "nlp_version": "v0.1",
            "section_offsets": {
                "findings": [0, len(case_data.get("findings", ""))],
                "impression": [len(case_data.get("findings", "")), 
                             len(case_data.get("findings", "")) + len(case_data.get("impression", ""))]
            },
            "unit_norm": "mm",
            "recist_ruleset": "RECIST 1.1",
            "tnm_ruleset": "AJCC 8th (lung)"
        }
        
        return OntologyConfig(
            graph_id=f"{patient_id}_t{timepoint}",
            patient_id=patient_id,
            study=study_info,
            context=context,
            nodes=all_nodes,
            edges=[asdict(edge) for edge in edges],
            provenance=provenance
        )

    def save_ontology_config(self, config: OntologyConfig, output_dir: str):
        """Save ontology configuration to file."""
        os.makedirs(output_dir, exist_ok=True)
        
        # Convert to dictionary
        config_dict = {
            "graph_id": config.graph_id,
            "patient_id": config.patient_id,
            "study": config.study,
            "context": asdict(config.context),
            "nodes": config.nodes,
            "edges": config.edges,
            "provenance": config.provenance
        }
        
        # Save to file
        filename = f"{config.graph_id}_ontology.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        print(f"Saved ontology config: {filepath}")
        return filepath


def generate_ontology_configs_for_cohort(cohort_data: List[Dict[str, Any]], 
                                        output_dir: str,
                                        use_radlex: bool = True) -> List[str]:
    """Generate ontology configurations for an entire cohort."""
    generator = OntologyConfigGenerator(use_radlex=use_radlex)
    config_files = []
    
    for case in cohort_data:
        patient_id = case.get("patient_id", "UNKNOWN")
        study_date = case.get("study_date", "UNKNOWN")
        timepoint = case.get("timepoint", 0)
        
        try:
            config = generator.generate_ontology_config(case, patient_id, study_date, timepoint)
            config_file = generator.save_ontology_config(config, output_dir)
            config_files.append(config_file)
        except Exception as e:
            print(f"Error generating config for {patient_id}: {e}")
    
    return config_files
