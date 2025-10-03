"""
Enhanced RadLex resolver for ontology-focused annotation and config generation.
Implements search-first strategy with exact matching and context-aware resolution.
"""

import urllib.parse
import requests
import time
import json
from typing import Optional, Dict, List, Any
from .radlex_service import get_radlex_service


class RadLexResolver:
    """Enhanced RadLex resolver with search-first strategy and context awareness."""
    
    def __init__(self, api_key: str, base_url: str = "https://data.bioontology.org",
                 cache: Optional[dict] = None, rate_limiter=None):
        self.headers = {"Authorization": f"apikey token={api_key}"}
        self.base_url = base_url
        self.cache = cache if cache is not None else {}
        self.rate_limiter = rate_limiter

        # High-value seeds (RID placeholders - replace with validated RIDs)
        self.seed = {
            "lung": {"label": "lung", "iri": "http://radlex.org/RID12780", "rid": "RID12780"},
            "right lung": {"label": "right lung", "iri": "http://radlex.org/RID13168", "rid": "RID13168"},
            "left lung": {"label": "left lung", "iri": "http://radlex.org/RID13169", "rid": "RID13169"},
            "right middle lobe of lung": {"label": "right middle lobe of lung", "iri": "http://radlex.org/RID13171", "rid": "RID13171"},
            "right upper lobe of lung": {"label": "right upper lobe of lung", "iri": "http://radlex.org/RID13170", "rid": "RID13170"},
            "right lower lobe of lung": {"label": "right lower lobe of lung", "iri": "http://radlex.org/RID13172", "rid": "RID13172"},
            "left upper lobe of lung": {"label": "left upper lobe of lung", "iri": "http://radlex.org/RID13173", "rid": "RID13173"},
            "left lower lobe of lung": {"label": "left lower lobe of lung", "iri": "http://radlex.org/RID13174", "rid": "RID13174"},
            "mediastinum": {"label": "mediastinum", "iri": "http://radlex.org/RID1310", "rid": "RID1310"},
            "lymph node": {"label": "lymph node", "iri": "http://radlex.org/RID13176", "rid": "RID13176"},
            "mass": {"label": "mass", "iri": "http://radlex.org/RID49492", "rid": "RID49492"},
            "nodule": {"label": "nodule", "iri": "http://radlex.org/RID49493", "rid": "RID49493"},
            "metastasis": {"label": "metastasis", "iri": "http://radlex.org/RID49494", "rid": "RID49494"},
            "liver": {"label": "liver", "iri": "http://radlex.org/RID12781", "rid": "RID12781"},
            "brain": {"label": "brain", "iri": "http://radlex.org/RID12782", "rid": "RID12782"},
            "bone": {"label": "bone", "iri": "http://radlex.org/RID12783", "rid": "RID12783"},
            "adrenal gland": {"label": "adrenal gland", "iri": "http://radlex.org/RID12784", "rid": "RID12784"},
            "kidney": {"label": "kidney", "iri": "http://radlex.org/RID12785", "rid": "RID12785"},
        }

    def _limit(self):
        """Apply rate limiting if available."""
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()

    def _cache_get(self, k): 
        """Get from cache or seed."""
        return self.cache.get(k) or self.seed.get(k)
    
    def _cache_set(self, k, v): 
        """Set cache value."""
        self.cache[k] = v

    def search_exact(self, query: str) -> Optional[Dict]:
        """Search for exact match in RadLex."""
        self._limit()
        params = {"q": query, "ontologies": "RADLEX", "pagesize": 10, "exact_match": "true"}
        r = requests.get(f"{self.base_url}/search", headers=self.headers, params=params, timeout=30)
        if r.ok:
            for item in r.json().get("collection", []):
                lbl = item.get("prefLabel") or item.get("label")
                if lbl and lbl.lower() == query.lower():
                    return {
                        "label": lbl,
                        "iri": item.get("@id"),
                        "rid": item.get("notation"),
                        "definition": item.get("definition"),
                        "synonyms": item.get("synonym", [])
                    }
        return None

    def search_best(self, query: str) -> Optional[Dict]:
        """Fallback non-exact search (top result)."""
        self._limit()
        params = {"q": query, "ontologies": "RADLEX", "pagesize": 10}
        r = requests.get(f"{self.base_url}/search", headers=self.headers, params=params, timeout=30)
        if r.ok:
            coll = r.json().get("collection", [])
            if coll:
                item = coll[0]
                return {
                    "label": item.get("prefLabel") or item.get("label"),
                    "iri": item.get("@id"),
                    "rid": item.get("notation"),
                    "definition": item.get("definition"),
                    "synonyms": item.get("synonym", [])
                }
        return None

    def fetch_parents(self, iri: str) -> List[Dict]:
        """Fetch parent concepts for a given IRI."""
        self._limit()
        iri_enc = urllib.parse.quote(iri, safe="")
        r = requests.get(f"{self.base_url}/ontologies/RADLEX/classes/{iri_enc}/parents",
                         headers=self.headers, timeout=30)
        if not r.ok: 
            return []
        out = []
        for p in r.json():
            out.append({
                "label": p.get("prefLabel") or p.get("label"),
                "iri": p.get("@id"),
                "rid": p.get("notation")
            })
        return out

    def resolve(self, term: str, context: Optional[List[str]] = None) -> Optional[Dict]:
        """
        Resolve a term with optional context.
        Strategy: cache → exact search → context-boosted query → best search → annotator
        """
        key = term.lower() + "|" + "|".join((context or [])).lower()
        cached = self._cache_get(key) or self._cache_get(term.lower())
        if cached: 
            return cached

        # 1) exact search
        concept = self.search_exact(term)
        if concept:
            self._cache_set(key, concept)
            return concept

        # 2) context-boosted query
        if context:
            q = f"{term} " + " ".join(context)
            concept = self.search_exact(q) or self.search_best(q)
            if concept:
                self._cache_set(key, concept)
                return concept

        # 3) generic best search
        concept = self.search_best(term)
        if concept:
            self._cache_set(key, concept)
            return concept

        # 4) last resort: annotator (span match inside phrase)
        ann = self.annotate_span(term)
        if ann:
            self._cache_set(key, ann)
            return ann

        return None

    def annotate_span(self, text: str) -> Optional[Dict]:
        """Use annotator as fallback (span-based, may overmatch)."""
        self._limit()
        payload = {"text": text}
        params = {"ontologies": "RADLEX", "longest_only": "true", 
                 "include": "prefLabel,synonym,definition,notation"}
        r = requests.post(f"{self.base_url}/annotator",
                          headers={**self.headers, "Content-Type": "application/json"},
                          json=payload, params=params, timeout=30)
        if not r.ok: 
            return None
        ann = r.json()
        if not ann: 
            return None
        cls = ann[0].get("annotatedClass", {})
        return {
            "label": cls.get("prefLabel") or cls.get("label"),
            "iri": cls.get("@id"),
            "rid": cls.get("notation"),
            "definition": cls.get("definition"),
            "synonyms": cls.get("synonym", [])
        }

    def resolve_with_parents(self, term: str, context: Optional[List[str]] = None) -> Optional[Dict]:
        """Resolve term and fetch parent concepts."""
        concept = self.resolve(term, context)
        if concept and concept.get("iri"):
            parents = self.fetch_parents(concept["iri"])
            concept["parents"] = parents
        return concept


def create_radlex_resolver(cache_file: Optional[str] = None) -> RadLexResolver:
    """Create a RadLex resolver instance."""
    svc = get_radlex_service(cache_file=cache_file)
    return RadLexResolver(
        api_key=svc.api_key,
        base_url=svc.base_url,
        cache=svc.cache,
        rate_limiter=svc.rate_limiter
    )


