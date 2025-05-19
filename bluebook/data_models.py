from pydantic import BaseModel
import bleach
import logging

logger = logging.getLogger('bluebook.data_models')

class Statistics:
    def __init__(self):
        self.all_num = 0
        self.correct = 0
    
    def get_correct_num(self):
        return self.correct
    
    def get_incorrect_num(self):
        return self.all_num - self.correct
    
    def increment_correct(self):
        self.correct += 1

    def increment_all_num(self):
        self.all_num += 1

    def increment_both(self):
        self.increment_all_num()
        self.increment_correct()

    def serialise(self):
        return {"all": self.all_num, "correct": self.correct, "incorrect": self.get_incorrect_num()}

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


def load_questions(ser_question_list):
    #logger.debug(f'Loading serialised list of questions: {ser_question_list}')
    question_list = list[Question]()
    if not ser_question_list['questions']:
        return question_list

    for i in range(ser_question_list['size']):
        choices = list[Choice]()
        for choice_dict in ser_question_list['questions'][i]['choices']:
            choices.append(Choice(option=choice_dict['option'],
                                  is_correct=choice_dict['is_correct'],
                                  explanation=choice_dict['explanation']))
            
        question_list.append(Question(question=ser_question_list['questions'][i]['question'],
                                      choices=choices,
                                      study_recommendation=ser_question_list['questions'][i]['study_recommendation'],
                                      saved=ser_question_list['questions'][i]['saved'],
                                      persistent_id=ser_question_list['questions'][i]['persistent_id']))
    
    return question_list