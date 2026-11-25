import logging, re
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

log = logging.getLogger(__name__)
WEIGHTS = {"category": .25, "colour": .15, "brand": .10, "location": .15, "time": .10, "description": .25}
CATEGORY_SYNONYMS = {"water bottle":"Bottle","bottle":"Bottle","flask":"Bottle","sipper":"Bottle","tumbler":"Bottle","identity card":"ID Card","id card":"ID Card","id":"ID Card","charger":"Charger","adapter":"Charger","cable":"Charger","backpack":"Bag","rucksack":"Bag","bag":"Bag","sweatshirt":"Clothing","hoodie":"Clothing","hoddie":"Clothing","jacket":"Clothing","ballpoint pen":"Stationery","ball pen":"Stationery","highlighter":"Stationery","marker":"Stationery","pencil":"Stationery","pen":"Stationery","stationery":"Stationery","notebook":"Notebook","wallet":"Wallet","keys":"Keys","key":"Keys"}
COLOUR_GROUPS = [{"navy","dark blue","blue","sky blue","light blue"},{"black","dark black","charcoal"},{"grey","gray","silver"},{"white","off-white","cream"},{"red","maroon"},{"green","dark green"}]
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
        if re.search(rf"\b{re.escape(phrase)}\b", s): return category
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

def _distance_m(a,b):
    if any(a.get(k) is None or b.get(k) is None for k in ("latitude","longitude")): return None
    lat1,lat2=radians(float(a["latitude"])),radians(float(b["latitude"]))
    dlat=lat2-lat1;dlon=radians(float(b["longitude"])-float(a["longitude"]))
    h=sin(dlat/2)**2+cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 6371000*2*asin(sqrt(h))

def score_pair(a,b):
    # Re-normalize the item text so older reports saved as "Other" benefit from new synonyms too.
    ca,cb = normalize_category(a.get("item") or a.get("category")),normalize_category(b.get("item") or b.get("category"))
    cat = 1.0 if ca==cb and ca!="Other" else (0.5 if {ca,cb} in ({"Charger","Electronics"},) else 0.0)
    c1,c2 = (a.get("colour") or "").lower().strip(),(b.get("colour") or "").lower().strip()
    colour = 1.0 if c1==c2 else (.8 if any(c1 in g and c2 in g for g in COLOUR_GROUPS) else 0.0)
    br1,br2=(a.get("brand") or "").strip(),(b.get("brand") or "").strip()
    brand = .5 if not br1 or not br2 else (1.0 if fuzz.ratio(br1.lower(),br2.lower())>=85 else 0.0)
    p1,p2=a.get("place"),b.get("place")
    b1,b2=(a.get("building") or "").strip().lower(),(b.get("building") or "").strip().lower()
    n1,n2=(a.get("location_name") or "").strip().lower(),(b.get("location_name") or "").strip().lower()
    distance=_distance_m(a,b)
    if b1 and b1==b2: location=1.0
    elif n1 and n1==n2: location=1.0
    elif distance is not None and distance<=60: location=1.0
    elif distance is not None and distance<=150: location=.8
    elif distance is not None and distance<=300: location=.5
    else: location=1.0 if p1==p2 else (.4 if p2 in NEARBY.get(p1,set()) else 0.0)
    h=_hours(a,b); time=1 if h<=2 else .7 if h<=24 else .4 if h<=72 else .2 if h<=168 else 0
    desc=_desc(a,b)
    parts={"category":cat,"colour":colour,"brand":brand,"location":location,"time":time,"description":desc}
    score=round(sum(parts[k]*WEIGHTS[k] for k in WEIGHTS)*100)
    if cat==0: score=min(score,35)
    reasons=[]
    reasons.append(f"Same category: {ca}" if cat==1 else f"Category similarity: {ca} / {cb}" if cat else f"Different categories: {ca} / {cb}")
    if colour: reasons.append(f"Same colour: {c1.title()}" if colour==1 else f"Colour similar: {c1.title()} ~ {c2.title()}")
    if brand==1: reasons.append(f"Same brand: {br1}")
    if location: reasons.append(f"Same building: {a.get('building')}" if b1 and b1==b2 else f"Same place: {p1}" if location==1 else f"Nearby places: {p1} / {p2}")
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
