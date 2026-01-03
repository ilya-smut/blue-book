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

class PromptBuilder:

    class PromptTemplate:
        EXAM_NAME_ANCHOR="##__EXAM_NAME_ANCHOR__##"
        QUESTION_NUM_ANCHOR="##__QUESTION_NUM_ANCHOR__##"
        ADDITIONAL_REQUEST_ANCHOR="##__ADDITIONAL_REQUEST_ANCHOR__##"
        ADDITIONAL_REQUESTS_SECTION_START_ANCHOR = "##__ADDITIONAL_REQUESTS_SECTION_START__##"
        ADDITIONAL_REQUESTS_SECTION_END_ANCHOR = "##__ADDITIONAL_REQUESTS_SECTION_END__##"
        MANDATORY_ANCHORS = [EXAM_NAME_ANCHOR, QUESTION_NUM_ANCHOR]
        OPTIONAL_ANCHORS = [ADDITIONAL_REQUEST_ANCHOR, ADDITIONAL_REQUESTS_SECTION_START_ANCHOR, ADDITIONAL_REQUESTS_SECTION_END_ANCHOR]

        def __init__(self, prompt: str):
            self.prompt = prompt
            self.valid = self.verify_template_prompt(prompt=prompt)
            self.optional_anchors = dict[str, bool]()
            if not self.valid:
                for anchor in self.OPTIONAL_ANCHORS:
                    self.optional_anchors[anchor] = False
            else:
                for anchor in self.OPTIONAL_ANCHORS:
                    if anchor in prompt:
                        self.optional_anchors[anchor] = True
                    else:
                        self.optional_anchors[anchor] = False

        @classmethod
        def verify_template_prompt(cls, prompt):
            mandatory_anchors = cls.MANDATORY_ANCHORS
            cumulative_flag = True
            i = 0
            while cumulative_flag and i<len(mandatory_anchors):
                cumulative_flag = cumulative_flag and (mandatory_anchors[i] in prompt)
                i+=1
            return cumulative_flag
        
        def is_valid(self):
            return self.valid
        
        def has_additional_request_section(self):
            has_start = self.optional_anchors[self.ADDITIONAL_REQUESTS_SECTION_START_ANCHOR]
            has_end = self.optional_anchors[self.ADDITIONAL_REQUESTS_SECTION_END_ANCHOR]
            has_placeholder = self.optional_anchors[self.ADDITIONAL_REQUEST_ANCHOR]
            return has_start and has_end and has_placeholder
        
        def get_template_prompt(self, attempt_additional_response: bool):
            compiled_prompt = None
            if not self.valid:
                return compiled_prompt
            if self.has_additional_request_section() and attempt_additional_response:
                compiled_prompt =  "\n".join(
                    line for line in self.prompt.splitlines()
                    if line != self.ADDITIONAL_REQUESTS_SECTION_START_ANCHOR and line != self.ADDITIONAL_REQUESTS_SECTION_END_ANCHOR
                )
            elif self.has_additional_request_section and (not attempt_additional_response):
                out: list[str] = []
                skip = False
                for line in self.prompt.splitlines():
                    if line == self.ADDITIONAL_REQUESTS_SECTION_START_ANCHOR:
                        skip = True
                        continue
                    if line == self.ADDITIONAL_REQUESTS_SECTION_END_ANCHOR:
                        skip = False
                        continue
                    if not skip:
                        out.append(line)
                compiled_prompt = "\n".join(out)
            
            return compiled_prompt

        

    @staticmethod
    def append_default_header(prompt: str, exam_name, question_num):
        prompt += f"""
You are a world-class {exam_name} examiner.
You have 10 years of experience designing official exam questions.
Your goal is to produce exactly {question_num} multiple-choice questions.
Questions must mirror the style, rigor, and coverage of the actual {exam_name} exam.
"""
        return prompt
    
    @classmethod
    def append_default_task_spec(cls, prompt, question_num):
        prompt += f"""
---- Task ----
1. Create {question_num} distinct multiple-choice questions (questions only—no essays).
2. For each question:
    a. Provide 4 answer options.
    b. Indicate the correct option.
    c. Give a concise explanation of why the correct answer is right.
    d. Produce a detailed study recommendation that will help student to understand the question.
"""
        return prompt
    
    @classmethod
    def append_default_focus(cls, prompt, exam_name, additional_request, with_headers: bool = False):
        if with_headers:
            prompt += f"\n{cls.PromptTemplate.ADDITIONAL_REQUESTS_SECTION_START_ANCHOR}\n"
        else:
            prompt += "\n"
        prompt += f"""---- Focus ----
The student asked to focus on: “{additional_request}”.
Questions should cover that topic and be closely related to
{exam_name} exam objectives
"""
        if with_headers:
            prompt += f"{cls.PromptTemplate.ADDITIONAL_REQUESTS_SECTION_END_ANCHOR}\n"
        return prompt

    @classmethod
    def append_default_constraints(cls, prompt):
        prompt += """
---- Constraints ----
1. Questions must be non-trivial (medium to high difficulty).
2. Avoid any ambiguous wording; each question must have a single clear correct answer.
3. Do not include any references to "examiner", "student" or "you" in the question text
"""
        return prompt
    
    @classmethod
    def append_default_attached_files_handler(cls, prompt):
        prompt += """
---- Utilize Attached Files ----
A student has requested you to utilize the context provided in the files attached to the request.
Your primary focus MUST be on topics / context found in the attached files. 
"""
        return prompt

    @classmethod
    def build_default_query(cls, exam_name: str, question_num: int, additional_request: str|None, are_files_attached: bool = False, with_headers: bool = False) -> str:
        prompt = ""
        prompt = PromptBuilder.append_default_header(prompt, exam_name, question_num)
        prompt = PromptBuilder.append_default_task_spec(prompt, question_num)
        if additional_request:
            prompt = PromptBuilder.append_default_focus(prompt, exam_name, additional_request, with_headers=with_headers)
        if are_files_attached:
            prompt = PromptBuilder.append_default_attached_files_handler(prompt)
        prompt = PromptBuilder.append_default_constraints(prompt)
        return prompt
    
    @classmethod
    def build_template_query(cls):
        return cls.build_default_query(exam_name=cls.PromptTemplate.EXAM_NAME_ANCHOR, question_num=cls.PromptTemplate.QUESTION_NUM_ANCHOR, additional_request=cls.PromptTemplate.ADDITIONAL_REQUEST_ANCHOR, are_files_attached=True, with_headers=True)
    
    @classmethod
    def build_custom_prompt(cls, template_query: str, exam_name: str, question_num: int, additional_request: str) -> str:
        replacements = {
            cls.PromptTemplate.EXAM_NAME_ANCHOR: exam_name,
            cls.PromptTemplate.QUESTION_NUM_ANCHOR: str(question_num),
            cls.PromptTemplate.ADDITIONAL_REQUEST_ANCHOR: additional_request,
        }
        template = cls.PromptTemplate(template_query)
        if not template.is_valid:
            prompt = cls.build_default_query(exam_name=exam_name, question_num=question_num, additional_request=additional_request)
            return prompt
        prompt = re.compile("|".join(map(re.escape, replacements)))
        return prompt.sub(lambda m: replacements[m.group(0)], template.get_template_prompt(attempt_additional_response=bool(additional_request)))
                


def ask_gemini(exam_name: str,
               question_num: int,
               token: Optional[str],
               additional_request: str|None = None,
               custom_prompt: str|None = None,
               attached_files: list = []) -> list[data_models.Question]:
    """Query the Gemini API to generate multiple-choice questions.
    Args:
        exam_name (str): The name of the exam for which questions are to be generated.
        question_num (int): The number of questions to generate.
        token (str): The API token for authentication.
        additional_request (str): Any additional request or focus area for the questions.
    Returns:
        list[data_models.Question]: A list of generated questions.
    """
    if not custom_prompt:
        query = PromptBuilder.build_default_query(
            exam_name=exam_name, question_num=question_num, additional_request=additional_request, are_files_attached=bool(attached_files)
        )
    else:
        query = PromptBuilder.build_custom_prompt(template_query=custom_prompt, exam_name=exam_name, question_num=question_num, additional_request=additional_request)
    logger.debug(f"Using following prompt: {query}")
    client = genai.Client(api_key=token)
    contents = [query]
    if attached_files:
        contents.extend(attached_files)
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=contents,
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
