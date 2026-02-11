"""State management for Blue Book application.

This module provides thread-safe state management using Flask sessions,
replacing the previous global state approach.
"""
import json
import logging
from typing import Any, Optional

from flask import session

from bluebook import data_models
from bluebook.configuration import Configuration

logger = logging.getLogger("bluebook.state_manager")


class StateManager:
    """Manages application state using Flask session for thread safety.
    
    This class encapsulates all state-related operations and stores state
    in Flask's session, making the application thread-safe for concurrent requests.
    """

    # Session keys
    _QUESTION_LIST_KEY = "question_list_serialized"
    _EXAM_ID_KEY = "exam_id"
    _INIT_KEY = "state_init"
    _SUBMITTED_KEY = "submitted"
    _ADDITIONAL_REQUEST_KEY = "additional_request"
    _LATEST_NUM_KEY = "latest_num"
    _TOKEN_PRESENT_KEY = "TOKEN_PRESENT"
    _PROMPTS_KEY = "prompts"

    def __init__(self) -> None:
        """Initialize the state manager."""

    def ensure_initialized(self) -> bool:
        """Ensure session state is initialized with default values.
        
        Returns:
            bool: True if this was the first initialization, False if already initialized.
        """
        first_init = False
        
        if self._INIT_KEY not in session:
            session[self._INIT_KEY] = True
            first_init = True
            
        if self._EXAM_ID_KEY not in session:
            session[self._EXAM_ID_KEY] = Configuration.DefaultValues.DEFAULT_EXAM_ID
            
        if self._QUESTION_LIST_KEY not in session:
            session[self._QUESTION_LIST_KEY] = json.dumps({"questions": [], "size": 0})
            
        if self._SUBMITTED_KEY not in session:
            session[self._SUBMITTED_KEY] = False
            logger.debug("session['submitted'] initialised to False.")
            
        if self._ADDITIONAL_REQUEST_KEY not in session:
            session[self._ADDITIONAL_REQUEST_KEY] = {"set": False, "value": "", "saved": False}
            
        if self._LATEST_NUM_KEY not in session:
            session[self._LATEST_NUM_KEY] = "2"
            logger.debug("session['latest_num'] initialised to 2.")
            
        if self._TOKEN_PRESENT_KEY not in session:
            session[self._TOKEN_PRESENT_KEY] = False
            logger.debug("session['TOKEN_PRESENT'] initialised to False.")
            
        return first_init

    @property
    def is_first_init(self) -> bool:
        """Check if this is the first initialization for this session."""
        return session.get(self._INIT_KEY, True)

    @is_first_init.setter
    def is_first_init(self, value: bool) -> None:
        """Set the initialization flag."""
        session[self._INIT_KEY] = value

    @property
    def exam_id(self) -> int:
        """Get the current exam ID."""
        return session.get(self._EXAM_ID_KEY, Configuration.DefaultValues.DEFAULT_EXAM_ID)

    @exam_id.setter
    def exam_id(self, value: int) -> None:
        """Set the current exam ID."""
        session[self._EXAM_ID_KEY] = value

    @property
    def question_list(self) -> list[data_models.Question]:
        """Get the current list of questions (deserialized)."""
        serialized = session.get(self._QUESTION_LIST_KEY, '{"questions": [], "size": 0}')
        try:
            data = json.loads(serialized)
            return data_models.load_questions(data)
        except (json.JSONDecodeError, KeyError):
            return []

    @question_list.setter
    def question_list(self, questions: list[data_models.Question]) -> None:
        """Set the current list of questions (serialized for session storage)."""
        serialized = data_models.serialize_questions(questions)
        session[self._QUESTION_LIST_KEY] = json.dumps(serialized)

    @property
    def submitted(self) -> bool:
        """Check if questions have been submitted/generated."""
        return session.get(self._SUBMITTED_KEY, False)

    @submitted.setter
    def submitted(self, value: bool) -> None:
        """Set the submitted state."""
        session[self._SUBMITTED_KEY] = value
        logger.debug(f"session['submitted'] set to {value}")

    @property
    def additional_request(self) -> dict[str, Any]:
        """Get the additional request data."""
        return session.get(self._ADDITIONAL_REQUEST_KEY, {"set": False, "value": "", "saved": False})

    @additional_request.setter
    def additional_request(self, value: dict[str, Any]) -> None:
        """Set the additional request data."""
        session[self._ADDITIONAL_REQUEST_KEY] = value

    @property
    def latest_num(self) -> str:
        """Get the latest number of questions requested."""
        return session.get(self._LATEST_NUM_KEY, "2")

    @latest_num.setter
    def latest_num(self, value: str) -> None:
        """Set the latest number of questions requested."""
        session[self._LATEST_NUM_KEY] = value

    @property
    def token_present(self) -> bool:
        """Check if API token is present."""
        return session.get(self._TOKEN_PRESENT_KEY, False)

    @token_present.setter
    def token_present(self, value: bool) -> None:
        """Set the token present flag."""
        session[self._TOKEN_PRESENT_KEY] = value

    @property
    def prompts(self) -> list[dict[str, Any]]:
        """Get the available prompts."""
        return session.get(self._PROMPTS_KEY, [])

    @prompts.setter
    def prompts(self, value: list[dict[str, Any]]) -> None:
        """Set the available prompts."""
        session[self._PROMPTS_KEY] = value

    def set_additional_request_value(
        self,
        value: Optional[str],
        is_saved: bool = False
    ) -> None:
        """Set the additional request with proper structure.
        
        Args:
            value: The additional request value, or None to clear.
            is_saved: Whether this request is saved in the database.
        """
        if not value:
            self.additional_request = {"set": False, "value": "", "saved": False}
            logger.debug("Additional request cleared.")
        else:
            self.additional_request = {"set": True, "value": value, "saved": is_saved}
            logger.debug("Additional request set", extra={"value": value})

    def get_serialized_questions(self) -> dict[str, Any]:
        """Get questions in serialized format for template rendering."""
        return data_models.serialize_questions(self.question_list)

    def to_json_string(self) -> str:
        """Serialize the question list to a JSON string for database storage."""
        questions = data_models.serialize_questions(self.question_list)
        return json.dumps(questions)

    def load_from_json_string(self, json_str: str) -> None:
        """Load question list from a JSON string (from database)."""
        logger.debug("Loading string into state", extra={"length": len(json_str) if json_str else 0})
        try:
            serialized_questions = json.loads(json_str) if json_str else {"questions": [], "size": 0}
            logger.debug("State string deserialised to python object successfully.")
        except json.JSONDecodeError:
            logger.debug("Invalid string. Reverting to {'questions': [], 'size': 0}.")
            serialized_questions = {"questions": [], "size": 0}
        self.question_list = data_models.load_questions(serialized_questions)

    def get_state_log(self) -> str:
        """Get a readable string representation of the current state for logging."""
        num_of_questions = len(self.question_list)
        return (f"State[ {num_of_questions} questions, "
                f"exam_id={self.exam_id}, is_init={self.is_first_init}]")
