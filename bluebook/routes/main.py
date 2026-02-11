"""Main blueprint for core application routes.

This blueprint handles:
- Home page rendering
- Token management (save/clear)
- Question wiping
- Database clearing
"""

from flask import Blueprint, redirect, render_template, request
from werkzeug.wrappers.response import Response

from bluebook import configuration, database_manager, token_manager
from bluebook.services.exam_service import ExamService
from bluebook.state_manager import StateManager

main_bp = Blueprint("main", __name__)


def get_state() -> StateManager:
    """Get the state manager instance for the current request."""
    return StateManager()


def get_db_manager(exam_id: int | None = None) -> database_manager.Database:
    """Get a database manager for the given exam ID."""
    if exam_id is None:
        exam_id = get_state().exam_id
    return database_manager.Database(exam_id=exam_id)


def get_exam_service() -> ExamService:
    """Get an ExamService instance for the current request."""
    state = get_state()
    db = get_db_manager()
    return ExamService(state, db)


@main_bp.route("/")
def root() -> str:
    """Render the home page of the application."""
    config = token_manager.load_config()
    service = get_exam_service()
    state = get_state()
    
    service.ensure_session()
    
    serialized_state = state.get_serialized_questions()
    if not serialized_state:
        serialized_state["size"] = 0
    
    state.token_present = token_manager.is_token_present(config)
    
    return render_template(
        "root.html.j2",
        data=serialized_state,
        saved_topics=service.obtain_saved_topics(),
        exams=service.obtain_exam_data(),
    )


@main_bp.route("/save_token", methods=["POST"])
def save_token() -> str:
    """Save the API token provided by the user."""
    api_token = request.form.get("API_TOKEN")
    config = token_manager.load_config()
    config["API_TOKEN"] = api_token
    token_manager.save_config(config)
    return root()


@main_bp.route("/clear_token", methods=["POST"])
def clear_token() -> str:
    """Clear the API token from the session and configuration."""
    token_manager.clear_token()
    return root()


@main_bp.route("/wipe_questions", methods=["POST"])
def wipe_questions() -> str:
    """Wipe the current questions from the session."""
    service = get_exam_service()
    service.ensure_session()
    service.wipe_questions()
    return root()


@main_bp.route("/clear-persistent-storage", methods=["POST"])
def clear_persistent_storage() -> Response:
    """Clear the persistent storage and reinitialize the database."""
    service = get_exam_service()
    state = get_state()
    
    service.ensure_session()
    service.clear_persistent_storage()
    
    exam_data = service.obtain_exam_data()
    if state.exam_id not in exam_data["built-in-indices"]:
        service.switch_state(configuration.Configuration.DefaultValues.DEFAULT_EXAM_ID)
    
    return redirect("/")
