import os
from app import create_app
from app.database import init_db
from app.auth import init_admin
from app.simulator import demarrer_simulateur

init_db()
init_admin()
demarrer_simulateur(intervalle_secondes=60)
app = create_app()

if __name__ == "__main__":
    app.run()
