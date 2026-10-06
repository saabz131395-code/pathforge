"""PathForge Flask application factory."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template

from database.init_db import DEFAULT_DB, initialize_database

from . import db
from .routes.intake import intake_bp
from .routes.paths import paths_bp


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    # Absolute path, so the app works no matter which folder it is started from.
    app.config['DATABASE'] = os.environ.get('PATHFORGE_DATABASE', str(DEFAULT_DB))
    if test_config:
        app.config.update(test_config)

    # First run on a fresh clone: build the database automatically.
    if not Path(app.config['DATABASE']).exists():
        initialize_database(app.config['DATABASE'])

    db.init_app(app)
    app.register_blueprint(intake_bp)
    app.register_blueprint(paths_bp)

    @app.template_filter('friendly_date')
    def friendly_date(value):
        if not value:
            return 'Not checked yet'
        try:
            return datetime.strptime(str(value), '%Y-%m-%d').strftime('%d %b %Y')
        except ValueError:
            return str(value)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template('error.html', code=404, title='Page not found',
                               message='That page or career path does not exist.'), 404

    @app.errorhandler(400)
    def bad_request(_error):
        return render_template('error.html', code=400, title='Something was missing',
                               message='Please choose an option and try again.'), 400

    return app
