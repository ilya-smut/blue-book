"""Data models for the Blue Book application.

This module contains Pydantic models for questions, choices, and statistics,
along with serialization/deserialization functions.
"""
import logging
from typing import Any

import bleach
from pydantic import BaseModel, field_validator, model_validator

logger = logging.getLogger("bluebook.data_models")


class Statistics:
    """Statistics for tracking answer correctness."""
    
    all_num: int
    correct: int
    
    def __init__(self) -> None:
        self.all_num = 0
        self.correct = 0

    def get_correct_num(self) -> int:
        """Returns the number of correct answers."""
        return self.correct

    def get_incorrect_num(self) -> int:
        """Returns the number of incorrect answers."""
        return self.all_num - self.correct

    def increment_correct(self) -> None:
        """Increments the count of correct answers."""
        self.correct += 1

    def increment_all_num(self) -> None:
        """Increments the total number of answers."""
        self.all_num += 1

    def increment_both(self) -> None:
        """Increments both the total number of answers and the count of correct answers."""
        self.increment_all_num()
        self.increment_correct()

    def serialize(self) -> dict[str, int]:
        """Serializes the statistics into a dictionary."""
        return {"all": self.all_num, "correct": self.correct, "incorrect": self.get_incorrect_num()}


class Choice(BaseModel):
    """Model representing a single answer choice."""
    
    option: str
    is_correct: bool
    explanation: str

    @field_validator("option", "explanation", mode="before")
    @classmethod
    def sanitize_strings(cls, v: str) -> str:
        """Sanitize string fields to prevent XSS attacks."""
        if isinstance(v, str):
            return bleach.clean(v)
        return v

    @field_validator("option")
    @classmethod
    def option_not_empty(cls, v: str) -> str:
        """Ensure option is not empty."""
        if not v.strip():
            raise ValueError("Option cannot be empty")
        return v


class _RawQuestion(BaseModel):
    """Raw question model used for parsing the response from the AI."""
    question: str
    choices: list[Choice]
    study_recommendation: str


class Question(BaseModel):
    """Model representing a question with its choices and metadata."""
    
    question: str
    choices: list[Choice]
    study_recommendation: str
    saved: bool | None = None  # Optional field to identify if question is saved or not
    persistent_id: int | None = None  # Database ID when saved

    @field_validator("question", "study_recommendation", mode="before")
    @classmethod
    def sanitize_strings(cls, v: str) -> str:
        """Sanitize string fields to prevent XSS attacks."""
        if isinstance(v, str):
            return bleach.clean(v)
        return v

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        """Ensure question is not empty."""
        if not v.strip():
            raise ValueError("Question cannot be empty")
        return v

    @field_validator("choices")
    @classmethod
    def validate_choices(cls, v: list[Choice]) -> list[Choice]:
        """Validate that there is at least one choice."""
        if not v:
            raise ValueError("Question must have at least one choice")
        return v

    @model_validator(mode="after")
    def validate_has_correct_answer(self) -> "Question":
        """Ensure there is exactly one correct answer."""
        correct_count = sum(1 for c in self.choices if c.is_correct)
        if correct_count == 0:
            logger.warning("Question has no correct answer marked")
        elif correct_count > 1:
            logger.warning(f"Question has {correct_count} correct answers, expected 1")
        return self

    @classmethod
    def from_raw_question(cls, raw_question: _RawQuestion) -> "Question":
        """Creates a Question object from a raw question model.
        Args:
            raw_question (_RawQuestion): The raw question model containing the question data.
        Returns:
            Question: A new Question object created from the raw question data.
        """
        return cls(
            question=raw_question.question,
            choices=raw_question.choices,
            study_recommendation=raw_question.study_recommendation,
            saved=None,
            persistent_id=None,
        )


def serialize_questions(question_list: list[Question]) -> dict[str, Any]:
    """Serializes a list of Question objects into a dictionary format.
    
    Uses Pydantic's model_dump for serialization.
    
    Args:
        question_list (list[Question]): List of Question objects to be serialized.
    Returns:
        dict: A dictionary containing serialized questions and their attributes.
    """
    return {
        "questions": [q.model_dump() for q in question_list],
        "size": len(question_list),
    }


def load_questions(ser_question_list: dict[str, Any]) -> list[Question]:
    """Loads a list of Question objects from a serialized dictionary format.
    
    Uses Pydantic's model_validate for deserialization.
    
    Args:
        ser_question_list (dict): Serialized question list containing questions
        and their attributes.
    Returns:
        list[Question]: A list of Question objects.
    """
    if not ser_question_list.get("questions"):
        return []
    
    questions: list[Question] = []
    for question_data in ser_question_list["questions"]:
        try:
            questions.append(Question.model_validate(question_data))
        except Exception as e:
            logger.warning(f"Failed to validate question: {e}")
            continue
    
    return questions
