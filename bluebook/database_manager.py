import sqlalchemy.exc
from sqlmodel import Field, SQLModel, Session, UniqueConstraint, create_engine, select, delete
from bluebook.confguration import Configuration
from bluebook import data_models
import logging

logger = logging.getLogger('bluebook.database_manager')


# Data Models
class ExtraRequest(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("request"),)
    id: int | None = Field(default=None, primary_key=True)
    request: str
    exam_id: int = Field(default=None, foreign_key="exams.id")

    def to_dict(self):
        return {'id': self.id, 'request': self.request}
    
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
    def __init__(self, exam_id=Configuration.DefaultValues.DEFAULT_EXAM_ID):
        # Default starting exam is CompTIA Security+ (exam_id=0)
        # Setup the database
        self.exam_id = exam_id
        self.built_in_indices = set()
        self.engine = create_engine(f"sqlite:///{Configuration.SystemPath.DATABASE_PATH}")
        SQLModel.metadata.create_all(self.engine)

        # Initialising built-in exams
        preset_exams =list[Exams]()
        preset_exams.append(Exams(id=0, name='CompTIA Security+'))
        preset_exams.append(Exams(id=1, name='CompTIA A+'))
        preset_exams.append(Exams(id=2, name='CompTIA Network+'))
        for exam in preset_exams:
            with Session(self.engine) as session:
                try:
                    session.add(exam)
                    session.commit()
                    self.built_in_indices.add(exam.id)
                except sqlalchemy.exc.IntegrityError:
                    self.built_in_indices.add(exam.id)
                    # It is already there - all good.
    
    # List of built-in exams. Will be used to avoid deleting built-in exams.
    def get_built_in_indices(self):
        return list(self.built_in_indices)


    def select_all_extra_requests(self):
        with Session(self.engine) as session:
            return session.exec(select(ExtraRequest).where(ExtraRequest.exam_id==self.exam_id)).all()
    
    def select_extra_req_by_id(self, id: int | str):
        if type(id) is str:
            try:
                id = int(id) # Best effort to convert to int
            except:
                pass
        with Session(self.engine) as session:
            return session.exec(select(ExtraRequest).where(ExtraRequest.id==id, ExtraRequest.exam_id==self.exam_id)).first()

    def select_extra_req_by_value(self, request: str):
        with Session(self.engine) as session:
            return session.exec(select(ExtraRequest).where(ExtraRequest.request == request, ExtraRequest.exam_id==self.exam_id)).first()
    
    def add_extra_request(self, request: int):
        extra_request = ExtraRequest(request=request, exam_id=self.exam_id)
        with Session(self.engine) as session:
            session.add(extra_request)
            session.commit()
    
    def remove_extra_request_by_id(self, id):
        if type(id) is str:
            try:
                id = int(id) # Best effort to convert to int
            except:
                pass
        with Session(self.engine) as session:
            session.exec(delete(ExtraRequest).where(ExtraRequest.id==id, ExtraRequest.exam_id==self.exam_id))
            session.commit()
    
    def remove_extra_request_by_value(self, request):
        with Session(self.engine) as session:
            session.exec(delete(ExtraRequest).where(ExtraRequest.request==request, ExtraRequest.exam_id==self.exam_id))
            session.commit()
    

    def select_question_by_value(self, question: str,  pydantic=False):
        with Session(self.engine) as session:
            if not pydantic:
                return session.exec(select(Questions).where(Questions.question == question, Questions.exam_id == self.exam_id)).first()
            else:
                 if row:= session.exec(select(Questions).where(Questions.question == question, Questions.exam_id == self.exam_id)).first():
                    choices_rows = session.exec(select(Choices).where(Choices.question_id == row.id))
                    choices = list[data_models.Choice]()
                    for choice_row in choices_rows:
                        choices.append(data_models.Choice(
                            option=choice_row.option,
                            is_correct=choice_row.is_correct,
                            explanation=choice_row.explanation
                        ))
                    question = data_models.Question(
                        question=row.question,
                        choices=choices,
                        study_recommendation=row.study_recommendation,
                        saved=True,
                        persistent_id=row.id
                    )
                    return question
    

    def select_question_by_id(self, persistent_id: int,  pydantic=False):
        with Session(self.engine) as session:
            if not pydantic:
                return session.exec(select(Questions).where(Questions.id == persistent_id, Questions.exam_id == self.exam_id)).first()
            else:
                 if row:= session.exec(select(Questions).where(Questions.id == persistent_id, Questions.exam_id == self.exam_id)).first():
                    choices_rows = session.exec(select(Choices).where(Choices.question_id == row.id))
                    choices = list[data_models.Choice]()
                    for choice_row in choices_rows:
                        choices.append(data_models.Choice(
                            option=choice_row.option,
                            is_correct=choice_row.is_correct,
                            explanation=choice_row.explanation
                        ))
                    question = data_models.Question(
                        question=row.question,
                        choices=choices,
                        study_recommendation=row.study_recommendation,
                        saved=True,
                        persistent_id=row.id
                    )
                    return question


    def add_question(self, question: data_models.Question):
        with Session(self.engine) as session:
            question_to_insert = Questions(question=question.question, study_recommendation=question.study_recommendation, saved=True, exam_id=self.exam_id)
            session.add(question_to_insert)
            session.commit()
            assinged_id = self.select_question_by_value(question.question).id
            choices_to_map = list[Choices]()
            for choice in question.choices:
                choice_to_insert = Choices(
                    option=choice.option, 
                    explanation=choice.explanation, 
                    is_correct=choice.is_correct, 
                    question_id=assinged_id
                    )
                choices_to_map.append(choice_to_insert)
            session.add_all(choices_to_map)
            session.commit()
    

    def remove_question_by_id(self, question_id: int):
        with Session(self.engine) as session:
            if question:= session.exec(select(Questions).where(Questions.id == question_id, Questions.exam_id == self.exam_id)).first():
                # Question found
                session.exec(delete(Choices).where(Choices.question_id == question.id))
                session.exec(delete(Questions).where(Questions.id == question.id, Questions.exam_id == self.exam_id))
                session.commit()
            else:
                # Question not found
                pass
    

    def select_all_questions_pydantic(self):
        with Session(self.engine) as session:
            pydantic_questions = list[data_models.Question]()
            all_rows = session.exec(select(Questions).where(Questions.exam_id == self.exam_id))
            for question_row in all_rows:
                choices_rows = session.exec(select(Choices).where(Choices.question_id == question_row.id))
                choices = list[data_models.Choice]()
                for choice_row in choices_rows:
                    choices.append(data_models.Choice(
                        option=choice_row.option,
                        is_correct=choice_row.is_correct,
                        explanation=choice_row.explanation,
                    ))
                question = data_models.Question(
                    question=question_row.question,
                    choices=choices,
                    study_recommendation=question_row.study_recommendation,
                    saved=True,
                    persistent_id=question_row.id
                )
                pydantic_questions.append(question)
            return pydantic_questions

    
    def save_state(self, state_str: str, exam_id: int, additional_request: str = None):
        with Session(self.engine) as session:
            state_obj = session.exec(select(States).where(States.exam_id == exam_id)).first()
            if state_obj:
                logger.debug(f'Updating existing state record.')
                state_obj.state = state_str
                state_obj.additional_request = additional_request
                session.add(state_obj)
            else:
                logger.debug(f'Creating new state record.')
                new_state = States(exam_id=exam_id, state=state_str, additional_request=additional_request)
                session.add(new_state)
            session.commit()
    

    def load_state(self, exam_id: int):
        out_state_str = {'state_str':'', 'exam_id': exam_id, 'additional_request': None}
        with Session(self.engine) as session:
            loaded_state = session.exec(select(States).where(States.exam_id == exam_id)).first()
            if loaded_state:
                out_state_str['state_str'] = loaded_state.state
                out_state_str['additional_request'] = loaded_state.additional_request
        return out_state_str
    

    def select_all_exams(self) -> list[dict]:
        exams = []
        with Session(self.engine) as session:
            exams_rows = session.exec(select(Exams))
            for row in exams_rows:
                exams.append({'id': row.id, 'name': row.name})
        return exams


    def select_exam_by_id(self, exam_id: int):
        data_out = {}
        with Session(self.engine) as session:
            exam_row = session.exec(select(Exams).where(Exams.id == exam_id)).first()
            if exam_row:
                data_out = {'id': exam_row.id, 'name': exam_row.name}
        return data_out
    
    
    def add_new_exam(self, exam_name: str):
        exam = Exams(name=exam_name)
        with Session(self.engine) as session:
            try:
                session.add(exam)
                session.commit()
            except sqlalchemy.exc.IntegrityError:
                pass # It is already there - all good.
    
    def delete_exam(self, exam_id: int):
        if exam_id not in self.built_in_indices:
            with Session(self.engine) as session:
                mapped_question_ids = session.exec(select(Questions.id).where(Questions.exam_id == exam_id)).all()
                for question_id in mapped_question_ids:
                    session.exec(delete(Choices).where(Choices.question_id == question_id))
                    session.exec(delete(Questions).where(Questions.id == question_id))
                session.exec(delete(ExtraRequest).where(ExtraRequest.exam_id == exam_id))
                session.exec(delete(States).where(States.exam_id == exam_id))
                session.exec(delete(Exams).where(Exams.id == exam_id))
                session.commit()


        
