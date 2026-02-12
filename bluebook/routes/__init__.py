"""Flask Blueprints for the Bluebook application.

This package contains route handlers organized by functionality:
- main: Home page, token management, core utilities
- questions: Question generation, checking, and saving
- exams: Exam switching and constructor
- files: File upload and attachment management
- prompts: Custom prompt management
"""

from bluebook.routes.main import main_bp
from bluebook.routes.questions import questions_bp
from bluebook.routes.exams import exams_bp
from bluebook.routes.files import files_bp
from bluebook.routes.prompts import prompts_bp

__all__ = [
    "main_bp",
    "questions_bp",
    "exams_bp",
    "files_bp",
    "prompts_bp",
]
