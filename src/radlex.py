import os, requests, urllib.parse

API_KEY = os.environ.get("BIOPORTAL_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing BIOPORTAL_API_KEY")
BASE = "https://data.bioontology.org"
HEAD = {"Authorization": f"apikey token={API_KEY}"}

text = "CT chest shows right upper lobe ground-glass nodule and mediastinal lymphadenopathy."

# --- Option A: ask Annotator to include prefLabel/synonyms directly ---
annot_r = requests.post(
    f"{BASE}/annotator",
    headers={**HEAD, "Content-Type": "application/json"},
    json={"text": text},
    params={
        "ontologies": "RADLEX",
        "longest_only": "true",
        # key line:
        "include": "prefLabel,synonym,definition,notation"
    }
)
annot_r.raise_for_status()
annots = annot_r.json()

print("Annotations (Annotator include):")
for a in annots:
    cls = a.get("annotatedClass", {})
    # some builds still won’t return prefLabel here; fall back to Option B below
    print("-", cls.get("prefLabel"), cls.get("@id"))

# --- Option B: robust — follow each class IRI to fetch its label ---
def fetch_label(class_iri: str):
    # URL-encode the IRI for the class endpoint
    iri_enc = urllib.parse.quote(class_iri, safe="")
    url = f"{BASE}/ontologies/RADLEX/classes/{iri_enc}"
    r = requests.get(url, headers=HEAD)
    if r.status_code == 404 and class_iri.startswith("http://radlex.org"):
        # normalize older IRIs without 'www.'
        iri_enc = urllib.parse.quote(class_iri.replace("http://radlex.org", "http://www.radlex.org"), safe="")
        r = requests.get(f"{BASE}/ontologies/RADLEX/classes/{iri_enc}", headers=HEAD)
    r.raise_for_status()
    js = r.json()
    return js.get("prefLabel") or js.get("label") or js.get("notation")

# Build tidy spans → concepts table
tidy = []
for a in annots:
    span = a.get("annotations", [{}])[0]  # first span for this match
    txt = span.get("text")
    cls = a.get("annotatedClass", {})
    iri = cls.get("@id")
    if not iri:
        continue
    label = cls.get("prefLabel")  # may already exist (Option A)
    if not label:
        label = fetch_label(iri)
    tidy.append({
        "match_text": txt,
        "class_label": label,
        "class_iri": iri,
    })

# Deduplicate by (label, iri, match_text)
seen, deduped = set(), []
for row in tidy:
    k = (row["match_text"], row["class_iri"])
    if k not in seen:
        seen.add(k)
        deduped.append(row)

print("\nResolved annotations:")
for row in deduped:
    print(f"- {row['match_text']} → {row['class_label']} ({row['class_iri']})")
