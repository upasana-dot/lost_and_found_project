from datetime import datetime, timezone, timedelta
from pathlib import Path
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from db import reports
from models import ReportCreate, ReuniteRequest
from matching import find_matches
from locations import LOCATIONS, BUILDINGS

app=FastAPI(title="findyourloss · Campus Lost & Found",version="1.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173"],allow_methods=["*"],allow_headers=["*"])
UPLOADS=Path(__file__).parent/"uploads"; UPLOADS.mkdir(exist_ok=True)
app.mount("/uploads",StaticFiles(directory=UPLOADS),name="uploads")
@app.on_event("startup")
def seed_empty_demo_database():
    # Migrate the former visible seed records without touching actual later submissions.
    legacy_ids=[f"R{i:03d}" for i in range(1,151)]
    legacy=list(reports.find({"report_id":{"$in":legacy_ids},"is_demo":{"$exists":False}}, {"report_id":1,"description":1}))
    old_seed_text={"Lost near the campus entrance","Found near the main entrance","Red notebook with lined pages","Blue notebook with a blank cover","Reported at a busy campus spot"}
    if len(legacy)>=140 and sum(r.get("description") in old_seed_text for r in legacy)>=120:
        reports.update_many({"report_id":{"$in":legacy_ids},"is_demo":{"$exists":False}},{"$set":{"is_demo":True}})
    # Hidden sample reports make first-run matching demonstrable; real reports remain separate in views.
    if reports.count_documents({"is_demo":True,"category":"Stationery"}) == 0:
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
@app.get("/api/buildings")
def buildings():return [{"building":name,**coords} for name,coords in BUILDINGS.items()]
@app.post("/api/reports/{kind}")
def create_report(kind:str,body:ReportCreate):
    if kind not in ("lost","found"):raise HTTPException(404,"Report type must be lost or found")
    if body.place not in LOCATIONS:raise HTTPException(422,"Unknown campus location")
    now=datetime.now(timezone.utc); seq=reports.count_documents({"is_demo":{"$ne":True}})+1; rid=f"R{seq:03d}"
    data=body.model_dump(exclude={"force"}); data.update(report_id=rid,type=kind,category=__import__("matching").normalize_category(body.item),time=body.time,status="open",matched_with=None,created_at=now)
    duplicate=reports.find_one({"type":kind,"status":"open","is_demo":{"$ne":True},"item":{"$regex":f"^{body.item}$","$options":"i"},"colour":{"$regex":f"^{body.colour}$","$options":"i"},"place":body.place,"time":{"$gte":body.time-timedelta(hours=1),"$lte":body.time+timedelta(hours=1)}})
    if duplicate and not body.force:return {"warning":"Possible duplicate report","duplicate":clean(duplicate),"report":None,"matches":[]}
    reports.insert_one(data); matches=find_matches(data)
    return {"report":clean(data),"matches":[{**m,"report":clean(m["report"])} for m in matches]}
@app.get("/api/reports")
def list_reports(type:str|None=None,status:str|None=None,place:str|None=None,limit:int=100):
    q={k:v for k,v in (("type",type),("status",status),("place",place)) if v}
    q["is_demo"]={"$ne":True}
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
    if a.get("is_demo") or b.get("is_demo"):raise HTTPException(409,"Demo matches are suggestions only; chat and reunite real reports after another user submits a matching item")
    if a["type"]==b["type"]:raise HTTPException(400,"Reports must be opposite types")
    reports.update_one({"report_id":a["report_id"]},{"$set":{"status":"reunited","matched_with":b["report_id"]}})
    reports.update_one({"report_id":b["report_id"]},{"$set":{"status":"reunited","matched_with":a["report_id"]}})
    return {"report":clean(reports.find_one({"report_id":report_id})),"matched":clean(reports.find_one({"report_id":body.matched_with}))}
@app.get("/api/reports/{report_id}/chat")
def get_chat(report_id:str,with_report_id:str):
    a=reports.find_one({"report_id":report_id}); b=reports.find_one({"report_id":with_report_id})
    if not a or not b:raise HTTPException(404,"Both reports must exist")
    if a.get("is_demo") or b.get("is_demo"):raise HTTPException(409,"Demo suggestions do not have a real reporter chat")
    if a["type"]==b["type"]:raise HTTPException(400,"Chat is only available for opposite report types")
    messages=[m for m in a.get("chat_messages",[]) if m.get("with_report_id")==with_report_id]
    return {"messages":messages,"report":clean(a),"matched":clean(b)}
@app.post("/api/reports/{report_id}/chat")
def send_chat(report_id:str,body:dict):
    other_id=body.get("with_report_id"); message=(body.get("message") or "").strip()
    if not other_id or not message:raise HTTPException(422,"with_report_id and message are required")
    if len(message)>1000:raise HTTPException(422,"Message must be 1000 characters or fewer")
    a=reports.find_one({"report_id":report_id}); b=reports.find_one({"report_id":other_id})
    if not a or not b:raise HTTPException(404,"Both reports must exist")
    if a.get("is_demo") or b.get("is_demo"):raise HTTPException(409,"Demo suggestions do not have a real reporter chat")
    if a["type"]==b["type"]:raise HTTPException(400,"Chat is only available for opposite report types")
    entry={"sender_report_id":report_id,"with_report_id":other_id,"message":message,"created_at":datetime.now(timezone.utc).isoformat()}
    other_entry={**entry,"with_report_id":report_id}
    reports.update_one({"report_id":report_id},{"$push":{"chat_messages":entry}})
    reports.update_one({"report_id":other_id},{"$push":{"chat_messages":other_entry}})
    return {"message":entry}
@app.post("/api/upload")
def upload(file:UploadFile=File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):raise HTTPException(415,"Upload an image")
    name=f"{datetime.now().timestamp():.0f}_{Path(file.filename or 'photo').name}"
    with (UPLOADS/name).open("wb") as out:shutil.copyfileobj(file.file,out)
    return {"image_url":f"http://localhost:8000/uploads/{name}"}
@app.get("/api/stats")
def stats():
    real={"is_demo":{"$ne":True}}
    total=reports.count_documents(real); lost=reports.count_documents({**real,"type":"lost"}); found=reports.count_documents({**real,"type":"found"}); reunited=reports.count_documents({**real,"status":"reunited"})//2
    return {"total_lost":lost,"total_found":found,"total_reunited":reunited,"reunification_rate":round(reunited/max(lost,found,1)*100,1),"open_reports":reports.count_documents({**real,"status":"open"})}
@app.get("/api/insights")
def insights():
    from insights import build_insights
    return build_insights()
@app.get("/api/alerts")
def alerts(report_id:str):return [{"report":clean(m["report"]),"score":m["score"],"label":m["label"],"reasons":m["reasons"]} for m in matches(report_id) if m["score"]>=80]
