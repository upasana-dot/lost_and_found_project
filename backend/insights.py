import pandas as pd
from datetime import datetime
from db import reports
from locations import LOCATIONS

def build_insights():
    rows=list(reports.find({"is_demo":{"$ne":True}}, {"_id":0}))
    df=pd.DataFrame(rows)
    places=[]
    for place,coords in LOCATIONS.items():
        group=df[df.place==place] if not df.empty and "place" in df else pd.DataFrame()
        places.append({"place":place,"lat":coords[0],"lng":coords[1],"count":len(group),"lost":int((group.type=="lost").sum()) if len(group) else 0,"found":int((group.type=="found").sum()) if len(group) else 0})
    lost=df[df.type=="lost"] if not df.empty else df
    top_items=lost.groupby("category").size().sort_values(ascending=False).head(3).reset_index(name="count").to_dict("records") if len(lost) else []
    hotspots=sorted(places,key=lambda x:x["count"],reverse=True)[:3]
    daily=[]
    if len(df):
        temp=df.copy(); temp["day"]=pd.to_datetime(temp.time).dt.strftime("%Y-%m-%d")
        daily=temp.groupby(["day","type"]).size().unstack(fill_value=0).reset_index().to_dict("records")
    counts=df.status.value_counts().to_dict() if len(df) else {}
    return {"top_items":top_items,"hotspots":hotspots,"by_place":places,"by_day":daily,"match_stats":counts}
