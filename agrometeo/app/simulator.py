"""
simulator.py — Simule les capteurs IoT pour toutes les parcelles enregistrées.
Tourne dans un thread daemon, se déclenche toutes les 60 secondes.
"""
import threading, time, random
from datetime import datetime, timezone
from app.database import get_db
from app.alertes import analyser_et_sauvegarder

PLAGES = {
    "temperature": {"min":18.0, "max":42.0, "unite":"°C",  "fluctuation":1.5},
    "humidite":    {"min":20.0, "max":95.0, "unite":"%",   "fluctuation":3.0},
    "ph_sol":      {"min":5.5,  "max":8.5,  "unite":"pH",  "fluctuation":0.2},
}
TYPES_CAPTEURS = ["temperature", "humidite", "ph_sol"]
_etat: dict = {}

def _valeur_initiale(t):
    p = PLAGES[t]
    return round(random.uniform((p["min"]+p["max"])/2 - 5, (p["min"]+p["max"])/2 + 5), 2)

def _prochaine_valeur(key, t):
    p = PLAGES[t]
    if key not in _etat:
        _etat[key] = _valeur_initiale(t)
    v = _etat[key] + random.uniform(-p["fluctuation"], p["fluctuation"])
    v = round(max(p["min"], min(p["max"], v)), 2)
    _etat[key] = v
    return v

def _inserer_mesures():
    try:
        db = get_db()
        # Récupérer toutes les parcelles actives
        parcelles = list(db.parcelles.find({"active": True}))
        if not parcelles:
            return

        mesures = []
        for parc in parcelles:
            username     = parc.get("username", "")
            nom_parcelle = parc.get("nom", "")
            for type_cap in TYPES_CAPTEURS:
                cap_id = f"{username}_{nom_parcelle}_{type_cap}".replace(" ", "_")
                valeur = _prochaine_valeur(cap_id, type_cap)
                mesures.append({
                    "capteur_id": cap_id,
                    "parcelle":   nom_parcelle,
                    "username":   username,
                    "type":       type_cap,
                    "valeur":     valeur,
                    "unite":      PLAGES[type_cap]["unite"],
                    "timestamp":  datetime.now(timezone.utc),
                })

        if mesures:
            db.mesures.insert_many(mesures)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {len(mesures)} mesures insérées ({len(parcelles)} parcelles).")
            analyser_et_sauvegarder(mesures)

    except Exception as e:
        print(f"[Simulateur] ⚠️ Erreur : {e}")

def _boucle(intervalle):
    print(f"🚀  Simulateur démarré (intervalle : {intervalle}s).")
    _inserer_mesures()
    while True:
        time.sleep(intervalle)
        _inserer_mesures()

def demarrer_simulateur(intervalle_secondes=60):
    t = threading.Thread(target=_boucle, args=(intervalle_secondes,), daemon=True, name="SimulateurIoT")
    t.start()
    return t
