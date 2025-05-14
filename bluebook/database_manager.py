from sqlmodel import Field, SQLModel, Session, UniqueConstraint, create_engine, select, delete
from bluebook.confguration import Configuration
from bluebook import data_models


# Data Models
class ExtraRequest(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("request"),)
    id: int | None = Field(default=None, primary_key=True)
    request: str 

    def to_dict(self):
        return {'id': self.id, 'request': self.request}
    
class Questions(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("question"),)
    id: int | None = Field(default=None, primary_key=True)
    question: str
    study_recommendation: str
    saved: bool | None


class Choices(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    option: str
    explanation: str
    is_correct: bool
    question_id: int = Field(default=None, foreign_key="questions.id")


class Database:
    def __init__(self):
        # Setup the database
        self.engine = create_engine(f"sqlite:///{Configuration.SystemPath.DATABASE_PATH}")
        SQLModel.metadata.create_all(self.engine)

    def select_all_extra_requests(self):
        with Session(self.engine) as session:
            return session.exec(select(ExtraRequest)).all()
    
    def select_extra_req_by_id(self, id: int | str):
        if type(id) is str:
            try:
                id = int(id) # Best effort to convert to int
            except:
                pass
        with Session(self.engine) as session:
            return session.exec(select(ExtraRequest).where(ExtraRequest.id==id)).first()

    def select_extra_req_by_value(self, request: str):
        with Session(self.engine) as session:
            return session.exec(select(ExtraRequest).where(ExtraRequest.request == request)).first()
    
    def add_extra_request(self, request: int):
        extra_request = ExtraRequest(request=request)
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
            session.exec(delete(ExtraRequest).where(ExtraRequest.id==id))
            session.commit()
    
    def remove_extra_request_by_value(self, request):
        with Session(self.engine) as session:
            session.exec(delete(ExtraRequest).where(ExtraRequest.request==request))
            session.commit()
    

    def select_question_by_value(self, question: str,  pydantic=False):
        with Session(self.engine) as session:
            if not pydantic:
                return session.exec(select(Questions).where(Questions.question == question)).first()
            else:
                 if row:= session.exec(select(Questions).where(Questions.question == question)).first():
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
                return session.exec(select(Questions).where(Questions.id == persistent_id)).first()
            else:
                 if row:= session.exec(select(Questions).where(Questions.id == persistent_id)).first():
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
            question_to_insert = Questions(question=question.question, study_recommendation=question.study_recommendation, saved=True)
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
            if question:= session.exec(select(Questions).where(Questions.id == question_id)).first():
                # Question found
                session.exec(delete(Choices).where(Choices.question_id == question.id))
                session.exec(delete(Questions).where(Questions.id == question.id))
                session.commit()
            else:
                # Question not found
                pass
    

    def select_all_questions_pydantic(self):
        with Session(self.engine) as session:
            pydantic_questions = list[data_models.Question]()
            all_rows = session.exec(select(Questions))
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

        