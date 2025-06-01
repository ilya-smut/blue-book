import contextlib
import logging
from typing import Any, Optional

import sqlalchemy.exc
from sqlmodel import (
    Field,
    Session,
    SQLModel,
    UniqueConstraint,
    col,
    create_engine,
    delete,
    select,
)

from bluebook import data_models
from bluebook.configuration import Configuration

logger = logging.getLogger("bluebook.database_manager")


# Data Models
class ExtraRequest(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("request"),)
    id: int | None = Field(default=None, primary_key=True)
    request: str
    exam_id: int = Field(default=None, foreign_key="exams.id")

    def to_dict(self) -> dict[str, str | int | None]:
        """Converts the ExtraRequest instance to a dictionary.
            Returns a dictionary representation of the ExtraRequest instance in the format:

            {
                "id": int,  # The ID of the extra request
                "request": str  # The request string
            }
        """
        return {"id": self.id, "request": self.request}


class Questions(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("question"),)
    id: int | None = Field(default=None, primary_key=True)
    question: str
    study_recommendation: str
    saved: bool | None
    exam_id: int = Field(default=None, foreign_key="exams.id")


class Choices(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    option: str
    explanation: str
    is_correct: bool
    question_id: int = Field(default=None, foreign_key="questions.id")


class Exams(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("name"),)
    id: int | None = Field(default=None, primary_key=True)
    name: str


class States(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("exam_id"),)
    id: int | None = Field(default=None, primary_key=True)
    exam_id: int = Field(default=None, foreign_key="exams.id")
    state: str
    additional_request: str | None


class Database:
    def __init__(self, exam_id: int = Configuration.DefaultValues.DEFAULT_EXAM_ID) -> None:
        """
        Initializes the Database instance.
        Args:
            exam_id (int): The ID of the exam to work with.
            Defaults to CompTIA Security+ (exam_id=0).
        """
        # Default starting exam is CompTIA Security+ (exam_id=0)
        # Setup the database
        self.exam_id = exam_id
        self.built_in_indices = set[int]()
        self.engine = create_engine(f"sqlite:///{Configuration.SystemPath.DATABASE_PATH}")
        SQLModel.metadata.create_all(self.engine)

        # Initialising built-in exams
        preset_exams = list[Exams]()
        preset_exams.append(Exams(id=0, name="CompTIA Security+"))
        preset_exams.append(Exams(id=1, name="CompTIA A+"))
        preset_exams.append(Exams(id=2, name="CompTIA Network+"))
        for exam in preset_exams:
            with Session(self.engine) as session:
                try:
                    session.add(exam)
                    session.commit()
                    self.built_in_indices.add(exam.id) # type: ignore
                except sqlalchemy.exc.IntegrityError:
                    self.built_in_indices.add(exam.id) # type: ignore
                    # It is already there - all good.

    # List of built-in exams. Will be used to avoid deleting built-in exams.
    def get_built_in_indices(self) -> list[int]:
        """Returns a list of built-in exam indices.
        Returns:
            list[int]: A list of built-in exam indices.
        """
        return list(self.built_in_indices)

    def select_all_extra_requests(self) -> list[ExtraRequest]:
        """Selects all extra requests for the current exam.
        Returns:
            list[ExtraRequest]: A list of all extra requests for the current exam.
        """
        with Session(self.engine) as session:
            return list(session.exec(
                select(ExtraRequest).where(ExtraRequest.exam_id == self.exam_id),
            ).all())

    def select_extra_req_by_id(self, id: int | str) -> Optional[ExtraRequest]: # noqa: A002
        """Selects an extra request by its ID for the current exam.
        Args:
            id (int | str): The ID of the extra request to search for.
        Returns:
            Optional[ExtraRequest]: The extra request if found, otherwise None.
        """
        if type(id) is str:
            with contextlib.suppress(ValueError, TypeError):
                # Best effort to convert to int
                id = int(id)  # noqa: A001
        with Session(self.engine) as session:
            return session.exec(
                select(ExtraRequest).where(
                    ExtraRequest.id == id, ExtraRequest.exam_id == self.exam_id,
                ),
            ).first()

    def select_extra_req_by_value(self, request: str) -> Optional[ExtraRequest]:
        """Selects an extra request by its value for the current exam.
        Args:
            request (str): The extra request to search for.
        Returns:
            Optional[ExtraRequest]: The extra request if found, otherwise None."""
        with Session(self.engine) as session:
            return session.exec(
                select(ExtraRequest).where(
                    ExtraRequest.request == request, ExtraRequest.exam_id == self.exam_id,
                ),
            ).first()

    def add_extra_request(self, request: str) -> None:
        """Adds a new extra request for the current exam.
        Args:
            request (str): The extra request to add.
        Returns:
            None
        Raises:
            sqlalchemy.exc.IntegrityError: If the request already exists for the current exam.
        """
        extra_request = ExtraRequest(request=request, exam_id=self.exam_id)
        with Session(self.engine) as session:
            session.add(extra_request)
            session.commit()

    def remove_extra_request_by_id(self, request_id: int | str) -> None:
        """Removes an extra request by its ID for the current exam.
        Args:
            request_id (int | str): The ID of the extra request to remove.
        Returns:
            None
        """
        if type(request_id) is str:
            with contextlib.suppress(ValueError, TypeError):
                request_id = int(request_id)  # Best effort to convert to int
        with Session(self.engine) as session:
            session.exec(
                delete(ExtraRequest).where(
                    col(ExtraRequest.id) == id, col(ExtraRequest.exam_id) == self.exam_id,
                ),
            )  # type: ignore
            session.commit()

    def remove_extra_request_by_value(self, request: str) -> None:
        """Removes an extra request by its value for the current exam.
        Args:
            request (str): The value of the extra request to remove.
        Returns:
            None
        """
        with Session(self.engine) as session:
            session.exec(
                delete(ExtraRequest).where(
                    col(ExtraRequest.request) == request,
                    col(ExtraRequest.exam_id) == self.exam_id,
                ),
            )  # type: ignore
            session.commit()

    def select_question_by_value(self,
                                 question: str,
                                 pydantic: bool = False,
                                 ) -> Optional[data_models.Question | Questions]:
        """Selects a question by its value for the current exam.
        Args:
            question (str): The question text to search for.
            pydantic (bool): If True, returns a Pydantic model,
            otherwise returns a SQLModel instance.
        Returns:
            Optional[data_models.Question | Questions]: The question if found, otherwise None.
        """
        with Session(self.engine) as session:
            if not pydantic:
                return session.exec(
                    select(Questions).where(
                        Questions.question == question, Questions.exam_id == self.exam_id,
                    ),
                ).first()

            if row := session.exec(
                select(Questions).where(
                    Questions.question == question, Questions.exam_id == self.exam_id,
                ),
            ).first():
                choices_rows = session.exec(
                    select(Choices).where(Choices.question_id == row.id),
                )
                choices = list[data_models.Choice]()
                for choice_row in choices_rows:
                    choices.append(
                        data_models.Choice(
                            option=choice_row.option,
                            is_correct=choice_row.is_correct,
                            explanation=choice_row.explanation,
                        ),
                    )
                structured_question = data_models.Question(
                    question=row.question,
                    choices=choices,
                    study_recommendation=row.study_recommendation,
                    saved=True,
                    persistent_id=row.id,
                )
                return structured_question
        return None

    def select_question_by_id(self,
                              persistent_id: int,
                              pydantic: bool = False,
                              ) -> Optional[data_models.Question | Questions]:
        """Selects a question by its persistent ID for the current exam.
    Args:
            persistent_id (int): The persistent ID of the question to search for.
            pydantic (bool): If True, returns a Pydantic model,
            otherwise returns a SQLModel instance.
        """
        with Session(self.engine) as session:
            if not pydantic:
                return session.exec(
                    select(Questions).where(
                        Questions.id == persistent_id, Questions.exam_id == self.exam_id,
                    ),
                ).first()

            if row := session.exec(
                select(Questions).where(
                    Questions.id == persistent_id, Questions.exam_id == self.exam_id,
                ),
            ).first():
                choices_rows = session.exec(
                    select(Choices).where(Choices.question_id == row.id),
                )
                choices = list[data_models.Choice]()
                for choice_row in choices_rows:
                    choices.append(
                        data_models.Choice(
                            option=choice_row.option,
                            is_correct=choice_row.is_correct,
                            explanation=choice_row.explanation,
                        ),
                    )
                question = data_models.Question(
                    question=row.question,
                    choices=choices,
                    study_recommendation=row.study_recommendation,
                    saved=True,
                    persistent_id=row.id,
                )
                return question
        return None

    def add_question(self, question: data_models.Question) -> None:
        """
        Adds a new question to the current exam.

        Args:
            question (data_models.Question): The question to add, as a Pydantic model.
        Returns:
            None
        Raises:
            sqlalchemy.exc.IntegrityError: If the question already exists for the current exam.
        """
        with Session(self.engine) as session:
            question_to_insert = Questions(
                question=question.question,
                study_recommendation=question.study_recommendation,
                saved=True,
                exam_id=self.exam_id,
            )
            session.add(question_to_insert)
            session.commit()
            if obtained_question:= self.select_question_by_value(question.question, pydantic=False):
                assinged_id = obtained_question.id # type: ignore
            choices_to_map = list[Choices]()
            for choice in question.choices:
                choice_to_insert = Choices(
                    option=choice.option,
                    explanation=choice.explanation,
                    is_correct=choice.is_correct,
                    question_id=assinged_id, # type: ignore
                )
                choices_to_map.append(choice_to_insert)
            session.add_all(choices_to_map)
            session.commit()

    def remove_question_by_id(self, question_id: int) -> None:
        """Removes a question by its ID for the current exam.
        Args:
            question_id (int): The ID of the question to remove.
        Returns:
            None
        """
        with Session(self.engine) as session:
            if question := session.exec(
                select(Questions).where(
                    Questions.id == question_id, Questions.exam_id == self.exam_id,
                ),
            ).first():
                # Question found
                session.exec(delete(Choices).where(col(Choices.question_id) == question.id))  # type: ignore
                session.exec(
                    delete(Questions).where(
                        col(Questions.id) == question.id, col(Questions.exam_id) == self.exam_id,
                    ),
                )  # type: ignore
                session.commit()
            else:
                # Question not found
                pass

    def select_all_questions_pydantic(self) -> list[data_models.Question]:
        """Selects all questions for the current exam and returns them as Pydantic models.
        Returns:
            list[data_models.Question]: A list of all questions for the current exam
            as Pydantic models.
        """
        with Session(self.engine) as session:
            pydantic_questions = list[data_models.Question]()
            all_rows = session.exec(select(Questions).where(Questions.exam_id == self.exam_id))
            for question_row in all_rows:
                choices_rows = session.exec(
                    select(Choices).where(Choices.question_id == question_row.id),
                )
                choices = list[data_models.Choice]()
                for choice_row in choices_rows:
                    choices.append(
                        data_models.Choice(
                            option=choice_row.option,
                            is_correct=choice_row.is_correct,
                            explanation=choice_row.explanation,
                        ),
                    )
                question = data_models.Question(
                    question=question_row.question,
                    choices=choices,
                    study_recommendation=question_row.study_recommendation,
                    saved=True,
                    persistent_id=question_row.id,
                )
                pydantic_questions.append(question)
            return pydantic_questions

    def save_state(self,
                    state_str: str,
                    exam_id: int,
                    additional_request: Optional[str] = None) -> None:
        """
        Saves the state of the exam to the database.
        If a state record for the given exam_id already exists, it updates the record.
        If it does not exist, it creates a new record.
        Args:
            state_str (str): The state string to save.
            exam_id (int): The ID of the exam for which to save the state.
            additional_request (Optional[str]): An optional additional request string.
        Returns:
            None
        """
        with Session(self.engine) as session:
            state_obj = session.exec(select(States).where(States.exam_id == exam_id)).first()
            if state_obj:
                logger.debug("Updating existing state record.")
                state_obj.state = state_str
                state_obj.additional_request = additional_request
                session.add(state_obj)
            else:
                logger.debug("Creating new state record.")
                new_state = States(
                    exam_id=exam_id, state=state_str, additional_request=additional_request,
                )
                session.add(new_state)
            session.commit()

    def load_state(self, exam_id: int) -> dict[str, Any]:
        """ Loads the state of the exam from the database.
        If the state does not exist, it returns an empty state string
        and None for additional_request.
        Args:
            exam_id (int): The ID of the exam for which to load the state.
        """
        out_state_str = {"state_str": "", "exam_id": exam_id, "additional_request": None}
        with Session(self.engine) as session:
            loaded_state = session.exec(select(States).where(States.exam_id == exam_id)).first()
            if loaded_state:
                out_state_str["state_str"] = loaded_state.state
                out_state_str["additional_request"] = loaded_state.additional_request
        return out_state_str

    def select_all_exams(self) -> list[dict[str, Any]]:
        """Selects all exams from the database and returns them as a list of dictionaries.
        Returns:
            list[dict]: A list of dictionaries, each containing the ID and name of an exam.
        """
        with Session(self.engine) as session:
            exams_rows = session.exec(select(Exams))
            exams = [{"id": row.id, "name": row.name} for row in exams_rows]
            return exams
        return []

    def select_exam_by_id(self, exam_id: int) -> dict[str, Any]:
        """Selects an exam by its ID and returns it as a dictionary.
        Returns a dictionary in the format:
            {
                "id": int,
                "name": str
            }
        If the exam does not exist, it returns an empty dictionary.
        Args:
            exam_id (int): The ID of the exam to select.
        """
        data_out = {}
        with Session(self.engine) as session:
            exam_row = session.exec(select(Exams).where(Exams.id == exam_id)).first()
            if exam_row:
                data_out = {"id": exam_row.id, "name": exam_row.name}
        return data_out

    def add_new_exam(self, exam_name: str) -> None:
        """
        Adds a new exam to the database.
        If the exam already exists, it does nothing.
        Args:
            exam_name (str): The name of the exam to add.
        Returns:
            None
        """
        exam = Exams(name=exam_name)
        with Session(self.engine) as session, contextlib.suppress(sqlalchemy.exc.IntegrityError):
            session.add(exam)
            session.commit()
            # if exception occurs, it means the exam already exists

    def delete_exam(self, exam_id: int) -> None:
        """
        Deletes an exam by its ID from the database.
        This method will also delete all associated questions, choices, extra requests, and states.
        Args:
            exam_id (int): The ID of the exam to delete.
        Returns:
            None
        """
        if exam_id not in self.built_in_indices:
            with Session(self.engine) as session:
                mapped_question_ids = session.exec(
                    select(Questions.id).where(Questions.exam_id == exam_id),
                ).all()
                for question_id in mapped_question_ids:
                    session.exec(delete(Choices).where(col(Choices.question_id) == question_id))  # type: ignore
                    session.exec(delete(Questions).where(col(Questions.id) == question_id))  # type: ignore
                session.exec(delete(ExtraRequest).where(col(ExtraRequest.exam_id) == exam_id))  # type: ignore
                session.exec(delete(States).where(col(States.exam_id) == exam_id))  # type: ignore
                session.exec(delete(Exams).where(col(Exams.id) == exam_id))  # type: ignore
                session.commit()
