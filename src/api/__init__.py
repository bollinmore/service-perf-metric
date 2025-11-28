from __future__ import annotations

from flask import Flask

from src.api.routes.comparisons import bp as comparisons_bp
from src.api.routes.downloads import bp as downloads_bp
from src.api.routes.versions import bp as versions_bp


def create_app() -> Flask:
    """Flask app factory for comparison APIs."""
    app = Flask(__name__)
    app.register_blueprint(versions_bp)
    app.register_blueprint(comparisons_bp)
    app.register_blueprint(downloads_bp)
    return app
