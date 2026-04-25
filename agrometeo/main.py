import os
from app import create_app
from app.database import init_db
from app.auth import init_admin
from app.simulator import demarrer_simulateur

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  🌾  AgroMétéo — Station Météo Agricole IoT")
    print("="*55)
    print("\n🔌  Connexion à MongoDB...")
    init_db()
    print("\n👤  Initialisation du compte admin...")
    init_admin()
    print("\n📡  Démarrage du simulateur IoT...")
    demarrer_simulateur(intervalle_secondes=60)
    print("\n🌐  Serveur démarré sur http://localhost:5000")
    print("    Compte admin : admin / Admin@2025")
    print("\n" + "="*55 + "\n")
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port, use_reloader=False)
