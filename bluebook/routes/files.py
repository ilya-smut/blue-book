"""Files blueprint for file management routes.

This blueprint handles:
- File upload page
- Local cache file operations
- Remote (Gemini) file operations
- File attachment to exams
"""

from flask import Blueprint, render_template, request
from werkzeug.utils import secure_filename

from bluebook import database_manager
from bluebook.file_manager import FileManager
from bluebook.services.exam_service import ExamService
from bluebook.state_manager import StateManager

files_bp = Blueprint("files", __name__)

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


@files_bp.route("/files", methods=["GET"])
def files_page() -> str:
    """Render the file management page."""
    service = get_exam_service()
    
    service.ensure_session()
    
    custom = {"header": "Files"}
    local_files = _file_manager.ls_cache_dir(str_names=True)
    
    try:
        gemini_files = list(_file_manager.ls_remote().keys())
    except Exception:
        gemini_files = []
    
    return render_template(
        "uploaded_files.html.j2",
        custom=custom,
        local_files=local_files,
        gemini_files=gemini_files,
        exams=service.obtain_exam_data(),
    )


@files_bp.route("/files/upload/local", methods=["POST"])
def upload_to_cache() -> str | tuple[str, int]:
    """Upload a file to the local cache."""
    service = get_exam_service()
    
    service.ensure_session()
    
    file = request.files.get("file")
    if not file or file.filename == "":
        return "No file uploaded", 400
    
    custom_name = request.form.get("custom_filename")
    if custom_name:
        file.filename = secure_filename(custom_name)
    
    _file_manager.form_file2cache(file=file)
    return files_page()


@files_bp.route("/files/upload/remote", methods=["POST"])
def upload_to_remote() -> str:
    """Sync a local file to Gemini remote storage."""
    service = get_exam_service()
    
    service.ensure_session()
    
    filename = request.form.get("filename")
    if filename:
        filename = secure_filename(filename)
    
    _file_manager.upload_from_cache(name=filename, force_unique=True)
    return files_page()


@files_bp.route("/files/delete/local", methods=["POST"])
def delete_from_cache() -> str | tuple[str, int]:
    """Delete a file from the local cache."""
    service = get_exam_service()
    
    service.ensure_session()
    
    filename = request.form.get("filename")
    if not filename:
        return "Empty Filename", 400
    
    filename = secure_filename(filename)
    _file_manager.remove_from_cache(filename)
    return files_page()


@files_bp.route("/files/delete/remote", methods=["POST"])
def delete_from_remote() -> str | tuple[str, int]:
    """Delete a file from Gemini remote storage."""
    service = get_exam_service()
    
    service.ensure_session()
    
    filename = request.form.get("filename")
    if not filename:
        return "Empty Filename", 400
    
    filename = secure_filename(filename)
    _file_manager.remove_from_remote(filename)
    return files_page()


@files_bp.route("/attached_to_exam", methods=["GET"])
def attached_files(exam_id: int | None = None, exam_name: str | None = None) -> str:
    """Render the files attached to an exam."""
    service = get_exam_service()
    db_manager = get_db_manager()
    
    service.ensure_session()
    
    if not exam_id:
        exam_id = request.args.get("exam-id")
    if not exam_name:
        exam_name = request.args.get("exam-name")
    
    custom = {
        "header": f"Files attached to {exam_name}",
        "exam_name": exam_name,
        "exam_id": exam_id,
    }
    
    local_files = _file_manager.ls_cache_dir(str_names=True)
    attached_files_list: list[str] = []
    
    afs = db_manager.select_attached_files(exam_id=exam_id)
    for row in afs:
        attached_files_list.append(row["name"])
    
    return render_template(
        "attached_files.html.j2",
        custom=custom,
        local_files=local_files,
        attached_files=attached_files_list,
        exams=service.obtain_exam_data(),
    )


@files_bp.route("/attached_to_exam/attach", methods=["POST"])
def attach_to_exam() -> str:
    """Attach a file to an exam."""
    service = get_exam_service()
    db_manager = get_db_manager()
    
    service.ensure_session()
    
    exam_name = request.form.get("exam-name")
    exam_id = request.form.get("exam-id")
    filename = request.form.get("filename")
    
    local_files = set(_file_manager.ls_cache_dir(str_names=True))
    
    if filename in local_files and exam_id:
        db_manager.add_attached_file(filename=filename, exam_id=int(exam_id))
    
    return attached_files(exam_id=exam_id, exam_name=exam_name)


@files_bp.route("/attached_to_exam/remove", methods=["POST"])
def remove_attached() -> str:
    """Remove a file attachment from an exam."""
    service = get_exam_service()
    db_manager = get_db_manager()
    
    service.ensure_session()
    
    exam_name = request.form.get("exam-name")
    exam_id = request.form.get("exam-id")
    filename = request.form.get("filename")
    
    if filename and exam_id:
        record = db_manager.select_attached_file_by_name(filename=filename, exam_id=exam_id)
        if record:
            db_manager.remove_attached_file(id=record["id"])
    
    return attached_files(exam_id=exam_id, exam_name=exam_name)
