# 🚀 Guide de déploiement — AgroMétéo

## ÉTAPE 1 — Configurer ton URI MongoDB Atlas

Dans le fichier `wsgi.py` et `main.py`, la connexion se fait via la variable
d'environnement `MONGO_URI`. Tu n'as PAS besoin de modifier les fichiers.

## ÉTAPE 2 — Déployer sur Render.com

1. Va sur https://render.com → créer un compte gratuit
2. Clique "New +" → "Web Service"
3. Connecte ton compte GitHub
4. Crée un repo GitHub et pousse le projet :

```bash
cd station_meteo
git init
git add .
git commit -m "AgroMétéo IoT - version finale"
git branch -M main
git remote add origin https://github.com/TON_USERNAME/agrometeo.git
git push -u origin main
```

5. Sur Render, sélectionne le repo
6. Configuration :
   - Name: agrometeo
   - Runtime: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 wsgi:app

7. Dans "Environment Variables", ajoute :
   - Clé: MONGO_URI
   - Valeur: mongodb+srv://fayesokhna828_db_user:TON_VRAI_MOT_DE_PASSE@agrometeo.swgrri6.mongodb.net/station_meteo_agricole?retryWrites=true&w=majority&appName=agrometeo

8. Clique "Create Web Service"

Ton site sera accessible sur : https://agrometeo-XXXX.onrender.com

## Compte admin par défaut
- Username: admin
- Password: Admin@2025
