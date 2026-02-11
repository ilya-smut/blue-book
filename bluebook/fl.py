"""Main Flask application module for Bluebook.

This module initializes the Flask application, registers blueprints,
and provides the CLI entry point for starting the server.
"""

import contextlib
import os
import secrets
from logging.config import dictConfig
from pathlib import Path

import click
from flask import Flask
from flask_session import Session

from bluebook import configuration
from bluebook.routes import (
    exams_bp,
    files_bp,
    main_bp,
    prompts_bp,
    questions_bp,
)


def _get_or_create_secret_key() -> bytes:
    """Get secret key from environment or generate and persist one.

    Returns:
        bytes: The secret key for Flask session encryption.
    """
    # First, check for environment variable
    env_key = os.environ.get("FLASK_SECRET_KEY")
    if env_key:
        return env_key.encode() if isinstance(env_key, str) else env_key

    # If not in env, try to load from persistent file
    secret_key_path = configuration.Configuration.SystemPath.CONFIG_DIR / ".secret_key"
    if secret_key_path.exists():
        return secret_key_path.read_bytes()

    # Generate new key and persist it
    new_key = secrets.token_bytes(32)
    with contextlib.suppress(OSError):
        secret_key_path.write_bytes(new_key)
    return new_key


def create_app() -> Flask:
    """Application factory for creating the Flask app.

    Returns:
        Flask: The configured Flask application instance.
    """
    # Compute the directory of the current file
    app_dir = Path(__file__).resolve().parent

    # Set the absolute paths for templates and static folders
    template_dir = Path(app_dir) / "templates"
    static_dir = Path(app_dir) / "static"

    # Initialize the application
    app = Flask("blue-book", template_folder=template_dir, static_folder=static_dir)
    app.secret_key = _get_or_create_secret_key()

    # Use server-side filesystem sessions to avoid the 4KB cookie size limit.
    # Only a small session ID cookie is sent to the browser.
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = str(
        configuration.Configuration.SystemPath.SESSION_DIR,
    )
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_USE_SIGNER"] = True
    app.config["SESSION_FILE_THRESHOLD"] = 100
    Session(app)

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(exams_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(prompts_bp)

    return app


# Create the app instance for direct use
app = create_app()


@click.group()
def bluebook() -> None:
    """
    Blue Book - advanced preparation questions generator for any exam.
    Based on gemini-flash-lite model.
    This is a command line interface for the Blue Book application.
    """


@bluebook.command()
@click.option(
    "--debug", is_flag=True, show_default=True, default=False, help="Run flask app in debug mode",
)
def start(debug: bool) -> None:
    """
    Start web server for Blue Book application.
    """
    if debug:
        dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                    },
                },
                "handlers": {
                    "wsgi": {
                        "class": "logging.StreamHandler",
                        "stream": "ext://flask.logging.wsgi_errors_stream",
                        "formatter": "default",
                    },
                },
                "root": {"level": "INFO", "handlers": ["wsgi"]},
                "loggers": {
                    "bluebook.database_manager": {
                        "level": "DEBUG",
                        "handlers": ["wsgi"],
                        "propagate": False,
                    },
                    "bluebook.generator": {
                        "level": "DEBUG",
                        "handlers": ["wsgi"],
                        "propagate": False,
                    },
                    "bluebook.token_manager": {
                        "level": "DEBUG",
                        "handlers": ["wsgi"],
                        "propagate": False,
                    },
                    "bluebook.data_models": {
                        "level": "DEBUG",
                        "handlers": ["wsgi"],
                        "propagate": False,
                    },
                    "bluebook.helpers.file_attachment": {
                        "level": "DEBUG",
                        "handlers": ["wsgi"],
                        "propagate": False,
                    },
                    "bluebook.services.exam_service": {
                        "level": "DEBUG",
                        "handlers": ["wsgi"],
                        "propagate": False,
                    },
                    "bluebook.services.question_service": {
                        "level": "DEBUG",
                        "handlers": ["wsgi"],
                        "propagate": False,
                    },
                },
            },
        )
        app.run(host="0.0.0.0", port=5000, debug=True, load_dotenv=True)  # noqa: S104
    else:
        dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                    },
                },
                "handlers": {
                    "wsgi": {
                        "class": "logging.StreamHandler",
                        "stream": "ext://flask.logging.wsgi_errors_stream",
                        "formatter": "default",
                    },
                },
                "root": {"level": "INFO", "handlers": ["wsgi"]},
            },
        )
        app.run(host="0.0.0.0", port=5000, debug=False, load_dotenv=True)  # noqa: S104


# run the application if this file is executed directly
if __name__ == "__main__":
    bluebook()
