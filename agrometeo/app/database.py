"""
database.py — Connexion MongoDB (local ou Atlas selon la variable d'environnement MONGO_URI)
"""
import os, sys
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

DB_NAME = "station_meteo_agricole"

CAPTEURS_INITIAUX = [
    {"capteur_id":"C001","parcelle":"Parcelle A","type":"temperature"},
    {"capteur_id":"C002","parcelle":"Parcelle A","type":"humidite"},
    {"capteur_id":"C003","parcelle":"Parcelle A","type":"ph_sol"},
    {"capteur_id":"C004","parcelle":"Parcelle B","type":"temperature"},
    {"capteur_id":"C005","parcelle":"Parcelle B","type":"humidite"},
    {"capteur_id":"C006","parcelle":"Parcelle B","type":"ph_sol"},
    {"capteur_id":"C007","parcelle":"Parcelle C","type":"temperature"},
    {"capteur_id":"C008","parcelle":"Parcelle C","type":"humidite"},
    {"capteur_id":"C009","parcelle":"Parcelle C","type":"ph_sol"},
]

def get_db():
    # Priorité : variable d'environnement MONGO_URI (Atlas) sinon localhost
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        return client[DB_NAME]
    except (ConnectionFailure, ServerSelectionTimeoutError):
        print("❌  Impossible de se connecter à MongoDB.")
        sys.exit(1)

def init_db():
    db = get_db()
    db.mesures.create_index([("capteur_id", ASCENDING), ("timestamp", ASCENDING)], name="idx_capteur_timestamp")
    db.mesures.create_index([("timestamp", ASCENDING)], name="idx_timestamp")
    db.mesures.create_index([("username", ASCENDING)], name="idx_username")
    if db.capteurs.count_documents({}) == 0:
        db.capteurs.insert_many(CAPTEURS_INITIAUX)
        print(f"✅  {len(CAPTEURS_INITIAUX)} capteurs insérés.")
    else:
        print(f"✅  Collection capteurs OK ({db.capteurs.count_documents({})} capteurs).")
    return db
