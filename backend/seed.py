"""Create a deterministic 150-report demo dataset. Run with USE_MOCK_DB=true for an in-memory database."""
import random
from datetime import datetime, timedelta, timezone
from db import reports
from matching import normalize_category

random.seed(42)
LOCATIONS=["Library","Canteen","Auditorium","Computer Lab","Sports Ground","Parking Area","Classroom","Seminar Hall"]
PAIRS=[("Water Bottle","Navy","Milton","Library","Blue Water Flask","Blue","Milton","Library"),("Black Backpack","Black","Skybags","Canteen","Dark Black Bag","Charcoal","Skybags","Canteen"),("White Charger","White","Boat","Computer Lab","White USB-C Adapter","Off-white","Boat","Computer Lab"),("Grey Hoodie","Grey",None,"Library","Grey Jacket","Gray",None,"Library"),("Red Notebook","Red",None,"Auditorium","Blue Notebook","Blue",None,"Auditorium"),("ID Card","White",None,"Library","Student Identity Card","White",None,"Library"),("Phone Charger","Black","Samsung","Library","Black Charging Cable","Black","Samsung","Library"),("Black Pen","Black","Cello","Classroom","Black Ballpoint Pen","Black","Cello","Classroom")]
def seed():
    # Refresh only internal sample reports; preserve real user submissions.
    reports.delete_many({"is_demo":True}); now=datetime.now(timezone.utc); docs=[]; n=0
    reports.create_index("report_id", unique=True)
    def add(kind,item,colour,brand,place,desc,dt):
        nonlocal n;n+=1;docs.append({"report_id":f"D{n:03d}","type":kind,"item":item,"category":normalize_category(item),"colour":colour,"brand":brand,"place":place,"time":dt,"description":desc,"image_url":None,"status":"open","matched_with":None,"is_demo":True,"created_at":dt+timedelta(minutes=random.randint(1,70))})
    # 40 engineered pairs, including wording variants and plausible near matches.
    for i in range(40):
        pair_index=i%len(PAIRS); p=PAIRS[pair_index]; weak=pair_index==4
        if weak: dt=now-timedelta(days=random.randint(10,13),hours=random.randint(0,15))
        elif pair_index==0: dt=now-timedelta(hours=3)
        elif pair_index==3: dt=now-timedelta(hours=22)
        elif pair_index==7: dt=now-timedelta(hours=2)
        else: dt=now-timedelta(days=random.randint(0,13),hours=random.randint(0,15))
        add("lost",p[0],p[1],p[2],p[3],"Red notebook with lined pages" if weak else "Lost near the campus entrance",dt)
        found_at=dt+timedelta(days=random.randint(1,3)) if weak else dt+timedelta(hours=1) if pair_index in (0,3,7) else dt+timedelta(hours=random.randint(1,20))
        add("found",p[4],p[5],p[6],p[7],"Blue notebook with a blank cover" if weak else "Found near the main entrance",found_at)
    frequent=[("Water Bottle","Bottle"),("ID Card","ID Card"),("Charger","Charger"),("Bottle","Bottle"),("Identity Card","ID Card"),("USB Charger","Charger"),("Notebook","Notebook"),("Wallet","Wallet"),("Backpack","Bag"),("Keys","Keys")]
    weighted_places=["Library"]*5+["Canteen"]*4+["Auditorium"]*3+LOCATIONS[3:]
    for i in range(70):
        item,cat=random.choice(frequent); kind="lost" if i<35 else "found"
        add(kind,item,random.choice(["Blue","Black","White","Navy","Grey"]),random.choice([None,None,"Milton","Samsung","Boat"]),random.choice(weighted_places),"Reported at a busy campus spot",now-timedelta(days=random.randint(0,13),hours=random.randint(0,23)))
    reports.insert_many(docs)
    from collections import Counter
    lost=Counter(d["category"] for d in docs if d["type"]=="lost");hot=Counter(d["place"] for d in docs)
    print("Top most-lost:",lost.most_common(3));print("Top hotspots:",hot.most_common(3));print(f"Seeded {len(docs)} hidden sample reports")
if __name__=="__main__":seed()
