import json
import os
import random
from logging.config import dictConfig
from typing import Any, Dict, Optional

import click
import sqlalchemy.exc
from flask import Flask, jsonify, redirect, render_template, request, session

import google.genai.errors  # type: ignore

from bluebook import configuration, data_models, database_manager, generator, token_manager

# Compute the directory of the current file
app_dir = os.path.dirname(os.path.abspath(__file__))

# Set the absolute paths for templates and static folders
template_dir = os.path.join(app_dir, "templates")
static_dir = os.path.join(app_dir, "static")


# Initialize the application and its state
app = Flask("blue-book", template_folder=template_dir, static_folder=static_dir)
state: Dict[str, Any] = {
    "question_list": list[data_models.Question](),
    "exam_id": 0,
    "init": True,
}  # Initial exam - always sec+ as for now
app.secret_key = random.randbytes(32)
db_manager = database_manager.Database()


def concatenate_state_log(state_log: Optional[dict] = None) -> str:
    """ Concatenates the state log into a readable string format.
    If state_log is None, uses the global state variable.
    Args:
        state_log (Optional[dict]): Optional state log to use instead of the global state.
    Returns:
        str: A string representation of the state log.
    """
    if not state_log:
        global state
        num_of_questions = str(len(state["question_list"]))
        return f"State[ {num_of_questions} questions, exam_id={state['exam_id']}, is_init={state['init']}]"
    else:
        num_of_questions = str(len(state_log["question_list"]))
        return f"State[ {num_of_questions} questions, exam_id={state_log['exam_id']}, is_init={state_log['init']}]"


def state_to_json_string():
    """Serializes the current state to a JSON string.
    Returns:
        str: A JSON string representation of the current state.
    """
    global state
    questions = data_models.serialize_questions(state["question_list"])
    str_questions = json.dumps(questions)
    app.logger.debug(f"State [{concatenate_state_log()}] dumped to a json string.")
    return str_questions


def load_state_from_string(str_questions: str) -> None:
    """Loads the state from a JSON string.
    Args:
        str_questions (str): A JSON string representation of the questions.
    """
    global state
    app.logger.debug(f"Loading string into state; string length={len(str_questions)}.")
    try:
        serialised_questions = json.loads(str_questions)
        app.logger.debug("State string deserialised to python object successfully.")
    except json.JSONDecodeError:
        app.logger.debug("Invalid string. Reverting to {'questions': [], 'size': 0}.")
        serialised_questions = {"questions": [], "size": 0}
    state["question_list"] = data_models.load_questions(serialised_questions)


def set_additional_request(value: str | bool) -> None:
    """Sets the additional request in the session.
    Args:
        value (str or bool): The additional request value. If False, clears the request.
    """
    if not value:
        session["additional_request"] = {"set": False, "value": "", "saved": False}
        app.logger.debug("Additional request cleared.")
    else:
        saved_request = db_manager.select_extra_req_by_value(value)
        app.logger.debug(f"Additional request set to {value}")
        if saved_request:
            session["additional_request"] = {"set": True, "value": value, "saved": True}
        else:
            session["additional_request"] = {"set": True, "value": value, "saved": False}


def ensure_session() -> None:
    """Ensures that the session is initialized with required keys.
    If the session is not initialized, it sets default values. Which are:
    - 'init': True
    - 'submitted': False
    - 'additional_request': {'set': False, 'value': '', 'saved': False}
    - 'latest_num': '2'
    - 'TOKEN_PRESENT': False
    """
    if state["init"]:
        state["init"] = False
        switch_state(state["exam_id"])
    if "submitted" not in session:
        session["submitted"] = False
        app.logger.debug("session['submitted'] initialised to False.")
    if "additional_request" not in session:
        set_additional_request(False)
    if "latest_num" not in session:
        session["latest_num"] = "2"
        app.logger.debug("session['latest_num'] initialised to 2.")
    if "TOKEN_PRESENT" not in session:
        session["TOKEN_PRESENT"] = False
        app.logger.debug("session['TOKEN_PRESENT'] initialised to False.")


def obtain_saved_topics() -> dict[str, Any]:
    """Retrieves all saved topics from the database. returns a dictionary with the size and list of saved topics.
        in the format:

        {
            "size": int,
            "requests": List[{"id": int, "request": str}...]
        }
    """
    data: dict[str, Any] = {}
    all_saved_topics = db_manager.select_all_extra_requests()
    size = len(all_saved_topics)
    data["size"] = size
    data["requests"] = list()
    for topic in all_saved_topics:
        data["requests"].append(topic.to_dict())
    app.logger.debug(f"Saved topics retrieved for exam_id={state['exam_id']}. Size={data['size']}")
    return data


def obtain_exam_data() -> dict[str, Any]:
    """Retrieves the current exam data and all exams from the database. Returns a dictionary with the following structure:

    {
        "exam_list": List[{"id": int, "name": str}...],
        "current_exam": {"id": int, "name": str} or None,
        "built-in-indices": List[int]
    }
    """
    current_exam = db_manager.select_exam_by_id(state["exam_id"])
    exam_data = {
        "exam_list": db_manager.select_all_exams(),
        "current_exam": current_exam,
        "built-in-indices": db_manager.get_built_in_indices(),
    }
    if current_exam:
        app.logger.debug(
            f"Exam data retrieved: {len(exam_data['exam_list'])} total exams, current: name='{exam_data['current_exam']['name']}', id={exam_data['current_exam']['id']}"
        )
    else:
        app.logger.debug(
            f"Exam data retrieved: {len(exam_data['exam_list'])} total exams, current exam is not in the database."
        )
    return exam_data


def switch_state(exam_id: int) -> None:
    """Switches the current state to a new exam_id.
    Args:
        exam_id (int): The ID of the exam to switch to.
    """
    app.logger.debug(f"Switching state to exam_id={exam_id}")
    app.logger.debug(f"Initial state: {concatenate_state_log()}")
    # Setting new state
    global state
    global db_manager
    state["exam_id"] = exam_id
    db_manager = database_manager.Database(exam_id=exam_id)
    loaded_state = db_manager.load_state(exam_id)
    load_state_from_string(loaded_state["state_str"])
    set_additional_request(loaded_state["additional_request"])
    if state["question_list"]:
        session["submitted"] = True
        app.logger.debug("session['submitted'] changed to True.")
    else:
        session["submitted"] = False
        app.logger.debug("session['submitted'] changed to False.")
    app.logger.debug(f"New state: {concatenate_state_log()}")


def save_state() -> None:
    """This function serializes the current state and saves it to the database.
    It also logs the current state for debugging purposes.
    """
    current_exam_id = state["exam_id"]
    current_state_str = state_to_json_string()
    app.logger.debug(f"Saving state: {concatenate_state_log()}")
    db_manager.save_state(
        state_str=current_state_str,
        exam_id=current_exam_id,
        additional_request=session["additional_request"]["value"],
    )


@app.route("/generate", methods=["POST"])
def generate() -> str:
    """Generates new questions based on the user's input.
    This function handles the form submission from the root page, retrieves the number of questions,
    additional request, and generates questions using the Gemini API.
    If the token is not present, it redirects to the token prompt page.
    """
    config = token_manager.load_config()
    ensure_session()

    if token_page := token_manager.ensure_token(config):
        app.logger.debug("Token not found. Sending token page.")
        return token_page

    session["submitted"] = True
    app.logger.debug("session['submitted'] set to True")

    num_of_questions = int(request.form["num_of_questions"])
    session["latest_num"] = str(num_of_questions)
    app.logger.debug(f"session['latest_num'] set to {session['latest_num']}")

    additional_request = generator.sanitise_input(str(request.form["additional_request"]))
    if "additional_request_preset" in request.form:
        if request.form["additional_request_preset"]:
            additional_request = generator.sanitise_input(
                str(request.form["additional_request_preset"])
            )
    if not additional_request:
        app.logger.debug(f"Generating {num_of_questions} new questions")
        set_additional_request(False)
    else:
        app.logger.debug(
            f"Generating {num_of_questions} new questions with additional request {additional_request}"
        )
        set_additional_request(additional_request)
    try:
        app.logger.debug("Sending request to gemini...")
        gemini_response = generator.ask_gemini(
            exam_name=obtain_exam_data()["current_exam"]["name"],
            question_num=num_of_questions,
            token=config["API_TOKEN"],
            additional_request=additional_request,
        )
        app.logger.debug("Recieved response!")
    except google.genai.errors.ClientError:
        app.logger.debug("Token Error. Sending token page")
        return render_template("token_prompt.html.j2")
    global state
    state["question_list"] = gemini_response
    app.logger.debug(f"Updated state: {concatenate_state_log()}")
    return root()


@app.route("/")
def root() -> str:
    """Renders the root page of the application.
    It initializes the session, loads the configuration, and prepares the data for rendering.
    If the token is present, it sets the session variable accordingly.
    The function also serializes the current state of questions and prepares the saved topics and exam data.
    """
    config = token_manager.load_config()
    ensure_session()
    global state
    serialized_state = data_models.serialize_questions(question_list=state["question_list"])
    if not serialized_state:
        serialized_state["size"] = 0
    if token_manager.is_token_present(config):
        session["TOKEN_PRESENT"] = True
    else:
        session["TOKEN_PRESENT"] = False
    return render_template(
        "root.html.j2",
        data=serialized_state,
        saved_topics=obtain_saved_topics(),
        exams=obtain_exam_data(),
    )


@app.route("/save_token", methods=["POST"])
def save_token() -> str:
    """Saves the API token provided by the user.
    This function retrieves the token from the form data, loads the existing configuration,
    updates the API token in the configuration, and saves it back to the configuration file.
    After saving the token, it redirects to the root page.
    """
    api_token = request.form.get("API_TOKEN")
    config = token_manager.load_config()
    config["API_TOKEN"] = api_token
    token_manager.save_config(config)
    return root()


@app.route("/clear_token", methods=["POST"])
def clear_token() -> str:
    """Clears the API token from the session and configuration.
    This function removes the API token from the session, configuration, and configuration file.
    """
    token_manager.clear_token()
    return root()


@app.route("/wipe_questions", methods=["POST"])
def wipe_questions() -> str:
    """Wipes the current questions from the session and state.
    This function resets the session variables related to questions, sets the additional request to False,
    updates the latest number of questions, and clears the question list in the state.
    It also checks if the token is present in the session and logs the action.
    Finally, it redirects to the root page.
    """
    session["submitted"] = False
    set_additional_request(False)
    session["latest_num"] = "2"
    global state
    state["question_list"] = []
    if "TOKEN_PRESENT" not in session:
        session["TOKEN_PRESENT"] = False
    app.logger.debug(f"Questions wiped. State: {concatenate_state_log()}")
    return root()


@app.route("/check", methods=["POST"])
def check() -> str:
    """Checks the user's answers against the generated questions.
    This function retrieves the user's answers from the form data, compares them with the correct answers,
    and prepares the data for rendering the results page.
    It also updates the statistics based on the user's answers and serializes the original data.
    Finally, it renders the 'check.html.j2' template with the prepared data.
    """
    ensure_session()
    user_answers = {key: request.form[key] for key in request.form}
    app.logger.debug(user_answers)
    global state
    original_data = state["question_list"]
    statistics = data_models.Statistics()
    data_out = {
        "original_data": data_models.serialize_questions(original_data),
        "user_answers": {},
        "is_answer_correct": {},
        "statistics": {},
    }
    for i in range(len(original_data)):
        if original_data[i].choices[int(user_answers[str(i)])].is_correct:
            app.logger.debug(f"Question {i} Correct!")
            data_out["user_answers"][i] = int(user_answers[str(i)])
            data_out["is_answer_correct"][i] = True
            statistics.increment_both()
        else:
            app.logger.debug(f"Question {i} Incorrect!")
            data_out["user_answers"][i] = int(user_answers[str(i)])
            data_out["is_answer_correct"][i] = False
            statistics.increment_all_num()
    data_out["statistics"] = statistics.serialise()
    app.logger.debug(data_out)
    return render_template(
        "check.html.j2", data=data_out, saved_topics=obtain_saved_topics(), exams=obtain_exam_data()
    )


@app.route("/save-the-topic", methods=["POST"])
def save_the_topic() -> str:
    """Saves the additional request topic provided by the user.
    This function checks if the topic is present in the form data, attempts to save it to the database,
    and updates the session with the saved topic. If the topic is already present in the database,
    it logs a debug message and does not save it again.
    Finally, it redirects to the root page.
    """
    ensure_session()
    if "topic" in request.form:
        topic_to_save = session["additional_request"]["value"]
        try:
            db_manager.add_extra_request(topic_to_save)
            set_additional_request(topic_to_save)  # To update session
        except sqlalchemy.exc.IntegrityError:
            app.logger.debug(f"Topic {topic_to_save} was NOT saved: Already present.")
            pass
    return redirect("/")


@app.route("/remove-saved-topic", methods=["POST"])
def remove_saved_topic() -> str:
    """Removes a saved topic from the database.
    This function checks if the 'additional_request_preset' is present in the form data,
    retrieves the topic to delete, checks if it exists in the database,
    and attempts to remove it. If the topic is successfully removed,
    it updates the session with the new additional request.
    Finally, it redirects to the root page.
    """
    ensure_session()
    if "additional_request_preset" in request.form:
        topic_to_delete = request.form["additional_request_preset"]
        if db_manager.select_extra_req_by_value(topic_to_delete):
            app.logger.debug(f"Attempting to delete saved topic: {topic_to_delete}")
            db_manager.remove_extra_request_by_value(topic_to_delete)
            app.logger.debug(f"Topic was removed: {topic_to_delete}")
            set_additional_request(topic_to_delete)  # To update session
    return redirect("/")


@app.route("/save-question", methods=["POST"])
def save_question() -> str:
    """Saves a question to the database.
    This function checks if the 'q_index' is present in the form data,
    retrieves the corresponding question from the state, and attempts to save it to the database.
    If the question is already saved, it logs a debug message and returns a message indicating that.
    If the question is saved successfully, it returns a success message.
    If the 'q_index' is not found in the form data, it logs a debug message.
    """
    ensure_session()
    global state
    if "q_index" in request.form:
        question = state["question_list"][int(request.form["q_index"])]
        try:
            question.saved = True
            db_manager.add_question(question)
            app.logger.debug(f"Question {int(request.form['q_index'])} saved successfully.")
            return jsonify(
                {"message": f"Question {int(request.form['q_index'])} saved successfully."}
            )
        except sqlalchemy.exc.IntegrityError:
            app.logger.debug(f"Question {int(request.form['q_index'])} was already saved.")
            return jsonify(
                {"message": f"Question {int(request.form['q_index'])} was already saved."}
            )
    app.logger.debug("Question index not found in received form.")


@app.route("/remove-saved-question/endpoint", methods=["POST"])
def remove_saved_question() -> str:
    """Removes a saved question from the database.
    This function checks if the 'persistent_id' is present in the form data,
    retrieves the question ID, and attempts to remove it from the database.
    If the question is successfully removed, it logs a debug message and redirects to the saved questions page.
    If there is a database error or an unexpected error, it logs the error and redirects to the saved questions page.
    If the 'persistent_id' is not found in the form data, it logs a debug message and redirects to the saved questions page.
    """
    ensure_session()
    if "persistent_id" in request.form:
        id = int(request.form["persistent_id"])
        try:
            db_manager.remove_question_by_id(id)
            app.logger.debug(f"Remove question with id={id}.")
            return redirect("/saved-questions")
        except sqlalchemy.exc.SQLAlchemyError as e:
            app.logger.error(f"Database operation failed: {e}")
            app.logger.debug(f"Could not remove question with id={id}.")
        except Exception as e:
            app.logger.error(f"Unexpected error in remove_question_by_id: {e}")
            app.logger.debug(f"Could not remove question with id={id}.")
            return redirect("/saved-questions")
    else:
        app.logger.debug("Persistent id not found.")
        return redirect("/saved-questions")


@app.route("/clear-persistent-storage", methods=["POST"])
def clear_persistent_storage() -> str:
    """Clears the persistent storage and reinitialises the database.
    This function ensures that the session is initialized, clears the persistent storage,
    resets the saved status of all questions in the state, reinitialises the database manager,
    and switches the state to the default exam ID if the current exam ID is not in the built-in indices.
    Finally, it redirects to the root page.
    """
    ensure_session()
    global state
    global db_manager
    configuration.Configuration.SystemPath.clear_persistent()
    for question in state["question_list"]:
        question.saved = False
    db_manager = database_manager.Database()
    app.logger.debug("Database has been cleared and reinitialised.")
    if state["exam_id"] not in obtain_exam_data()["built-in-indices"]:
        switch_state(configuration.Configuration.DefaultValues.DEFAULT_EXAM_ID)
    return redirect("/")


@app.route("/saved-questions", methods=["GET"])
def saved_questions() -> str:
    """Renders the saved questions page.
    This function ensures that the session is initialized, retrieves all saved questions from the database,
    serializes the questions, and prepares the data for rendering the 'saved_questions.html.j2' template.
    It also obtains the saved topics and exam data to be displayed on the page.
    """
    ensure_session()
    questions = db_manager.select_all_questions_pydantic()
    serialised_questions = data_models.serialize_questions(questions)
    return render_template(
        "saved_questions.html.j2",
        serialised_questions=serialised_questions,
        saved_topics=obtain_saved_topics(),
        exams=obtain_exam_data(),
    )


@app.route("/set-exam", methods=["POST"])
def set_exam() -> str:
    """Switches to another exam based on the exam ID provided in the form data.
    This function ensures that the session is initialized, retrieves the new exam ID from the form data,
    saves the current state, and switches to the new exam state if the new exam ID is different from the current one.
    Finally, it redirects to the root page.
    """
    ensure_session()
    if "exam-id" in request.form:
        new_exam_id = int(request.form["exam-id"])
        app.logger.debug(f"Switching to another exam with id={new_exam_id}")
        # Saving existing state
        save_state()
        # Switching to a new state if different from current
        if new_exam_id != state["exam_id"]:
            switch_state(new_exam_id)
    return redirect("/")


@app.route("/exam-constructor", methods=["GET"])
def exam_constructor() -> str:
    """Renders the exam constructor page.
    This function ensures that the session is initialized, prepares custom data for rendering,
    and retrieves the exam data from the database.
    It returns the rendered 'exam_constructor.html.j2' template with the custom data and exam data.
    """
    ensure_session()
    custom = {"header": "Exam Constructor"}
    return render_template("exam_constructor.html.j2", custom=custom, exams=obtain_exam_data())


@app.route("/exam-constructor/add-custom-exam", methods=["POST"])
def add_custom_exam() -> str:
    """Adds a new custom exam based on the name provided in the form data.
    This function ensures that the session is initialized, retrieves the exam name from the form data,
    sanitizes the input, and adds the new exam to the database if the exam name is valid.
    If the exam name is not provided or is empty, it logs a debug message and does not add the exam.
    Finally, it redirects to the exam constructor page.
    """
    ensure_session()
    if "new-exam-name" in request.form:
        exam_name = generator.sanitise_input(request.form["new-exam-name"])
        if exam_name:
            db_manager.add_new_exam(exam_name=exam_name)
        else:
            app.logger.debug("Exam name was not provided. Abort adding new exam.")
    else:
        app.logger.debug("Exam name not found in received form. Abort adding new exam.")
    return redirect("/exam-constructor")


@app.route("/exam-constructor/delete-custom-exam", methods=["POST"])
def delete_custom_exam() -> str:
    """Deletes a custom exam based on the exam ID provided in the form data.
    This function ensures that the session is initialized, retrieves the exam ID from the form data,
    and attempts to delete the exam from the database if the exam ID is valid.
    If the exam ID is not provided or is empty, it logs a debug message and does not delete the exam.
    If the exam is successfully deleted and it was the current exam, it switches back to the default starting exam.
    Finally, it redirects to the exam constructor page.
    """
    ensure_session()
    if "exam-id" in request.form:
        exam_id = int(request.form["exam-id"])
        if exam_id:
            db_manager.delete_exam(exam_id=exam_id)
            if state["exam_id"] == exam_id:
                switch_state(
                    configuration.Configuration.DefaultValues.DEFAULT_EXAM_ID
                )  # Switch back to default starting exam
        else:
            app.logger.debug("Received exam id is empty. Abort removing exam.")
    else:
        app.logger.debug("Exam id not present in request form. Abort removing exam.")
    return redirect("/exam-constructor")


@click.group()
def bluebook() -> None:
    """
    Blue Book - advanced preparation questions generator for any exam. Based on gemini-flash-lite model
    This is a command line interface for the Blue Book application.
    """
    pass


@bluebook.command()
@click.option(
    "--debug", is_flag=True, show_default=True, default=False, help="Run flask app in debug mode"
)
def start(debug) -> None:
    """
    Start web server for Blue Book application.
    """
    if debug:
        dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                    }
                },
                "handlers": {
                    "wsgi": {
                        "class": "logging.StreamHandler",
                        "stream": "ext://flask.logging.wsgi_errors_stream",
                        "formatter": "default",
                    }
                },
                "root": {"level": "INFO", "handlers": ["wsgi"]},
                "loggers": {
                    "bluebook.database_manager": {
                        "level": "DEBUG",
                        "handlers": ["wsgi"],
                        "propagate": False,
                    },
                    "bluebook.generator": {
                        "level": "DEBUG",
                        "handlers": ["wsgi"],
                        "propagate": False,
                    },
                    "bluebook.token_manager": {
                        "level": "DEBUG",
                        "handlers": ["wsgi"],
                        "propagate": False,
                    },
                    "bluebook.data_models": {
                        "level": "DEBUG",
                        "handlers": ["wsgi"],
                        "propagate": False,
                    },
                },
            }
        )
        app.run(host="0.0.0.0", port=5000, debug=True, load_dotenv=True)
    else:
        dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                    }
                },
                "handlers": {
                    "wsgi": {
                        "class": "logging.StreamHandler",
                        "stream": "ext://flask.logging.wsgi_errors_stream",
                        "formatter": "default",
                    }
                },
                "root": {"level": "INFO", "handlers": ["wsgi"]},
            }
        )
        app.run(host="0.0.0.0", port=5000, debug=False, load_dotenv=True)


# run the application if this file is executed directly
if __name__ == "__main__":
    bluebook()
