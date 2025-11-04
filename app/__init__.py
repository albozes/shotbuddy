from flask import Flask
from flask_cors import CORS
from app.services.project_manager import ProjectManager
import logging

def create_app():
    app = Flask(__name__)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    CORS(app)

    # Application-wide services
    app.config['PROJECT_MANAGER'] = ProjectManager()
    app.config['SHOT_MANAGER_CACHE'] = {}

    from app.routes.project_routes import project_bp
    from app.routes.shot_routes import shot_bp
    from app.routes.settings_routes import settings_bp

    # Register blueprints with appropriate prefixes
    app.register_blueprint(project_bp, url_prefix='/')
    app.register_blueprint(shot_bp, url_prefix="/api/shots")
    app.register_blueprint(settings_bp, url_prefix="/api/settings")

    return app
