"""Exams blueprint for exam management routes.

This blueprint handles:
- Exam switching
- Exam constructor page
- Adding/deleting custom exams
"""

from flask import Blueprint, redirect, render_template, request
from werkzeug.wrappers.response import Response

from bluebook import database_manager
from bluebook.services.exam_service import ExamService
from bluebook.state_manager import StateManager

exams_bp = Blueprint("exams", __name__)


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


@exams_bp.route("/set-exam", methods=["POST"])
def set_exam() -> Response:
    """Switch to another exam based on the exam ID provided."""
    service = get_exam_service()
    state = get_state()
    
    service.ensure_session()
    
    if "exam-id" in request.form:
        new_exam_id = int(request.form["exam-id"])
        
        # Save existing state
        service.save_state()
        
        # Switch to new state if different from current
        if new_exam_id != state.exam_id:
            service.switch_state(new_exam_id)
    
    return redirect("/")


@exams_bp.route("/exam-constructor", methods=["GET"])
def exam_constructor() -> str:
    """Render the exam constructor page."""
    service = get_exam_service()
    
    service.ensure_session()
    
    custom = {"header": "Exam Constructor"}
    return render_template(
        "exam_constructor.html.j2",
        custom=custom,
        exams=service.obtain_exam_data(),
    )


@exams_bp.route("/exam-constructor/add-custom-exam", methods=["POST"])
def add_custom_exam() -> Response:
    """Add a new custom exam."""
    service = get_exam_service()
    
    service.ensure_session()
    
    if "new-exam-name" in request.form:
        exam_name = request.form["new-exam-name"]
        service.add_custom_exam(exam_name)
    
    return redirect("/exam-constructor")


@exams_bp.route("/exam-constructor/delete-custom-exam", methods=["POST"])
def delete_custom_exam() -> Response:
    """Delete a custom exam."""
    service = get_exam_service()
    
    service.ensure_session()
    
    if "exam-id" in request.form:
        exam_id = int(request.form["exam-id"])
        service.delete_custom_exam(exam_id)
    
    return redirect("/exam-constructor")
