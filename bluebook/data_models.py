from pydantic import BaseModel
import bleach

class Choice(BaseModel):
    option: str
    is_correct: bool
    explanation: str

    def escape(self):
        self.option = bleach.clean(self.option)
        self.explanation = bleach.clean(self.explanation)


class _RawQuestion(BaseModel):
    question: str
    choices: list[Choice]
    study_recommendation: str


class Question(BaseModel):
    question: str
    choices: list[Choice]
    study_recommendation: str
    saved: bool | None # Optional field to identify if question is saved or not, in state. Not saved persistently.
    persistent_id: int | None

    def escape(self):
        self.question = bleach.clean(self.question)
        for choice in self.choices:
            choice.escape()

    @classmethod
    def from_raw_question(cls, raw_question: _RawQuestion):
        new_question = Question(
            question = raw_question.question,
            choices = raw_question.choices,
            study_recommendation= raw_question.study_recommendation,
            saved=None,
            persistent_id=None
        )
        return new_question


def serialize_questions(question_list: list[Question]):
    serialized = {"questions": [], "size":0}
    for question in question_list:
        serialized['questions'].append(
            {
                'question': question.question,
                'choices':[],
                'study_recommendation': question.study_recommendation, 
                'saved': question.saved, 
                'persistent_id': question.persistent_id
            })
        for choice in question.choices:
            serialized['questions'][-1]['choices'].append(
                {
                    'option': choice.option, 
                    'is_correct': choice.is_correct, 
                    'explanation': choice.explanation
                })
        serialized['size'] += 1
    return serialized