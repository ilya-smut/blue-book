"""Service layer for question-related business logic.

This module contains the QuestionService class that handles all question-related
operations including generation, checking answers, and persistence.
"""

import logging
from typing import Any

import google.genai.errors  # type: ignore
import sqlalchemy.exc

from bluebook import data_models, database_manager, generator, token_manager
from bluebook.file_manager import FileManager
from bluebook.helpers.file_attachment import get_remote_attached_files
from bluebook.state_manager import StateManager

logger = logging.getLogger("bluebook.services.question_service")


class QuestionService:
    """Service class for question-related operations."""

    def __init__(
        self, 
        state: StateManager, 
        db_manager: database_manager.Database,
        file_manager: FileManager | None = None
    ) -> None:
        """Initialize the question service.
        
        Args:
            state: The state manager for the current session.
            db_manager: The database manager instance.
            file_manager: Optional file manager instance.
        """
        self.state = state
        self.db_manager = db_manager
        self.file_manager = file_manager or FileManager()

    def generate_questions(
        self,
        num_of_questions: int,
        additional_request: str,
        exam_name: str,
        token: str,
        use_attached_files: bool = False,
        prompt_id: int = 0,
    ) -> list[data_models.Question]:
        """Generate questions using the Gemini API.
        
        Args:
            num_of_questions: Number of questions to generate.
            additional_request: Topic focus or additional instructions.
            exam_name: Name of the current exam.
            token: API token for Gemini.
            use_attached_files: Whether to include attached files.
            prompt_id: ID of custom prompt to use (0 for built-in).
            
        Returns:
            list of Question objects.
            
        Raises:
            google.genai.errors.ClientError: If API call fails.
        """
        custom_prompt = None
        if prompt_id != 0:
            logger.debug(f"Custom prompt selected id: {prompt_id}")
            prompt_data = self.db_manager.select_prompt_by_id(prompt_id=prompt_id)
            if prompt_data:
                custom_prompt = prompt_data['prompt']

        attached_files = []
        if use_attached_files:
            logger.debug("Using attached files for generation")
            attached_files = get_remote_attached_files(db=self.db_manager, fl=self.file_manager)

        logger.debug("Generating questions", extra={
            "num_of_questions": num_of_questions,
            "additional_request": additional_request,
            "use_attached_files": use_attached_files,
        })

        questions = generator.ask_gemini(
            exam_name=exam_name,
            question_num=num_of_questions,
            token=token,
            additional_request=additional_request,
            attached_files=attached_files,
            custom_prompt=custom_prompt,
        )

        logger.debug("Questions generated", extra={"count": len(questions)})
        return questions

    def check_answers(
        self, 
        user_answers: dict[str, str]
    ) -> dict[str, Any]:
        """Check user answers against the correct answers.
        
        Args:
            user_answers: Dictionary mapping question index to selected answer index.
            
        Returns:
            dict containing original_data, user_answers, is_answer_correct, and statistics.
        """
        original_data = self.state.question_list
        statistics = data_models.Statistics()
        
        data_out: dict[str, Any] = {
            "original_data": data_models.serialize_questions(original_data),
            "user_answers": {},
            "is_answer_correct": {},
            "statistics": {},
        }

        for i in range(len(original_data)):
            answer_idx = int(user_answers.get(str(i), "0"))
            is_correct = original_data[i].choices[answer_idx].is_correct
            
            data_out["user_answers"][i] = answer_idx
            data_out["is_answer_correct"][i] = is_correct
            
            if is_correct:
                statistics.increment_both()
            else:
                statistics.increment_all_num()

        data_out["statistics"] = statistics.serialize()
        logger.debug("User answers checked", extra={"statistics": data_out["statistics"]})
        return data_out

    def save_question(self, question_index: int) -> tuple[bool, str]:
        """Save a question to the database.
        
        Args:
            question_index: Index of the question in the current list.
            
        Returns:
            tuple of (success: bool, message: str).
        """
        questions = self.state.question_list
        
        if question_index < 0 or question_index >= len(questions):
            return False, "Question index out of range."
        
        question = questions[question_index]
        
        try:
            question.saved = True
            self.db_manager.add_question(question)
            # Update the state with modified question
            self.state.question_list = questions
            logger.debug("Question saved successfully", extra={
                "question_index": question_index,
                "exam_id": self.state.exam_id,
            })
            return True, f"Question {question_index} saved successfully."
        except sqlalchemy.exc.IntegrityError:
            logger.debug("Question was already saved", extra={
                "question_index": question_index,
                "exam_id": self.state.exam_id,
            })
            return False, f"Question {question_index} was already saved."

    def remove_saved_question(self, persistent_id: int) -> bool:
        """Remove a saved question from the database.
        
        Args:
            persistent_id: The database ID of the question.
            
        Returns:
            bool: True if removed successfully, False otherwise.
        """
        try:
            self.db_manager.remove_question_by_id(persistent_id)
            logger.debug("Question removed", extra={
                "persistent_id": persistent_id,
                "exam_id": self.state.exam_id,
            })
            return True
        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.error("Database operation failed", exc_info=e)
            return False
        except Exception as e:
            logger.error("Unexpected error in remove_question_by_id", exc_info=e)
            return False

    def get_saved_questions(self) -> dict[str, Any]:
        """Get all saved questions for the current exam.
        
        Returns:
            dict with serialized questions.
        """
        questions = self.db_manager.select_all_questions_pydantic()
        return data_models.serialize_questions(questions)

    def save_topic(self, topic: str) -> bool:
        """Save an additional request topic to the database.
        
        Args:
            topic: The topic to save.
            
        Returns:
            bool: True if saved successfully, False if already exists.
        """
        try:
            self.db_manager.add_extra_request(topic)
            logger.debug("Topic saved", extra={"topic": topic})
            return True
        except sqlalchemy.exc.IntegrityError:
            logger.debug("Topic was NOT saved: Already present", extra={"topic": topic})
            return False

    def remove_topic(self, topic: str) -> bool:
        """Remove a saved topic from the database.
        
        Args:
            topic: The topic to remove.
            
        Returns:
            bool: True if removed successfully, False otherwise.
        """
        if self.db_manager.select_extra_req_by_value(topic):
            self.db_manager.remove_extra_request_by_value(topic)
            logger.debug("Topic removed", extra={"topic": topic})
            return True
        return False
