from google import genai
import logging
import bleach
import re
from bluebook import data_models

logger = logging.getLogger("[Generator]")

def sanitise_input(input: str):
    sanitized = ''
    if len(input) > 90:
        sanitized = re.sub('[^0-9a-zA-Z ]+', '', input[:90])
        sanitized = bleach.clean(sanitized)
    else:
        sanitized = re.sub('[^0-9a-zA-Z ]+', '', input)
        sanitized = bleach.clean(sanitized)
    return sanitized


def gen_query(question_num, additional_request):
    query = f"""You are a Comptia Security+ examiner with 10 years of experience. You are the best in the world in creating preparation test questions for security+.
You need to create {str(question_num)} multiple choice questions. You are passionate about your work and aim to create detailed questions that are as close to exam questions as possible. Your explanations are in depth and allow students not only to check their knwoledge with your tests, but also learn something they did not know before.  For each question you must provide a study recommendation which would tell a student what exact topic they need to study to be able to answer the question."""
    if additional_request:
        query += f"The student has specifically asked you to focus on following topic(s): '{additional_request}'. You must focus on the mentioned topic and create questions related to it or to its adjacent Comptia Security+ Exam objective."
    return query


def ask_gemini(question_num, token, additional_request):
    query = gen_query(question_num, additional_request)
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

    logger.debug(f"Response: {response.text}")
    raw_questions: list[data_models._RawQuestion] = response.parsed
    questions = list[data_models.Question]()
    for raw_question in raw_questions:
        questions.append(data_models.Question.from_raw_question(raw_question))
        questions[-1].escape()
    return questions


if __name__ == "__main__":
    print(ask_gemini(2))