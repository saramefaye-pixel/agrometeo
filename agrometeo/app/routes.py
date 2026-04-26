from flask import Blueprint, jsonify, render_template, request, session, redirect, url_for
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.auth import (verifier_identifiants, inscrire_utilisateur,
    enregistrer_connexion, supprimer_connexion, get_sessions_actives,
    login_required, admin_required, set_quota_defaut, get_quota_defaut)

bp = Blueprint("main", __name__)

def _s(doc):
    doc.pop("_id", None)
    if isinstance(doc.get("timestamp"), datetime):
        doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return doc

# ── AUTH ──────────────────────────────────────────────────────────────────────
@bp.route("/login", methods=["GET","POST"])
def login():
    if "username" in session:
        return redirect(url_for("main.index"))
    erreur_login = erreur_inscription = None
    succes_inscription = False
    if request.method == "POST":
        action = request.form.get("action","login")
        if action == "login":
            u = request.form.get("username","").strip().lower()
            p = request.form.get("mot_de_passe","")
            user = verifier_identifiants(u, p)
            if user:
                session["username"]    = u
                session["role"]        = user["role"]
                session["nom_complet"] = user["nom_complet"]
                session["avatar"]      = user["avatar"]
                enregistrer_connexion(u)
                return redirect(url_for("main.index"))
            erreur_login = "Identifiants incorrects."
        else:  # inscription
            nom    = request.form.get("nom_complet","").strip()
            u      = request.form.get("new_username","").strip().lower()
            email  = request.form.get("email","").strip()
            mdp    = request.form.get("new_password","")
            mdp2   = request.form.get("confirm_password","")
            if mdp != mdp2:
                erreur_inscription = "Les mots de passe ne correspondent pas."
            elif not all([nom, u, email, mdp]):
                erreur_inscription = "Tous les champs sont obligatoires."
            else:
                ok, msg = inscrire_utilisateur(nom, u, email, mdp)
                if ok:
                    succes_inscription = True
                else:
                    erreur_inscription = msg
    return render_template("login.html",
        erreur_login=erreur_login,
        erreur_inscription=erreur_inscription,
        succes_inscription=succes_inscription)

@bp.route("/logout")
def logout():
    supprimer_connexion(session.get("username",""))
    session.clear()
    return redirect(url_for("main.login"))

@bp.route("/")
@login_required
def index():
    if session.get("role") == "admin":
        return redirect(url_for("main.admin"))
    return redirect(url_for("main.dashboard"))

@bp.route("/dashboard")
@login_required
def dashboard():
    if session.get("role") == "admin":
        return redirect(url_for("main.admin"))
    db = get_db()
    user = db.utilisateurs.find_one({"username": session["username"]}, {"_id":0,"mot_de_passe_hash":0})
    return render_template("index.html",
        username=session["username"],
        nom_complet=session["nom_complet"],
        avatar=session["avatar"],
        parcelles_user=user.get("parcelles",[]),
        quota=user.get("quota_parcelles",3))

@bp.route("/admin")
@admin_required
def admin():
    db = get_db()
    nb_users = db.utilisateurs.count_documents({"role":"user"})
    return render_template("admin.html",
        nom_complet=session["nom_complet"],
        avatar=session["avatar"],
        nb_utilisateurs=nb_users,
        quota_defaut=get_quota_defaut())

# ── API UTILISATEUR ───────────────────────────────────────────────────────────
@bp.route("/api/mes_parcelles")
@login_required
def mes_parcelles():
    db = get_db()
    user = db.utilisateurs.find_one({"username":session["username"]},{"_id":0})
    return jsonify(user.get("parcelles",[]))

@bp.route("/api/ajouter_parcelle", methods=["POST"])
@login_required
def ajouter_parcelle():
    try:
        db = get_db()
        data = request.get_json()
        nom_parcelle = data.get("nom","").strip()
        if not nom_parcelle:
            return jsonify({"erreur":"Nom de parcelle requis."}), 400
        user = db.utilisateurs.find_one({"username":session["username"]})
        parcelles = user.get("parcelles",[])
        quota = user.get("quota_parcelles",3)
        if len(parcelles) >= quota:
            return jsonify({"erreur":f"Quota atteint ({quota} parcelles maximum)."}), 400
        if nom_parcelle in parcelles:
            return jsonify({"erreur":"Cette parcelle existe déjà."}), 400
        # Ajouter la parcelle à l'utilisateur
        db.utilisateurs.update_one({"username":session["username"]},{"$push":{"parcelles":nom_parcelle}})
        # Créer les capteurs pour cette parcelle
        u = session["username"]
        nouveaux_capteurs = []
        base = db.capteurs.count_documents({"username":u})
        for i, t in enumerate(["temperature","humidite","ph_sol"]):
            cid = f"{u[:3].upper()}{base+i+1:03d}"
            nouveaux_capteurs.append({
                "capteur_id": cid,
                "parcelle": nom_parcelle,
                "type": t,
                "username": u,
            })
        db.capteurs.insert_many(nouveaux_capteurs)
        return jsonify({"ok":True,"parcelle":nom_parcelle})
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

@bp.route("/api/alerte_manuelle", methods=["POST"])
@login_required
def alerte_manuelle():
    try:
        db = get_db()
        data = request.get_json()
        parcelle = data.get("parcelle","")
        message  = data.get("message","").strip()
        if not message or not parcelle:
            return jsonify({"erreur":"Parcelle et message requis."}), 400
        db.alertes.insert_one({
            "niveau": "warning",
            "icone": "📝",
            "titre": f"Alerte manuelle — {parcelle}",
            "message": message,
            "recommandation": "Alerte signalée manuellement par l'utilisateur.",
            "parcelle": parcelle,
            "username": session["username"],
            "valeur": None,
            "timestamp": datetime.now(timezone.utc),
            "type": "manuelle",
        })
        return jsonify({"ok":True})
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

# ── API ADMIN ─────────────────────────────────────────────────────────────────
@bp.route("/api/admin/stats")
@admin_required
def admin_stats():
    try:
        db = get_db()
        une_heure = datetime.now(timezone.utc) - timedelta(hours=1)
        return jsonify({
            "nb_mesures_total":     db.mesures.count_documents({}),
            "nb_mesures_1h":        db.mesures.count_documents({"timestamp":{"$gte":une_heure}}),
            "nb_alertes_critiques": db.alertes.count_documents({"niveau":"critique","timestamp":{"$gte":une_heure}}),
            "nb_alertes_warnings":  db.alertes.count_documents({"niveau":"warning","timestamp":{"$gte":une_heure}}),
            "nb_capteurs":          db.capteurs.count_documents({}),
            "nb_utilisateurs":      db.utilisateurs.count_documents({"role":"user"}),
            "collections": {
                "mesures":         db.mesures.count_documents({}),
                "capteurs":        db.capteurs.count_documents({}),
                "alertes":         db.alertes.count_documents({}),
                "utilisateurs":    db.utilisateurs.count_documents({"role":"user"}),
                "recommandations": db.recommandations.count_documents({}),
            },
            "heure_serveur": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        })
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

@bp.route("/api/admin/utilisateurs")
@admin_required
def admin_utilisateurs():
    try:
        db = get_db()
        users = list(db.utilisateurs.find({"role":"user"},{"_id":0,"mot_de_passe_hash":0}))
        for u in users:
            if isinstance(u.get("date_inscription"), datetime):
                u["date_inscription"] = u["date_inscription"].strftime("%Y-%m-%d")
            u["en_ligne"] = u["username"] in __import__("app.auth", fromlist=["SESSIONS_ACTIVES"]).SESSIONS_ACTIVES
            u["nb_mesures"] = db.mesures.count_documents({"username":u["username"]})
            u["nb_alertes"] = db.alertes.count_documents({"username":u["username"]})
        return jsonify(users)
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

@bp.route("/api/admin/sessions")
@admin_required
def admin_sessions():
    return jsonify(get_sessions_actives())

@bp.route("/api/admin/alertes_recentes")
@admin_required
def admin_alertes_recentes():
    try:
        db = get_db()
        docs = db.alertes.find({}).sort("timestamp",-1).limit(30)
        return jsonify([_s(d) for d in docs])
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

@bp.route("/api/admin/set_quota", methods=["POST"])
@admin_required
def admin_set_quota():
    try:
        data = request.get_json()
        valeur = int(data.get("valeur",3))
        username = data.get("username")
        db = get_db()
        if username:
            db.utilisateurs.update_one({"username":username},{"$set":{"quota_parcelles":valeur}})
        else:
            set_quota_defaut(valeur)
        return jsonify({"ok":True})
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

@bp.route("/api/admin/vider_mesures", methods=["POST"])
@admin_required
def admin_vider_mesures():
    try:
        db = get_db()
        sept_jours = datetime.now(timezone.utc) - timedelta(days=7)
        result = db.mesures.delete_many({"timestamp":{"$lt":sept_jours}})
        return jsonify({"supprimees":result.deleted_count})
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

# ── API COMMUNES ──────────────────────────────────────────────────────────────
@bp.route("/api/status")
@login_required
def status():
    try:
        db = get_db()
        return jsonify({"ok":True,"nb_mesures":db.mesures.count_documents({}),"nb_capteurs":db.capteurs.count_documents({})})
    except Exception as e:
        return jsonify({"ok":False,"erreur":str(e)}), 500

@bp.route("/api/parcelles")
@login_required
def parcelles():
    try:
        db = get_db()
        if session.get("role") == "admin":
            liste = sorted(db.capteurs.distinct("parcelle"))
        else:
            user = db.utilisateurs.find_one({"username":session["username"]})
            liste = user.get("parcelles",[])
        return jsonify(liste)
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

def _filtre_user(filtre=None):
    f = filtre or {}
    return f

@bp.route("/api/mesures")
@login_required
def mesures():
    try:
        parcelle = request.args.get("parcelle")
        type_cap = request.args.get("type")
        limite   = int(request.args.get("limite",100))
        db = get_db()
        filtre = _filtre_user()
        if parcelle: filtre["parcelle"] = parcelle
        if type_cap: filtre["type"] = type_cap
        docs = db.mesures.find(filtre).sort("timestamp",-1).limit(limite)
        return jsonify([_s(d) for d in docs])
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

@bp.route("/api/anomalies")
@login_required
def anomalies():
    try:
        parcelle = request.args.get("parcelle")
        db = get_db()
        filtre = _filtre_user({"type":"humidite","valeur":{"$lt":30}})
        if parcelle: filtre["parcelle"] = parcelle
        docs = db.mesures.find(filtre).sort("timestamp",-1).limit(200)
        return jsonify([_s(d) for d in docs])
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

@bp.route("/api/stats/temperature")
@login_required
def stats_temperature():
    try:
        db = get_db()
        hier = datetime.now(timezone.utc) - timedelta(hours=24)
        match = {"type":"temperature","timestamp":{"$gte":hier}}
        if session.get("role") != "admin":
            match["username"] = session["username"]
        pipeline = [
            {"$match": match},
            {"$group":{"_id":"$parcelle","moyenne":{"$avg":"$valeur"},"min":{"$min":"$valeur"},"max":{"$max":"$valeur"},"nb_mesures":{"$sum":1}}},
            {"$project":{"_id":0,"parcelle":"$_id","moyenne":{"$round":["$moyenne",2]},"min":{"$round":["$min",2]},"max":{"$round":["$max",2]},"nb_mesures":1}},
            {"$sort":{"parcelle":1}}
        ]
        return jsonify(list(db.mesures.aggregate(pipeline)))
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

@bp.route("/api/evolution")
@login_required
def evolution():
    try:
        capteur_id = request.args.get("capteur_id")
        heures = int(request.args.get("heures",24))
        if not capteur_id:
            return jsonify({"erreur":"capteur_id requis"}), 400
        db = get_db()
        debut = datetime.now(timezone.utc) - timedelta(hours=heures)
        match = {"capteur_id":capteur_id,"timestamp":{"$gte":debut}}
        if session.get("role") != "admin":
            match["username"] = session["username"]
        pipeline = [
            {"$match":match},
            {"$group":{"_id":{"heure":{"$dateToString":{"format":"%Y-%m-%d %H:00","date":"$timestamp"}}},"moyenne":{"$avg":"$valeur"},"min":{"$min":"$valeur"},"max":{"$max":"$valeur"}}},
            {"$project":{"_id":0,"heure":"$_id.heure","moyenne":{"$round":["$moyenne",2]},"min":{"$round":["$min",2]},"max":{"$round":["$max",2]}}},
            {"$sort":{"heure":1}}
        ]
        return jsonify(list(db.mesures.aggregate(pipeline)))
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

@bp.route("/api/capteurs")
@login_required
def capteurs():
    try:
        parcelle = request.args.get("parcelle")
        db = get_db()
        filtre = {} if session.get("role")=="admin" else {"username":session["username"]}
        if parcelle: filtre["parcelle"] = parcelle
        return jsonify(list(db.capteurs.find(filtre,{"_id":0})))
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

@bp.route("/api/alertes")
@login_required
def alertes():
    try:
        parcelle = request.args.get("parcelle")
        niveau   = request.args.get("niveau")
        limite   = int(request.args.get("limite",50))
        db = get_db()
        filtre = {} if session.get("role")=="admin" else {"username":session["username"]}
        if parcelle: filtre["parcelle"] = parcelle
        if niveau:   filtre["niveau"] = niveau
        docs = db.alertes.find(filtre).sort("timestamp",-1).limit(limite)
        return jsonify([_s(d) for d in docs])
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

@bp.route("/api/alertes/resume")
@login_required
def alertes_resume():
    try:
        db = get_db()
        une_heure = datetime.now(timezone.utc) - timedelta(hours=1)
        filtre = {"timestamp":{"$gte":une_heure}}
        if session.get("role") != "admin":
            filtre["username"] = session["username"]
        return jsonify({
            "critiques": db.alertes.count_documents({**filtre,"niveau":"critique"}),
            "warnings":  db.alertes.count_documents({**filtre,"niveau":"warning"}),
        })
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500

@bp.route("/api/recommandations")
@login_required
def recommandations():
    try:
        parcelle = request.args.get("parcelle")
        db = get_db()
        match = {}
        if session.get("role") != "admin":
            match["username"] = session["username"]
        if parcelle:
            match["parcelle"] = parcelle
        pipeline = [
            {"$match": match},
            {"$sort":{"timestamp":-1}},
            {"$group":{"_id":"$parcelle","statut":{"$first":"$statut"},"icone":{"$first":"$icone"},"conseil":{"$first":"$conseil"},"temperature":{"$first":"$temperature"},"humidite":{"$first":"$humidite"},"ph_sol":{"$first":"$ph_sol"},"timestamp":{"$first":"$timestamp"}}},
            {"$project":{"_id":0,"parcelle":"$_id","statut":1,"icone":1,"conseil":1,"temperature":1,"humidite":1,"ph_sol":1,"timestamp":1}},
            {"$sort":{"parcelle":1}}
        ]
        docs = list(db.recommandations.aggregate(pipeline))
        return jsonify([_s(d) for d in docs])
    except Exception as e:
        return jsonify({"erreur":str(e)}), 500
@bp.route("/api/simuler_cycle")
def simuler_cycle():
    """Déclenché par un appel externe toutes les minutes."""
    from app.simulator import _inserer_mesures
    _inserer_mesures()
    return jsonify({"ok": True, "heure": datetime.now().strftime("%H:%M:%S")})
