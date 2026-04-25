import os
from flask import Flask
from flask_session import Session

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "agrometeo-secret-2025-sfi-uasin")
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = os.path.join(os.path.dirname(__file__), "../.flask_sessions")
    app.config["SESSION_PERMANENT"] = False
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    Session(app)
    from app.routes import bp
    app.register_blueprint(bp)
    return app
