from google import genai
import logging
import bleach
import re
from bluebook import data_models

logger = logging.getLogger("bluebook.generator")

def sanitise_input(input: str):
    sanitized = ''
    if len(input) > 90:
        sanitized = re.sub('[^0-9a-zA-Z ]+-', '', input[:90])
        sanitized = bleach.clean(sanitized)
    else:
        sanitized = re.sub('[^0-9a-zA-Z ]+-', '', input)
        sanitized = bleach.clean(sanitized)
    return sanitized


def gen_default_query(exam_name, question_num, additional_request):
    """
    Builds a high-precision prompt for generating multiple-choice practice questions.
    """
    prompt = f"""
You are a world-class {exam_name} examiner with over 10 years of experience designing official exam questions.  
Your goal is to produce exactly {question_num} multiple-choice questions that mirror the style, rigor, and coverage of the actual {exam_name} exam.

## Task
1. Create {question_num} distinct multiple-choice questions (questions only—no essays).
2. For each question:
   - Provide 4 answer options.
   - Indicate the correct option.
   - Give a concise explanation of why the correct answer is right.
   - Produce a detailed study recommendation that will help student to fully understand this question.

## Focus
"""
    if additional_request:
        prompt += f"- The student asked to focus on: “{additional_request}”.  \n"
        prompt += f"- Questions should cover that topic and closely related {exam_name} exam objectives.\n"
    else:
        prompt += f"- No additional topic requested; cover a representative range of {exam_name} exam objectives.\n"

    prompt += """
## Constraints
- Questions must be non-trivial (medium to high difficulty).
- Avoid any ambiguous wording; each question must have a single clear correct answer.
- Do not include any references to “examiner”, "student" or “you” in the question text.
"""

    return prompt


def ask_gemini(exam_name, question_num, token, additional_request):
    query = gen_default_query(exam_name=exam_name, question_num=question_num, additional_request=additional_request)
    client = genai.Client(api_key=token)
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite-preview-02-05",
            contents=query,
            config={
                'response_mime_type': 'application/json',
                'response_schema': list[data_models._RawQuestion],
            },
        )
    # if server error, return empty list
    except genai.errors.ServerError as e:
        logger.error(f"Client error: {e}")
        return []
    
    raw_questions: list[data_models._RawQuestion] = response.parsed
    questions = list[data_models.Question]()
    for raw_question in raw_questions:
        questions.append(data_models.Question.from_raw_question(raw_question))
        questions[-1].escape()
    return questions
