#!/usr/bin/env python3
"""
Anatomic Mapper using RadLex for hierarchical lesion and finding mapping.

This module uses RadLex ontology to create structured, hierarchical maps
of lesions, their anatomic locations, and relationships.
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import random

from .radlex_service import get_radlex_service
from .radlex_config import get_config


@dataclass
class AnatomicLocation:
    """Represents an anatomic location with RadLex mapping."""
    name: str
    radlex_id: Optional[str] = None
    radlex_label: Optional[str] = None
    parent_location: Optional[str] = None
    level: str = "organ"  # body, region, organ, suborgan, segment
    laterality: Optional[str] = None  # left, right, bilateral
    position: Optional[str] = None  # anterior, posterior, superior, inferior, etc.


@dataclass
class LesionFinding:
    """Represents a lesion or finding with anatomic mapping."""
    finding_type: str  # nodule, mass, lymph_node, metastasis, etc.
    anatomic_location: AnatomicLocation
    size_mm: Optional[int] = None
    features: List[str] = None  # spiculation, cavitation, etc.
    radlex_id: Optional[str] = None
    radlex_label: Optional[str] = None
    confidence: float = 1.0
    target_lesion: bool = True
    
    def __post_init__(self):
        if self.features is None:
            self.features = []


@dataclass
class AnatomicMap:
    """Hierarchical map of anatomic findings."""
    patient_id: str
    study_date: str
    body_regions: Dict[str, Dict[str, Any]] = None
    lesions: List[LesionFinding] = None
    lymph_nodes: List[LesionFinding] = None
    metastases: List[LesionFinding] = None
    artifacts: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.body_regions is None:
            self.body_regions = {}
        if self.lesions is None:
            self.lesions = []
        if self.lymph_nodes is None:
            self.lymph_nodes = []
        if self.metastases is None:
            self.metastases = []
        if self.artifacts is None:
            self.artifacts = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self, filepath: str):
        """Save to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


class RadLexAnatomicMapper:
    """Maps anatomic structures and findings using RadLex ontology."""
    
    def __init__(self, use_radlex: bool = True, cache_file: Optional[str] = None):
        self.use_radlex = use_radlex
        self.radlex_service = None
        self.cache_file = cache_file
        
        if use_radlex:
            try:
                self.radlex_service = get_radlex_service(cache_file=cache_file)
            except Exception as e:
                print(f"Warning: RadLex service unavailable: {e}")
                self.use_radlex = False
        
        # Predefined anatomic hierarchy for lung cancer
        self.anatomic_hierarchy = {
            "thorax": {
                "lungs": {
                    "right_lung": {
                        "RUL": {"level": "lobe", "laterality": "right"},
                        "RML": {"level": "lobe", "laterality": "right"},
                        "RLL": {"level": "lobe", "laterality": "right"}
                    },
                    "left_lung": {
                        "LUL": {"level": "lobe", "laterality": "left"},
                        "LLL": {"level": "lobe", "laterality": "left"}
                    }
                },
                "mediastinum": {
                    "lymph_nodes": {
                        "2R": {"level": "station", "laterality": "right"},
                        "2L": {"level": "station", "laterality": "left"},
                        "4R": {"level": "station", "laterality": "right"},
                        "4L": {"level": "station", "laterality": "left"},
                        "7": {"level": "station", "laterality": "central"},
                        "10R": {"level": "station", "laterality": "right"},
                        "10L": {"level": "station", "laterality": "left"}
                    }
                },
                "pleura": {
                    "right_pleura": {"level": "pleura", "laterality": "right"},
                    "left_pleura": {"level": "pleura", "laterality": "left"}
                }
            }
        }
    
    def map_lung_location(self, lobe: str) -> AnatomicLocation:
        """Map a lung lobe to its anatomic location."""
        if lobe in ["RUL", "RML", "RLL"]:
            laterality = "right"
            parent = "right_lung"
        elif lobe in ["LUL", "LLL"]:
            laterality = "left"
            parent = "left_lung"
        else:
            laterality = None
            parent = None
        
        # Try to get RadLex mapping
        radlex_id = None
        radlex_label = None
        if self.use_radlex and self.radlex_service:
            try:
                concept = self.radlex_service.get_concept_by_text(f"{lobe} lobe")
                if concept:
                    radlex_id = concept.get("iri")
                    radlex_label = concept.get("class_label")
            except Exception:
                pass
        
        return AnatomicLocation(
            name=lobe,
            radlex_id=radlex_id,
            radlex_label=radlex_label,
            parent_location=parent,
            level="lobe",
            laterality=laterality
        )
    
    def map_lymph_node_station(self, station: str) -> AnatomicLocation:
        """Map a lymph node station to its anatomic location."""
        laterality = None
        if station.endswith("R"):
            laterality = "right"
        elif station.endswith("L"):
            laterality = "left"
        else:
            laterality = "central"
        
        # Try to get RadLex mapping
        radlex_id = None
        radlex_label = None
        if self.use_radlex and self.radlex_service:
            try:
                concept = self.radlex_service.get_concept_by_text(f"mediastinal lymph node station {station}")
                if concept:
                    radlex_id = concept.get("iri")
                    radlex_label = concept.get("class_label")
            except Exception:
                pass
        
        return AnatomicLocation(
            name=station,
            radlex_id=radlex_id,
            radlex_label=radlex_label,
            parent_location="mediastinal_lymph_nodes",
            level="station",
            laterality=laterality
        )
    
    def map_metastatic_site(self, site: str) -> AnatomicLocation:
        """Map a metastatic site to its anatomic location."""
        # Map common metastatic sites
        site_mapping = {
            "liver": {"level": "organ", "parent": "abdomen"},
            "brain": {"level": "organ", "parent": "central_nervous_system"},
            "bone": {"level": "system", "parent": "musculoskeletal"},
            "adrenal_right": {"level": "organ", "parent": "abdomen", "laterality": "right"},
            "adrenal_left": {"level": "organ", "parent": "abdomen", "laterality": "left"},
            "kidney_right": {"level": "organ", "parent": "abdomen", "laterality": "right"},
            "kidney_left": {"level": "organ", "parent": "abdomen", "laterality": "left"}
        }
        
        site_info = site_mapping.get(site, {"level": "organ", "parent": "unknown"})
        
        # Try to get RadLex mapping
        radlex_id = None
        radlex_label = None
        if self.use_radlex and self.radlex_service:
            try:
                concept = self.radlex_service.get_concept_by_text(site)
                if concept:
                    radlex_id = concept.get("iri")
                    radlex_label = concept.get("class_label")
            except Exception:
                pass
        
        return AnatomicLocation(
            name=site,
            radlex_id=radlex_id,
            radlex_label=radlex_label,
            parent_location=site_info.get("parent"),
            level=site_info.get("level"),
            laterality=site_info.get("laterality")
        )
    
    def map_finding_type(self, finding_type: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Map a finding type to RadLex concept."""
        radlex_id = None
        radlex_label = None
        
        if self.use_radlex and self.radlex_service:
            try:
                concept = self.radlex_service.get_concept_by_text(finding_type)
                if concept:
                    radlex_id = concept.get("iri")
                    radlex_label = concept.get("class_label")
            except Exception:
                pass
        
        return finding_type, radlex_id, radlex_label
    
    def create_anatomic_map(self, case_data: Dict[str, Any], patient_id: str, study_date: str) -> AnatomicMap:
        """Create a hierarchical anatomic map from case data."""
        anatomic_map = AnatomicMap(patient_id=patient_id, study_date=study_date)
        
        # Map primary tumor
        if case_data.get("primary"):
            primary = case_data["primary"]
            location = self.map_lung_location(primary["lobe"])
            finding_type, radlex_id, radlex_label = self.map_finding_type("lung mass")
            
            lesion = LesionFinding(
                finding_type="primary_tumor",
                anatomic_location=location,
                size_mm=primary["size_mm"],
                features=primary.get("features", []),
                radlex_id=radlex_id,
                radlex_label=radlex_label,
                target_lesion=True
            )
            anatomic_map.lesions.append(lesion)
        
        # Map lymph nodes
        for node in case_data.get("nodes", []):
            location = self.map_lymph_node_station(node["station"])
            finding_type, radlex_id, radlex_label = self.map_finding_type("enlarged lymph node")
            
            lymph_node = LesionFinding(
                finding_type="lymph_node",
                anatomic_location=location,
                size_mm=node["short_axis_mm"],
                features=[],
                radlex_id=radlex_id,
                radlex_label=radlex_label,
                target_lesion=node["short_axis_mm"] >= 10
            )
            anatomic_map.lymph_nodes.append(lymph_node)
        
        # Map metastases
        for met in case_data.get("mets", []):
            location = self.map_metastatic_site(met["site"])
            finding_type, radlex_id, radlex_label = self.map_finding_type("metastasis")
            
            metastasis = LesionFinding(
                finding_type="metastasis",
                anatomic_location=location,
                size_mm=met["size_mm"],
                features=[],
                radlex_id=radlex_id,
                radlex_label=radlex_label,
                target_lesion=met["size_mm"] >= 10
            )
            anatomic_map.metastases.append(metastasis)
        
        # Build body region hierarchy
        anatomic_map.body_regions = self._build_body_regions(anatomic_map)
        
        return anatomic_map
    
    def _build_body_regions(self, anatomic_map: AnatomicMap) -> Dict[str, Any]:
        """Build hierarchical body regions from findings."""
        regions = {
            "thorax": {
                "lungs": {
                    "right_lung": {"findings": [], "subregions": {}},
                    "left_lung": {"findings": [], "subregions": {}}
                },
                "mediastinum": {
                    "lymph_nodes": {"findings": [], "subregions": {}}
                },
                "pleura": {"findings": [], "subregions": {}}
            }
        }
        
        # Categorize findings by body region
        for lesion in anatomic_map.lesions:
            if lesion.anatomic_location.parent_location == "right_lung":
                regions["thorax"]["lungs"]["right_lung"]["findings"].append({
                    "type": "primary_tumor",
                    "location": lesion.anatomic_location.name,
                    "size_mm": lesion.size_mm,
                    "radlex_id": lesion.radlex_id
                })
            elif lesion.anatomic_location.parent_location == "left_lung":
                regions["thorax"]["lungs"]["left_lung"]["findings"].append({
                    "type": "primary_tumor", 
                    "location": lesion.anatomic_location.name,
                    "size_mm": lesion.size_mm,
                    "radlex_id": lesion.radlex_id
                })
        
        for node in anatomic_map.lymph_nodes:
            regions["thorax"]["mediastinum"]["lymph_nodes"]["findings"].append({
                "type": "lymph_node",
                "station": node.anatomic_location.name,
                "size_mm": node.size_mm,
                "radlex_id": node.radlex_id
            })
        
        return regions


def create_anatomic_map_from_case(case_data: Dict[str, Any], patient_id: str, study_date: str, 
                                 use_radlex: bool = True) -> AnatomicMap:
    """Convenience function to create anatomic map from case data."""
    mapper = RadLexAnatomicMapper(use_radlex=use_radlex)
    return mapper.create_anatomic_map(case_data, patient_id, study_date)
