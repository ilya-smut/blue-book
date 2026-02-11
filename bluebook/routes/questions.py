"""Questions blueprint for question-related routes.

This blueprint handles:
- Question generation
- Answer checking
- Question saving/removal
- Topic saving/removal
- Saved questions page
"""

from flask import Blueprint, jsonify, redirect, render_template, request
from flask.wrappers import Response as FlaskResponse
from werkzeug.wrappers.response import Response

import google.genai.errors  # type: ignore

from bluebook import data_models, database_manager, generator, token_manager
from bluebook.file_manager import FileManager
from bluebook.services.exam_service import ExamService
from bluebook.services.question_service import QuestionService
from bluebook.state_manager import StateManager

questions_bp = Blueprint("questions", __name__)

# Shared file manager instance
_file_manager = FileManager()


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


def get_question_service() -> QuestionService:
    """Get a QuestionService instance for the current request."""
    state = get_state()
    db = get_db_manager()
    return QuestionService(state, db, _file_manager)


@questions_bp.route("/generate", methods=["POST"])
def generate() -> str:
    """Generate new questions based on user input."""
    from bluebook.routes.main import root
    
    config = token_manager.load_config()
    exam_service = get_exam_service()
    question_service = get_question_service()
    state = get_state()
    
    exam_service.ensure_session()
    
    if token_page := token_manager.ensure_token(config):
        return token_page
    
    state.submitted = True
    num_of_questions = int(request.form["num_of_questions"])
    use_attached_files = bool(request.form.get("use_attached_files"))
    prompt_id = int(request.form["prompt"])
    
    state.latest_num = str(num_of_questions)
    
    additional_request = generator.sanitize_input(str(request.form["additional_request"]))
    if request.form.get("additional_request_preset"):
        additional_request = generator.sanitize_input(
            str(request.form["additional_request_preset"]),
        )
    
    if not additional_request:
        exam_service.set_additional_request(False)
    else:
        exam_service.set_additional_request(additional_request)
    
    try:
        exam_data = exam_service.obtain_exam_data()
        questions = question_service.generate_questions(
            num_of_questions=num_of_questions,
            additional_request=additional_request,
            exam_name=exam_data["current_exam"]["name"],
            token=config["API_TOKEN"],
            use_attached_files=use_attached_files,
            prompt_id=prompt_id,
        )
        state.question_list = questions
    except google.genai.errors.ClientError:
        return render_template("token_prompt.html.j2")
    
    return root()


@questions_bp.route("/check", methods=["POST"])
def check() -> str:
    """Check user answers against the correct answers."""
    exam_service = get_exam_service()
    question_service = get_question_service()
    
    exam_service.ensure_session()
    
    user_answers = {key: request.form[key] for key in request.form}
    data_out = question_service.check_answers(user_answers)
    
    return render_template(
        "check.html.j2",
        data=data_out,
        saved_topics=exam_service.obtain_saved_topics(),
        exams=exam_service.obtain_exam_data(),
    )


@questions_bp.route("/save-question", methods=["POST"])
def save_question() -> Response | tuple[FlaskResponse, int]:
    """Save a question to the database."""
    exam_service = get_exam_service()
    question_service = get_question_service()
    
    exam_service.ensure_session()
    
    if "q_index" not in request.form:
        return jsonify({"message": "Question index not found in received form."}), 400
    
    question_index = int(request.form["q_index"])
    success, message = question_service.save_question(question_index)
    
    return jsonify({"message": message})


@questions_bp.route("/remove-saved-question/endpoint", methods=["POST"])
def remove_saved_question() -> Response:
    """Remove a saved question from the database."""
    exam_service = get_exam_service()
    question_service = get_question_service()
    
    exam_service.ensure_session()
    
    if "persistent_id" in request.form:
        question_id = int(request.form["persistent_id"])
        question_service.remove_saved_question(question_id)
    
    return redirect("/saved-questions")


@questions_bp.route("/saved-questions", methods=["GET"])
def saved_questions() -> str:
    """Render the saved questions page."""
    exam_service = get_exam_service()
    question_service = get_question_service()
    
    exam_service.ensure_session()
    
    serialized_questions = question_service.get_saved_questions()
    
    return render_template(
        "saved_questions.html.j2",
        serialised_questions=serialized_questions,
        saved_topics=exam_service.obtain_saved_topics(),
        exams=exam_service.obtain_exam_data(),
    )


@questions_bp.route("/save-the-topic", methods=["POST"])
def save_the_topic() -> Response:
    """Save the additional request topic."""
    exam_service = get_exam_service()
    question_service = get_question_service()
    state = get_state()
    
    exam_service.ensure_session()
    
    if "topic" in request.form:
        topic_to_save = state.additional_request["value"]
        question_service.save_topic(topic_to_save)
        exam_service.set_additional_request(topic_to_save)
    
    return redirect("/")


@questions_bp.route("/remove-saved-topic", methods=["POST"])
def remove_saved_topic() -> Response:
    """Remove a saved topic from the database."""
    exam_service = get_exam_service()
    question_service = get_question_service()
    
    exam_service.ensure_session()
    
    if "additional_request_preset" in request.form:
        topic_to_delete = request.form["additional_request_preset"]
        if question_service.remove_topic(topic_to_delete):
            exam_service.set_additional_request(topic_to_delete)
    
    return redirect("/")
