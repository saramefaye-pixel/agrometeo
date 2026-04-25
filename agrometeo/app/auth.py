"""
auth.py — Authentification complète avec MongoDB + inscription réelle.
Mots de passe hashés avec werkzeug.security.
"""
from flask import session, redirect, url_for
from functools import wraps
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import get_db

SESSIONS_ACTIVES: dict = {}

def init_admin():
    try:
        db = get_db()
        if not db.utilisateurs.find_one({"username": "admin"}):
            db.utilisateurs.insert_one({
                "username": "admin",
                "nom_complet": "Administrateur",
                "email": "admin@agrometeo.sn",
                "mot_de_passe_hash": generate_password_hash("Admin@2025"),
                "role": "admin",
                "avatar": "👨‍💼",
                "date_inscription": datetime.now(timezone.utc),
                "parcelles": [],
                "quota_parcelles": 99,
            })
            print("✅  Admin créé — login: admin / Admin@2025")
        else:
            print("✅  Admin existant.")
    except Exception as e:
        print(f"⚠️  Erreur init admin: {e}")

def enregistrer_connexion(username):
    SESSIONS_ACTIVES[username] = {
        "depuis": datetime.now(timezone.utc),
        "derniere_activite": datetime.now(timezone.utc),
    }

def supprimer_connexion(username):
    SESSIONS_ACTIVES.pop(username, None)

def mettre_a_jour_activite(username):
    if username in SESSIONS_ACTIVES:
        SESSIONS_ACTIVES[username]["derniere_activite"] = datetime.now(timezone.utc)

def get_sessions_actives():
    db = get_db()
    resultat = []
    for username, info in SESSIONS_ACTIVES.items():
        user = db.utilisateurs.find_one({"username": username}, {"_id":0,"mot_de_passe_hash":0})
        if not user:
            continue
        depuis = info["depuis"]
        duree_min = int((datetime.now(timezone.utc) - depuis).total_seconds() / 60)
        resultat.append({
            "username": username,
            "nom_complet": user.get("nom_complet", username),
            "email": user.get("email",""),
            "role": user.get("role","user"),
            "avatar": user.get("avatar","👤"),
            "depuis": depuis.strftime("%H:%M:%S"),
            "duree_min": duree_min,
            "nb_parcelles": len(user.get("parcelles",[])),
            "quota_parcelles": user.get("quota_parcelles", 3),
        })
    return resultat

def inscrire_utilisateur(nom_complet, username, email, mot_de_passe):
    try:
        db = get_db()
        username = username.strip().lower()
        email = email.strip().lower()
        if db.utilisateurs.find_one({"username": username}):
            return False, "Ce nom d'utilisateur est déjà pris."
        if db.utilisateurs.find_one({"email": email}):
            return False, "Cette adresse email est déjà utilisée."
        if len(mot_de_passe) < 6:
            return False, "Le mot de passe doit contenir au moins 6 caractères."
        quota = get_quota_defaut()
        db.utilisateurs.insert_one({
            "username": username,
            "nom_complet": nom_complet.strip(),
            "email": email,
            "mot_de_passe_hash": generate_password_hash(mot_de_passe),
            "role": "user",
            "avatar": "👩‍🌾",
            "date_inscription": datetime.now(timezone.utc),
            "parcelles": [],
            "quota_parcelles": quota,
        })
        return True, ""
    except Exception as e:
        return False, f"Erreur serveur : {e}"

def verifier_identifiants(username, mot_de_passe):
    try:
        db = get_db()
        user = db.utilisateurs.find_one({"username": username.strip().lower()})
        if user and check_password_hash(user["mot_de_passe_hash"], mot_de_passe):
            return user
        return None
    except Exception:
        return None

def get_quota_defaut():
    try:
        db = get_db()
        cfg = db.config.find_one({"cle": "quota_parcelles_defaut"})
        return cfg["valeur"] if cfg else 3
    except Exception:
        return 3

def set_quota_defaut(valeur):
    try:
        db = get_db()
        db.config.update_one({"cle":"quota_parcelles_defaut"},{"$set":{"valeur":valeur}},upsert=True)
    except Exception as e:
        print(f"Erreur set_quota: {e}")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("main.login"))
        mettre_a_jour_activite(session["username"])
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("main.login"))
        if session.get("role") != "admin":
            return redirect(url_for("main.dashboard"))
        mettre_a_jour_activite(session["username"])
        return f(*args, **kwargs)
    return decorated
