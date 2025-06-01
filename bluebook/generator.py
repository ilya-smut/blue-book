import logging
import re
from typing import Optional

import bleach
from google import genai  # type: ignore

from bluebook import data_models

logger = logging.getLogger("bluebook.generator")


def sanitise_input(user_input: str) -> str:
    """Sanitizes the input string to prevent XSS attacks and ensure it is safe for use.
    Args:
        user_input (str): The input string to sanitize.
    Returns:
        str: The sanitized string, limited to 90 characters and cleaned of unsafe content.
    """
    sanitized = ""
    if len(user_input) > 90:
        sanitized = re.sub("[^0-9a-zA-Z ]+-", "", user_input[:90])
        sanitized = bleach.clean(sanitized)
    else:
        sanitized = re.sub("[^0-9a-zA-Z ]+-", "", user_input)
        sanitized = bleach.clean(sanitized)
    return sanitized


def gen_default_query(exam_name: str, question_num: int, additional_request: str) -> str:
    """Generates a default query for the Gemini API to create multiple-choice questions.
    Args:
        exam_name (str): The name of the exam for which questions are to be generated.
        question_num (int): The number of questions to generate.
        additional_request (str): Any additional request or focus area for the questions.
    Returns:
        str: The generated query string.
    """
    prompt = f"""
You are a world-class {exam_name} examiner.
You have 10 years of experience designing official exam questions.
Your goal is to produce exactly {question_num} multiple-choice questions.
Questions must mirror the style, rigor, and coverage of the actual {exam_name} exam.

## Task
1. Create {question_num} distinct multiple-choice questions (questions only—no essays).
2. For each question:
   - Provide 4 answer options.
   - Indicate the correct option.
   - Give a concise explanation of why the correct answer is right.
   - Produce a detailed study recommendation that will help student to understand the question.

## Focus
"""
    if additional_request:
        prompt += f"- The student asked to focus on: “{additional_request}”.  \n"
        prompt += ("- Questions should cover that topic and closely "
            "related {exam_name} exam objectives.\n")
    else:
        prompt += ("- No additional topic requested; cover a "
            "representative range of {exam_name} exam objectives.\n")

    prompt += """
## Constraints
- Questions must be non-trivial (medium to high difficulty).
- Avoid any ambiguous wording; each question must have a single clear correct answer.
- Do not include any references to “examiner”, "student" or “you” in the question text.
"""

    return prompt


def ask_gemini(exam_name: str,
               question_num: int,
               token: Optional[str],
               additional_request: str) -> list[data_models.Question]:
    """Query the Gemini API to generate multiple-choice questions.
    Args:
        exam_name (str): The name of the exam for which questions are to be generated.
        question_num (int): The number of questions to generate.
        token (str): The API token for authentication.
        additional_request (str): Any additional request or focus area for the questions.
    Returns:
        list[data_models.Question]: A list of generated questions.
    """
    query = gen_default_query(
        exam_name=exam_name, question_num=question_num, additional_request=additional_request,
    )
    client = genai.Client(api_key=token)
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite-preview-02-05",
            contents=query,
            config={
                "response_mime_type": "application/json",
                "response_schema": list[data_models._RawQuestion],
            },
        )
    # if server error, return empty list
    except genai.errors.ServerError as e:
        logger.error("Server error while generating questions", exc_info=e)
        return []

    raw_questions: list[data_models._RawQuestion] = response.parsed  # type: ignore
    questions = list[data_models.Question]()
    for raw_question in raw_questions:
        questions.append(data_models.Question.from_raw_question(raw_question))
        questions[-1].escape()
    return questions
