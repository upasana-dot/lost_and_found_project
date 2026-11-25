from datetime import datetime, timezone, timedelta
from pathlib import Path
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from db import reports, USE_MOCK
from models import ReportCreate, ReuniteRequest
from matching import find_matches

LOCATIONS={"Library":(27.4924,77.6737),"Canteen":(27.4927,77.6741),"Auditorium":(27.4920,77.6742),"Computer Lab":(27.4925,77.6744),"Sports Ground":(27.4917,77.6738),"Parking Area":(27.4929,77.6734),"Classroom":(27.4922,77.6735),"Seminar Hall":(27.4928,77.6745)}
app=FastAPI(title="BLUE Campus Lost & Found",version="1.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173"],allow_methods=["*"],allow_headers=["*"])
UPLOADS=Path(__file__).parent/"uploads"; UPLOADS.mkdir(exist_ok=True)
app.mount("/uploads",StaticFiles(directory=UPLOADS),name="uploads")
@app.on_event("startup")
def seed_mock_on_startup():
    # mongomock is process-local, so populate the API process when it starts.
    if USE_MOCK and reports.count_documents({}) == 0:
        from seed import seed
        seed()
def clean(doc):
    if not doc:return None
    doc=dict(doc);doc.pop("_id",None)
    for k,v in doc.items():
        if isinstance(v,datetime):doc[k]=v.isoformat()
    return doc
@app.get("/api/locations")
def locations():return [{"place":p,"lat":v[0],"lng":v[1]} for p,v in LOCATIONS.items()]
@app.post("/api/reports/{kind}")
def create_report(kind:str,body:ReportCreate):
    if kind not in ("lost","found"):raise HTTPException(404,"Report type must be lost or found")
    if body.place not in LOCATIONS:raise HTTPException(422,"Unknown campus location")
    now=datetime.now(timezone.utc); seq=reports.count_documents({})+1; rid=f"R{seq:03d}"
    data=body.model_dump(exclude={"force"}); data.update(report_id=rid,type=kind,category=__import__("matching").normalize_category(body.item),time=body.time,status="open",matched_with=None,created_at=now)
    duplicate=reports.find_one({"type":kind,"status":"open","item":{"$regex":f"^{body.item}$","$options":"i"},"colour":{"$regex":f"^{body.colour}$","$options":"i"},"place":body.place,"time":{"$gte":body.time-timedelta(hours=1),"$lte":body.time+timedelta(hours=1)}})
    if duplicate and not body.force:return {"warning":"Possible duplicate report","duplicate":clean(duplicate),"report":None,"matches":[]}
    reports.insert_one(data); matches=find_matches(data)
    return {"report":clean(data),"matches":[{**m,"report":clean(m["report"])} for m in matches]}
@app.get("/api/reports")
def list_reports(type:str|None=None,status:str|None=None,place:str|None=None,limit:int=100):
    q={k:v for k,v in (("type",type),("status",status),("place",place)) if v}
    return [clean(x) for x in reports.find(q).sort("created_at",-1).limit(min(max(limit,1),500))]
@app.get("/api/reports/{report_id}")
def get_report(report_id:str):
    r=reports.find_one({"report_id":report_id})
    if not r:raise HTTPException(404,"Report not found")
    return clean(r)
@app.get("/api/matches/{report_id}")
def matches(report_id:str):
    r=reports.find_one({"report_id":report_id})
    if not r:raise HTTPException(404,"Report not found")
    return [{**m,"report":clean(m["report"])} for m in find_matches(r)]
@app.post("/api/reports/{report_id}/reunite")
def reunite(report_id:str,body:ReuniteRequest):
    a=reports.find_one({"report_id":report_id}); b=reports.find_one({"report_id":body.matched_with})
    if not a or not b:raise HTTPException(404,"Both reports must exist")
    if a["type"]==b["type"]:raise HTTPException(400,"Reports must be opposite types")
    reports.update_one({"report_id":a["report_id"]},{"$set":{"status":"reunited","matched_with":b["report_id"]}})
    reports.update_one({"report_id":b["report_id"]},{"$set":{"status":"reunited","matched_with":a["report_id"]}})
    return {"report":clean(reports.find_one({"report_id":report_id})),"matched":clean(reports.find_one({"report_id":body.matched_with}))}
@app.post("/api/upload")
def upload(file:UploadFile=File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):raise HTTPException(415,"Upload an image")
    name=f"{datetime.now().timestamp():.0f}_{Path(file.filename or 'photo').name}"
    with (UPLOADS/name).open("wb") as out:shutil.copyfileobj(file.file,out)
    return {"image_url":f"http://localhost:8000/uploads/{name}"}
@app.get("/api/stats")
def stats():
    total=reports.count_documents({}); lost=reports.count_documents({"type":"lost"}); found=reports.count_documents({"type":"found"}); reunited=reports.count_documents({"status":"reunited"})//2
    return {"total_lost":lost,"total_found":found,"total_reunited":reunited,"reunification_rate":round(reunited/max(lost,found,1)*100,1),"open_reports":reports.count_documents({"status":"open"})}
@app.get("/api/insights")
def insights():
    from insights import build_insights
    return build_insights()
@app.get("/api/alerts")
def alerts(report_id:str):return [{"report":clean(m["report"]),"score":m["score"],"label":m["label"],"reasons":m["reasons"]} for m in matches(report_id) if m["score"]>=80]
