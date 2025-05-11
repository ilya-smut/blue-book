from pydantic import BaseModel
import bleach

class Choice(BaseModel):
    option: str
    is_correct: bool
    explanation: str

    def escape(self):
        self.option = bleach.clean(self.option)
        self.explanation = bleach.clean(self.explanation)


class Question(BaseModel):
    question: str
    choices: list[Choice]

    def escape(self):
        self.question = bleach.clean(self.question)
        for choice in self.choices:
            choice.escape()