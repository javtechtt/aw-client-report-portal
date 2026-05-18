"""AW Client Report Portal — Flask app factory."""
import os
from pathlib import Path

import click
from dotenv import load_dotenv
from flask import Flask

from config import CONFIGS
from extensions import db

load_dotenv()


def _ensure_sqlite_parent_dir(uri: str) -> None:
    # Works for both local (database/portal.db) and Railway (e.g. /data/portal.db
    # mounted from a persistent volume). Non-sqlite URIs are ignored.
    if uri.startswith("sqlite:///"):
        Path(uri[len("sqlite:///"):]).parent.mkdir(parents=True, exist_ok=True)


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)

    config_name = config_name or os.getenv("APP_CONFIG", "development")
    app.config.from_object(CONFIGS[config_name])

    _ensure_sqlite_parent_dir(app.config["SQLALCHEMY_DATABASE_URI"])

    db.init_app(app)

    from routes import dashboard, clients, accounts, reports
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(clients.bp)
    app.register_blueprint(accounts.bp)
    app.register_blueprint(reports.bp)

    @app.cli.command("init-db")
    def init_db_command():
        """Create all tables in the SQLite database."""
        import models  # noqa: F401 - ensures models register with SQLAlchemy
        db.create_all()
        click.echo(f"Database initialized at {app.config['SQLALCHEMY_DATABASE_URI']}")

    @app.cli.command("seed")
    def seed_command():
        """Wipe and reseed sample households."""
        from seed import run as run_seed
        run_seed()
        click.echo("Seed complete: 3 sample households inserted.")

    return app


app = create_app()
