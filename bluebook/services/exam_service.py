"""Service layer for exam-related business logic.

This module contains the ExamService class that handles all exam-related
operations including state switching, saving, and exam CRUD operations.
"""

import logging
from typing import Any

from bluebook import configuration, data_models, database_manager, generator
from bluebook.state_manager import StateManager

logger = logging.getLogger("bluebook.services.exam_service")


class ExamService:
    """Service class for exam-related operations."""

    def __init__(self, state: StateManager, db_manager: database_manager.Database) -> None:
        """Initialize the exam service.
        
        Args:
            state: The state manager for the current session.
            db_manager: The database manager instance.
        """
        self.state = state
        self.db_manager = db_manager

    def get_serialized_state(self) -> str:
        """Serialize the current state to a JSON string.
        
        Returns:
            str: JSON representation of the current state.
        """
        return self.state.to_json_string()

    def load_state_from_string(self, state_str: str | None) -> None:
        """Load state from a JSON string.
        
        Args:
            state_str: JSON string representation of state, or None.
        """
        self.state.load_from_json_string(state_str if state_str else "")

    def set_additional_request(self, value: Any) -> None:
        """Set the additional request in the session.
        
        Args:
            value: The additional request value. If falsy, clears the request.
        """
        if not value:
            self.state.set_additional_request_value(None)
        else:
            saved_request = self.db_manager.select_extra_req_by_value(value)
            self.state.set_additional_request_value(value, is_saved=bool(saved_request))

    def switch_state(self, exam_id: int) -> None:
        """Switch the current state to a new exam.
        
        Args:
            exam_id: The ID of the exam to switch to.
        """
        logger.debug("Switching state", extra={"exam_id": exam_id})
        
        # Setting new state
        self.state.exam_id = exam_id
        # Get fresh db_manager for the new exam
        new_db_manager = database_manager.Database(exam_id=exam_id)
        loaded_state = new_db_manager.load_state(exam_id)
        self.load_state_from_string(loaded_state["state_str"])
        self.set_additional_request(loaded_state["additional_request"])
        
        if self.state.question_list:
            self.state.submitted = True
        else:
            self.state.submitted = False
        
        logger.debug("State switched", extra={
            "exam_id": self.state.exam_id,
            "question_list_size": len(self.state.question_list),
            "additional_request": self.state.additional_request["value"],
        })

    def save_state(self) -> None:
        """Serialize and save the current state to the database."""
        current_exam_id = self.state.exam_id
        current_state_str = self.get_serialized_state()
        logger.debug("Saving state to database", extra={
            "exam_id": current_exam_id,
            "state_str_length": len(current_state_str),
            "additional_request": self.state.additional_request["value"],
        })
        self.db_manager.save_state(
            state_str=current_state_str,
            exam_id=current_exam_id,
            additional_request=self.state.additional_request["value"],
        )

    def obtain_saved_topics(self) -> dict[str, Any]:
        """Retrieve all saved topics from the database.
        
        Returns:
            dict with 'size' and 'requests' list.
        """
        data: dict[str, Any] = {}
        all_saved_topics = self.db_manager.select_all_extra_requests()
        size = len(all_saved_topics)
        data["size"] = size
        data["requests"] = [topic.to_dict() for topic in all_saved_topics]
        logger.debug("Saved topics retrieved", extra={"size": size, "exam_id": self.state.exam_id})
        return data

    def obtain_exam_data(self) -> dict[str, Any]:
        """Retrieve current exam data and all exams from the database.
        
        Returns:
            dict with 'exam_list', 'current_exam', and 'built-in-indices'.
        """
        current_exam = self.db_manager.select_exam_by_id(self.state.exam_id)
        exam_data = {
            "exam_list": self.db_manager.select_all_exams(),
            "current_exam": current_exam,
            "built-in-indices": self.db_manager.get_built_in_indices(),
        }
        logger.debug("Exam data retrieved", extra={
            "current_exam": exam_data["current_exam"],
            "size": len(exam_data["exam_list"]),
        })
        return exam_data

    def add_custom_exam(self, exam_name: str) -> bool:
        """Add a new custom exam.
        
        Args:
            exam_name: The name of the new exam.
            
        Returns:
            bool: True if exam was added, False otherwise.
        """
        sanitized_name = generator.sanitize_input(exam_name)
        if sanitized_name:
            self.db_manager.add_new_exam(exam_name=sanitized_name)
            logger.debug("Custom exam added", extra={"exam_name": sanitized_name})
            return True
        logger.debug("Exam name was not provided. Abort adding new exam.")
        return False

    def delete_custom_exam(self, exam_id: int) -> bool:
        """Delete a custom exam.
        
        Args:
            exam_id: The ID of the exam to delete.
            
        Returns:
            bool: True if current exam needs to be switched.
        """
        if exam_id:
            self.db_manager.delete_exam(exam_id=exam_id)
            logger.debug("Custom exam deleted", extra={"exam_id": exam_id})
            if self.state.exam_id == exam_id:
                self.switch_state(configuration.Configuration.DefaultValues.DEFAULT_EXAM_ID)
                return True
        return False

    def wipe_questions(self) -> None:
        """Wipe all questions from the current session."""
        self.state.submitted = False
        self.set_additional_request(False)
        self.state.latest_num = "2"
        self.state.question_list = []
        logger.debug("Questions wiped", extra={
            "exam_id": self.state.exam_id,
        })

    def clear_persistent_storage(self) -> None:
        """Clear the persistent storage and reinitialize."""
        configuration.Configuration.SystemPath.clear_persistent()
        questions = self.state.question_list
        for question in questions:
            question.saved = False
        self.state.question_list = questions
        logger.debug("Database has been cleared and reinitialised.")

    def ensure_session(self) -> None:
        """Ensure the session is initialized with required keys."""
        first_init = self.state.ensure_initialized()
        
        if first_init or self.state.is_first_init:
            self.state.is_first_init = False
            self.switch_state(self.state.exam_id)
        
        # Update prompts list
        self.state.prompts = [
            {"id": prompt["id"], "name": prompt["name"]} 
            for prompt in self.db_manager.select_all_prompts()
        ]
