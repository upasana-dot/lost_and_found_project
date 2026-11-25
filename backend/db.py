import os
from pymongo import MongoClient, ASCENDING

USE_MOCK = os.getenv("USE_MOCK_DB", "false").lower() == "true"
if USE_MOCK:
    import mongomock
    client = mongomock.MongoClient()
else:
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=2000)
db = client["blue"]
reports = db["reports"]
reports.create_index([("report_id", ASCENDING)], unique=True)
reports.create_index([("type", ASCENDING), ("status", ASCENDING)])
