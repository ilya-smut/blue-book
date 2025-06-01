import logging
from typing import Any

import bleach
from pydantic import BaseModel

logger = logging.getLogger("bluebook.data_models")


class Statistics:
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

    def serialise(self) -> dict[str, int]:
        """Serializes the statistics into a dictionary."""
        return {"all": self.all_num, "correct": self.correct, "incorrect": self.get_incorrect_num()}


class Choice(BaseModel):
    option: str
    is_correct: bool
    explanation: str

    def escape(self) -> None:
        """Escapes the content of the choice to prevent XSS attacks."""
        self.option = bleach.clean(self.option)
        self.explanation = bleach.clean(self.explanation)


class _RawQuestion(BaseModel):
    """Raw question model used for parsing the response from the AI."""
    question: str
    choices: list[Choice]
    study_recommendation: str


class Question(BaseModel):
    question: str
    choices: list[Choice]
    study_recommendation: str
    saved: (
        bool | None
    )  # Optional field to identify if question is saved or not, in state. Not saved persistently.
    persistent_id: int | None

    def escape(self) -> None:
        """Escapes the content of the question and choices to prevent XSS attacks."""
        self.question = bleach.clean(self.question)
        for choice in self.choices:
            choice.escape()

    @classmethod
    def from_raw_question(cls, raw_question: _RawQuestion) -> "Question":
        """Creates a Question object from a raw question model.
        Args:
            raw_question (_RawQuestion): The raw question model containing the question data.
        Returns:
            Question: A new Question object created from the raw question data.
        """
        new_question = Question(
            question=raw_question.question,
            choices=raw_question.choices,
            study_recommendation=raw_question.study_recommendation,
            saved=None,
            persistent_id=None,
        )
        return new_question


def serialize_questions(question_list: list[Question]) -> dict[str, Any]:
    """Serializes a list of Question objects into a dictionary format.
    Args:
        question_list (list[Question]): List of Question objects to be serialized.
    Returns:
        dict: A dictionary containing serialized questions and their attributes.
    """
    serialized: dict[str, Any] = {"questions": [], "size": 0}
    for question in question_list:
        serialized["questions"].append(
            {
                "question": question.question,
                "choices": [],
                "study_recommendation": question.study_recommendation,
                "saved": question.saved,
                "persistent_id": question.persistent_id,
            },
        )
        for choice in question.choices:
            serialized["questions"][-1]["choices"].append(
                {
                    "option": choice.option,
                    "is_correct": choice.is_correct,
                    "explanation": choice.explanation,
                },
            )
        serialized["size"] += 1
    return serialized


def load_questions(ser_question_list: dict[str, Any]) -> list[Question]:
    """Loads a list of Question objects from a serialized dictionary format.
    Args:
        ser_question_list (dict): Serialized question list containing questions
        and their attributes.
    Returns:
        list[Question]: A list of Question objects.
    """
    question_list = list[Question]()
    if not ser_question_list["questions"]:
        return question_list

    for i in range(ser_question_list["size"]):
        choices = list[Choice]()
        for choice_dict in ser_question_list["questions"][i]["choices"]:
            choices.append(
                Choice(
                    option=choice_dict["option"],
                    is_correct=choice_dict["is_correct"],
                    explanation=choice_dict["explanation"],
                ),
            )

        question_list.append(
            Question(
                question=ser_question_list["questions"][i]["question"],
                choices=choices,
                study_recommendation=ser_question_list["questions"][i]["study_recommendation"],
                saved=ser_question_list["questions"][i]["saved"],
                persistent_id=ser_question_list["questions"][i]["persistent_id"],
            ),
        )

    return question_list
