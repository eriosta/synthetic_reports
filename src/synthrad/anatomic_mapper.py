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
from .radlex_resolver import create_radlex_resolver


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
        self.resolver = None
        self.cache_file = cache_file
        
        if use_radlex:
            try:
                self.radlex_service = get_radlex_service(cache_file=cache_file)
                self.resolver = create_radlex_resolver(cache_file=cache_file)
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
        laterality = "right" if lobe in ["RUL","RML","RLL"] else ("left" if lobe in ["LUL","LLL"] else None)
        parent = "right_lung" if laterality=="right" else ("left_lung" if laterality=="left" else None)
        
        # Compose canonical text
        lobe_map = {"RUL":"right upper lobe of lung","RML":"right middle lobe of lung",
                    "RLL":"right lower lobe of lung","LUL":"left upper lobe of lung","LLL":"left lower lobe of lung"}
        term = lobe_map.get(lobe, lobe)
        
        radlex_id = radlex_label = None
        if self.use_radlex and self.resolver:
            try:
                c = self.resolver.resolve(term, context=["lung","lobe"])
                if c:
                    radlex_id, radlex_label = c.get("iri"), c.get("label")
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
        laterality = "right" if station.endswith("R") else ("left" if station.endswith("L") else "central")
        
        # Prefer standard phrase for stations
        term = f"mediastinal lymph node station {station}"
        
        radlex_id = radlex_label = None
        if self.use_radlex and self.resolver:
            try:
                c = self.resolver.resolve(term, context=["mediastinum","lymph node","station"])
                if c:
                    radlex_id, radlex_label = c.get("iri"), c.get("label")
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
        site_map = {
            "liver": "liver", "brain": "brain", "bone": "bone",
            "adrenal_right": "right adrenal gland", "adrenal_left": "left adrenal gland",
            "kidney_right": "right kidney", "kidney_left": "left kidney"
        }
        term = site_map.get(site, site)
        parent = "abdomen" if "adrenal" in site or "liver" in site or "kidney" in site else "unknown"
        laterality = "right" if "right" in term else ("left" if "left" in term else None)
        level = "organ" if term not in ["bone"] else "system"

        radlex_id = radlex_label = None
        if self.use_radlex and self.resolver:
            try:
                c = self.resolver.resolve(term, context=["organ"])
                if c:
                    radlex_id, radlex_label = c.get("iri"), c.get("label")
            except Exception:
                pass

        return AnatomicLocation(
            name=site, radlex_id=radlex_id, radlex_label=radlex_label,
            parent_location=parent, level=level, laterality=laterality
        )
    
    def map_finding_type(self, finding_type: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Map a finding type to RadLex concept."""
        # prefer controlled forms
        canonical = {
            "primary_tumor": "mass", "lung mass": "mass",
            "lymph_node": "lymph node", "enlarged lymph node": "lymph node",
            "metastasis": "metastasis", "nodule": "nodule"
        }.get(finding_type.lower(), finding_type)
        
        radlex_id = radlex_label = None
        if self.use_radlex and self.resolver:
            try:
                c = self.resolver.resolve(canonical, context=["imaging finding"])
                if c:
                    radlex_id, radlex_label = c.get("iri"), c.get("label")
            except Exception:
                pass
        
        return canonical, radlex_id, radlex_label
    
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
