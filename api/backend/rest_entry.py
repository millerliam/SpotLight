from flask import Flask
from dotenv import load_dotenv, find_dotenv
import os
import logging
from logging.handlers import RotatingFileHandler

from backend.db_connection import db
from backend.o_and_m.o_and_m_routes import o_and_m
from backend.customers.customer_routes import customer
from backend.spots.spots_route import spots
from backend.orders.orders_routes import orders
from backend.salesman.salesman_route import salesman_bp
from backend.owner.owner_route import owner_bp


def get_env(*keys, default=None, cast=None):
    """
    Return the first non-empty env var among `keys`, else `default`.
    Optionally cast the value (e.g., cast=int). Strips whitespace.
    """
    for k in keys:
        v = os.getenv(k)
        if v is not None and str(v).strip() != "":
            v = str(v).strip()
            return cast(v) if cast else v
    return default if (cast is None or default is None) else cast(default)


def create_app():
    app = Flask(__name__)

    # 1) Logging first (so we see startup/debug info)
    setup_logging(app)

    # 2) Load .env if present (no error if it's missing)
    #    find_dotenv() will locate ./api/.env or any ancestor; override=False preserves OS/Docker vars.
    load_dotenv(find_dotenv(), override=False)

    # 3) App / DB config with sensible defaults and backward-compatible keys
    # SECRET / Flask env
    app.config["SECRET_KEY"] = get_env(
        "SECRET_KEY", "FLASK_SECRET_KEY", "SECRET", default="dev"
    )
    # You can still use FLASK_ENV externally; we don't need to store it in config.

    # Database settings — supports both DB_* and older MYSQL_* names
    app.config["MYSQL_DATABASE_USER"] = get_env(
        "DB_USER", "MYSQL_DATABASE_USER", "MYSQL_USER", default="root"
    )
    app.config["MYSQL_DATABASE_PASSWORD"] = get_env(
        "DB_PASSWORD", "MYSQL_ROOT_PASSWORD", "MYSQL_DATABASE_PASSWORD", "MYSQL_PASSWORD",
        default="changeme"
    )
    app.config["MYSQL_DATABASE_HOST"] = get_env(
        "DB_HOST", "MYSQL_DATABASE_HOST", "MYSQL_HOST",
        # Default to localhost; if you're using docker-compose with a DB service named "db",
        # set DB_HOST=db in your env/compose.
        default="127.0.0.1"
    )
    app.config["MYSQL_DATABASE_PORT"] = get_env(
        "DB_PORT", "MYSQL_DATABASE_PORT", "MYSQL_PORT", default=3306, cast=int
    )
    app.config["MYSQL_DATABASE_DB"] = get_env(
        "DB_NAME", "MYSQL_DATABASE_DB", "MYSQL_DATABASE", "MYSQL_DB",
        default="SpotLight"
    )

    # Log the resolved (non-sensitive) connection info for debugging
    app.logger.info(
        "DB config -> host=%s port=%s user=%s db=%s",
        app.config['MYSQL_DATABASE_HOST'],
        app.config['MYSQL_DATABASE_PORT'],
        app.config['MYSQL_DATABASE_USER'],
        app.config['MYSQL_DATABASE_DB'],
    )

    # 4) Initialize DB and register blueprints
    app.logger.info("current_app(): starting the database connection")
    db.init_app(app)

    app.logger.info("create_app(): registering blueprints with Flask app object.")
    app.register_blueprint(o_and_m, url_prefix="/o_and_m")
    app.register_blueprint(customer, url_prefix="/customer")
    app.register_blueprint(spots, url_prefix="/spots")
    app.register_blueprint(orders)
    app.register_blueprint(salesman_bp)
    app.register_blueprint(owner_bp)

    return app


def setup_logging(app):
    """
    Configure logging for the Flask application in both files and console.
    Creates ./logs if needed and writes rotating logs to logs/api.log
    """
    if not os.path.exists('logs'):
        os.mkdir('logs')

    file_handler = RotatingFileHandler(
        'logs/api.log',
        maxBytes=10240,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.DEBUG)
    app.logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    console_handler.setLevel(logging.DEBUG)
    app.logger.addHandler(console_handler)

    app.logger.setLevel(logging.DEBUG)
    app.logger.info('API startup')
