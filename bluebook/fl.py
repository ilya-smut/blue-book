from flask import Flask, render_template, request, session, redirect
from logging.config import dictConfig
import google.genai.errors
import os
import random
import click
import sqlalchemy.exc
from bluebook import generator
from bluebook import token_manager
from bluebook import database_manager

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


# Compute the directory of the current file
app_dir = os.path.dirname(os.path.abspath(__file__))

# Set the absolute paths for templates and static folders
template_dir = os.path.join(app_dir, 'templates')
static_dir = os.path.join(app_dir, 'static')


# Initialize the application and its state
app = Flask("blue-book", template_folder=template_dir, static_folder=static_dir)
state: list[generator.Question] = [] # Essentially a list of gennerated questions
app.secret_key = random.randbytes(32)
db_manager = database_manager.Database()


def set_additional_request(value):
    if not value:
        session['additional_request'] = {'set': False, 'value': '', 'saved': False}
    else:
        saved_request = db_manager.select_extra_req_by_value(value)
        if saved_request:
            session['additional_request'] = {'set': True, 'value': value, 'saved': True}
        else:
            session['additional_request'] = {'set': True, 'value': value, 'saved': False}


def ensure_session():
    if 'submitted' not in session:
        session['submitted'] = False
    if 'additional_request' not in session:
        set_additional_request(False)
    if 'latest_num' not in session:
        session['latest_num'] = '2'
    if 'TOKEN_PRESENT' not in session:
        session['TOKEN_PRESENT'] = False


def obtain_saved_topics():
    data = {}
    all_saved_topics = db_manager.select_all_extra_requests()
    size = len(all_saved_topics)
    data['size'] = size
    data['requests'] = []
    for topic in all_saved_topics:
        data['requests'].append(topic.to_dict())
    return data


@app.route("/generate", methods=['POST'])
def generate():
    config = token_manager.load_config()
    ensure_session()
    if token_page:= token_manager.ensure_token(config):
        return token_page
    session['submitted'] = True
    num_of_questions = int(request.form['num_of_questions'])
    session['latest_num'] = str(num_of_questions)
    additional_request = generator.sanitise_input(str(request.form['additional_request']))
    if "additional_request_preset" in request.form:
        if request.form['additional_request_preset']:
            additional_request = generator.sanitise_input(str(request.form['additional_request_preset']))
    if not additional_request:
        app.logger.debug(f"Generating {num_of_questions} new questions")
        set_additional_request(False)
    else:
        app.logger.debug(f"Generating {num_of_questions} new questions with additional request {additional_request}")
        set_additional_request(additional_request)
    try:
        gemini_response = generator.ask_gemini(num_of_questions, config['API_TOKEN'], additional_request=additional_request)
    except google.genai.errors.ClientError:
        return render_template("token_prompt.html.j2")
    global state
    state = gemini_response
    return root()


@app.route("/")
def root():
    config = token_manager.load_config()
    ensure_session()
    global state
    serialized_state = generator.serialize_questions(question_list=state)
    if not serialized_state:
        serialized_state['size'] = 0
    if token_manager.is_token_present(config):
        session['TOKEN_PRESENT'] = True
    else:
        session['TOKEN_PRESENT'] = False
    #app.logger.debug(serialized_state)
    return render_template("root.html.j2", data=serialized_state, saved_topics=obtain_saved_topics())


@app.route("/save_token", methods=["POST"])
def save_token():
    api_token = request.form.get("API_TOKEN")
    config = token_manager.load_config()
    config["API_TOKEN"] = api_token
    token_manager.save_config(config)
    return root()


@app.route("/clear_token", methods=["POST"])
def clear_token():
    token_manager.clear_token()
    return root()


@app.route("/wipe_questions", methods=["POST"])
def wipe_questions():
    session['submitted'] = False
    set_additional_request(False)
    session['latest_num'] = '2'
    global state
    state = []
    if 'TOKEN_PRESENT' not in session:
        session['TOKEN_PRESENT'] = False
    return root()


@app.route("/check", methods=["POST"])
def check():
    ensure_session()
    user_answers = {key: request.form[key] for key in request.form}
    app.logger.debug(user_answers)
    global state
    original_data = state
    statistics = Statistics()
    data_out = {"original_data": generator.serialize_questions(original_data), "user_answers": {}, "is_answer_correct":{}, "statistics": {}}
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
    data_out['statistics'] = statistics.serialise()
    app.logger.debug(data_out)
    return render_template("check.html.j2", data=data_out, saved_topics=obtain_saved_topics())


@app.route('/save-the-topic', methods=['POST'])
def save_the_topic():
    ensure_session()
    if "topic" in request.form:
        topic_to_save = session['additional_request']['value']
        try:
            db_manager.add_extra_request(topic_to_save)
            set_additional_request(topic_to_save) # To update session
        except sqlalchemy.exc.IntegrityError:
            app.logger.info("Topic was NOT saved: Already present.")
            pass
    return redirect("/")


@app.route('/remove-saved-topic', methods=['POST'])
def remove_saved_topic():
    ensure_session()
    if "topic" in request.form:
        topic_to_delete = session['additional_request']['value']
        if db_manager.select_extra_req_by_value(topic_to_delete):
            app.logger.debug(f'Attempting to delete saved topic: {topic_to_delete}')
            db_manager.remove_extra_request_by_value(topic_to_delete)
            app.logger.info(f'Topic was removed: {topic_to_delete}')
            set_additional_request(topic_to_delete) # To update session
    return redirect("/")


@click.group()
def bluebook():
    '''
    Blue Book - simple CompTIA Sec+ questions generator. Based on gemini-flash-lite model
    '''
    pass


@bluebook.command()
@click.option("--debug", is_flag=True, show_default=True, default=False, help="Run flask app in debug mode")
def start(debug):
    '''
    Start web server
    '''
    if debug:
        dictConfig({
            'version': 1,
            'formatters': {'default': {
                'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
            }},
            'handlers': {'wsgi': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://flask.logging.wsgi_errors_stream',
                'formatter': 'default'
            }},
            'root': {
                'level': 'INFO',
                'handlers': ['wsgi']
            }
        })
        app.run("0.0.0.0", "5000", True, True)
    else:
        dictConfig({
            'version': 1,
            'formatters': {'default': {
                'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
            }},
            'handlers': {'wsgi': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://flask.logging.wsgi_errors_stream',
                'formatter': 'default'
            }},
            'root': {
                'level': 'INFO',
                'handlers': ['wsgi']
            }
        })
        app.run("0.0.0.0", "5000", False, True)


if __name__ == "__main__":
    bluebook()