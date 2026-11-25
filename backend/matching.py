import logging, re
from datetime import datetime
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

log = logging.getLogger(__name__)
WEIGHTS = {"category": .25, "colour": .15, "brand": .10, "location": .15, "time": .10, "description": .25}
CATEGORY_SYNONYMS = {"bottle":"Bottle","flask":"Bottle","sipper":"Bottle","tumbler":"Bottle","water bottle":"Bottle","id":"ID Card","id card":"ID Card","identity card":"ID Card","charger":"Charger","adapter":"Charger","cable":"Charger","bag":"Bag","backpack":"Bag","rucksack":"Bag","hoodie":"Clothing","jacket":"Clothing","sweatshirt":"Clothing","notebook":"Notebook","wallet":"Wallet","keys":"Keys","key":"Keys"}
COLOUR_GROUPS = [{"navy","dark blue","blue","sky blue"},{"black","dark black","charcoal"},{"grey","gray","silver"},{"white","off-white","cream"},{"red","maroon"},{"green","dark green"}]
NEARBY = {"Library":{"Computer Lab"},"Computer Lab":{"Library"},"Canteen":{"Auditorium"},"Auditorium":{"Canteen"}}
try:
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer("all-MiniLM-L6-v2")
except Exception as exc:
    _model = None
    log.warning("Sentence embeddings unavailable; using RapidFuzz only: %s", exc)

def normalize_category(item):
    s = re.sub(r"[^a-z0-9 ]", " ", (item or "").lower()).strip()
    for phrase, category in sorted(CATEGORY_SYNONYMS.items(), key=lambda x: -len(x[0])):
        if phrase in s: return category
    return "Other"

def _text(r): return " ".join(str(r.get(k) or "") for k in ("item","colour","brand","description"))
def _desc(a,b):
    fuzzy = fuzz.token_set_ratio(_text(a), _text(b)) / 100
    if _model is None: return fuzzy
    try:
        import numpy as np
        va, vb = _model.encode([_text(a),_text(b)], normalize_embeddings=True)
        cosine = max(0.0, float(np.dot(va,vb)))
        return .5*fuzzy + .5*cosine
    except Exception as exc:
        log.warning("Embedding comparison failed; using RapidFuzz: %s", exc)
        return fuzzy

def _date(v):
    if isinstance(v, datetime): return v.replace(tzinfo=None)
    return datetime.fromisoformat(str(v).replace("Z", "+00:00")).replace(tzinfo=None)

def _hours(a,b): return abs((_date(a["time"])-_date(b["time"])).total_seconds())/3600

def score_pair(a,b):
    ca,cb = normalize_category(a.get("category") or a.get("item")),normalize_category(b.get("category") or b.get("item"))
    cat = 1.0 if ca==cb and ca!="Other" else (0.5 if {ca,cb} in ({"Charger","Electronics"},) else 0.0)
    c1,c2 = (a.get("colour") or "").lower().strip(),(b.get("colour") or "").lower().strip()
    colour = 1.0 if c1==c2 else (.8 if any(c1 in g and c2 in g for g in COLOUR_GROUPS) else 0.0)
    br1,br2=(a.get("brand") or "").strip(),(b.get("brand") or "").strip()
    brand = .5 if not br1 or not br2 else (1.0 if fuzz.ratio(br1.lower(),br2.lower())>=85 else 0.0)
    p1,p2=a.get("place"),b.get("place")
    location=1.0 if p1==p2 else (.4 if p2 in NEARBY.get(p1,set()) else 0.0)
    h=_hours(a,b); time=1 if h<=2 else .7 if h<=24 else .4 if h<=72 else .2 if h<=168 else 0
    desc=_desc(a,b)
    parts={"category":cat,"colour":colour,"brand":brand,"location":location,"time":time,"description":desc}
    score=round(sum(parts[k]*WEIGHTS[k] for k in WEIGHTS)*100)
    if cat==0: score=min(score,35)
    reasons=[]
    reasons.append(f"Same category: {ca}" if cat==1 else f"Category similarity: {ca} / {cb}" if cat else f"Different categories: {ca} / {cb}")
    if colour: reasons.append(f"Same colour: {c1.title()}" if colour==1 else f"Colour similar: {c1.title()} ~ {c2.title()}")
    if brand==1: reasons.append(f"Same brand: {br1}")
    if location: reasons.append(f"Same place: {p1}" if location==1 else f"Nearby places: {p1} / {p2}")
    reasons.append(f"Reported within {h:.0f} hours")
    label="High probability match" if score>=80 else "Possible match" if score>=60 else "Weak match" if score>=40 else None
    return score,parts,label,reasons

def find_matches(report, limit=5):
    from db import reports
    opposite="found" if report["type"]=="lost" else "lost"
    results=[]
    for candidate in reports.find({"type":opposite,"status":"open"}):
        if candidate.get("report_id")==report.get("report_id"): continue
        score,breakdown,label,reasons=score_pair(report,candidate)
        if label: results.append({"report":candidate,"score":score,"breakdown":breakdown,"label":label,"reasons":reasons})
    results.sort(key=lambda m:m["score"],reverse=True)
    return results[:limit]
