"""Prompts blueprint for custom prompt management routes.

This blueprint handles:
- Custom prompts page
- Adding/deleting custom prompts
"""

from flask import Blueprint, render_template, request

from bluebook import database_manager, generator
from bluebook.services.exam_service import ExamService
from bluebook.state_manager import StateManager

prompts_bp = Blueprint("prompts", __name__)


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


@prompts_bp.route("/custom_prompts", methods=["GET"])
def custom_prompts() -> str:
    """Render the custom prompts page."""
    service = get_exam_service()
    db_manager = get_db_manager()
    
    service.ensure_session()
    
    available_prompts = db_manager.select_all_prompts()
    
    return render_template(
        "prompt_builder.html.j2",
        prompts={"prompt_list": available_prompts},
        default_prompt_text=generator.PromptBuilder.build_template_query(),
        custom={"header": "Custom Prompts Builder"},
        exams=service.obtain_exam_data(),
    )


@prompts_bp.route("/custom_prompts/add", methods=["POST"])
def add_custom_prompt() -> str:
    """Add a new custom prompt."""
    service = get_exam_service()
    db_manager = get_db_manager()
    
    service.ensure_session()
    
    name = request.form.get("name")
    prompt = request.form.get("prompt")
    
    if generator.PromptBuilder.PromptTemplate.verify_template_prompt(prompt):
        db_manager.add_custom_prompt(name=name, prompt=prompt)
    
    return custom_prompts()


@prompts_bp.route("/custom_prompts/delete", methods=["POST"])
def delete_custom_prompt() -> str:
    """Delete a custom prompt."""
    service = get_exam_service()
    db_manager = get_db_manager()
    
    service.ensure_session()
    
    prompt_id = request.form.get("id")
    db_manager.remove_prompt(prompt_id=prompt_id)
    
    return custom_prompts()
