from google import genai
from pydantic import BaseModel
import logging
import bleach
import re

logger = logging.getLogger("[Generator]")

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


def sanitise_input(input: str):
    sanitized = ''
    if len(input) > 90:
        sanitized = re.sub('[^0-9a-zA-Z ]+', '', input[:90])
        sanitized = bleach.clean(sanitized)
    else:
        sanitized = re.sub('[^0-9a-zA-Z ]+', '', input)
        sanitized = bleach.clean(sanitized)
    return sanitized


def serialize_questions(question_list):
    serialized = {"questions": [], "size":0}
    for question in question_list:
        serialized['questions'].append({'question': question.question, 'choices':[]})
        for choice in question.choices:
            serialized['questions'][-1]['choices'].append({'option': choice.option, 'is_correct': choice.is_correct, 'explanation': choice.explanation})
        serialized['size'] += 1
    return serialized


TEST_RESPONSE = {'questions': [{'question': 'A security administrator is tasked with implementing a new authentication system. The primary requirement is to ensure that users can only access resources during specific times of the day and on specific days of the week. Which of the following authentication methods would BEST satisfy this requirement?', 'choices': [{'option': 'Multi-factor authentication with biometric login.', 'is_correct': False, 'explanation': "While multi-factor authentication enhances security, biometrics alone doesn't inherently incorporate time-based restrictions. It verifies identity, not access schedules."}, {'option': 'Role-Based Access Control (RBAC) with time-based restrictions applied to the roles.', 'is_correct': True, 'explanation': 'RBAC allows administrators to assign permissions based on user roles. Time-based restrictions can be implemented to limit access to specific resources or actions during certain times or days, directly addressing the requirements.'}, {'option': 'Single Sign-On (SSO) with password synchronization across all applications.', 'is_correct': False, 'explanation': "SSO streamlines authentication, but it doesn't inherently provide time-based access controls. Password synchronization improves user experience but doesn't restrict access by time."}, {'option': 'Attribute-Based Access Control (ABAC) with location-based and device-based authentication.', 'is_correct': False, 'explanation': 'ABAC is more complex than RBAC. Although location and device can be attributes, the question highlights the time-based requirement. Without time configured, ABAC does not satisfy this primary requirement.'}]}, {'question': "A penetration tester has successfully gained access to a company's internal network by exploiting a vulnerability in a web application. After establishing a foothold, the tester wants to maintain persistent access and avoid detection. Which of the following techniques would be MOST effective for achieving this goal?", 'choices': [{'option': 'Conducting a full system audit and reporting all identified vulnerabilities immediately.', 'is_correct': False, 'explanation': "This action would alert the security team of the penetration testing activity and compromise the tester's access."}, {'option': 'Installing a rootkit to hide malicious processes and backdoors, along with creating a scheduled task to re-establish access if the initial foothold is lost.', 'is_correct': True, 'explanation': 'Rootkits provide persistent, stealthy access by hiding malicious code and processes. A scheduled task ensures that access is re-established even if the initial entry point is patched or removed. This combination is highly effective for maintaining long-term access.'}, {'option': 'Deleting all log files and system audit trails to cover their tracks.', 'is_correct': False, 'explanation': "While deleting logs can help hide activity, it's often detectable and doesn't establish persistent access. This is a reactive, not proactive, approach to persistence."}, {'option': "Changing the user's password to prevent other users from accessing the system and reporting the change to IT support to receive administrator privileges.", 'is_correct': False, 'explanation': 'This is an extremely aggressive approach that would likely trigger immediate security alerts and disrupt normal system operations, making it easily detectable and not ideal for stealthy persistence.'}]}], "size": 2}


def gen_query(question_num, additional_request):
    query = f"""You are a Comptia Security+ examiner with 10 years of experience. You are the best in the world in creating preparation test questions for security+.
You need to create {str(question_num)} multiple choice questions. You are passionate about your work and aim to create detailed questions that are as close to exam questions as possible. Your explanations are in depth and allow students not only to check their knwoledge with your tests, but also learn something they did not know before.  """
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
                'response_schema': list[Question],
            },
        )
    # if server error, return empty list
    except genai.errors.ServerError as e:
        logger.error(f"Client error: {e}")
        return []

    logger.debug(f"Response: {response.text}")
    questions: list[Question] = response.parsed
    for question in questions:
        question.escape()
    return questions




if __name__ == "__main__":
    print(ask_gemini(2))