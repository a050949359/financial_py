from __future__ import annotations

from flask import Flask

from web.routes import web_blueprint


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False

    app.register_blueprint(web_blueprint)
    return app