from flask import Flask, render_template, request, session, redirect, jsonify
from logging.config import dictConfig
import google.genai.errors
import os
import random
import json
import click
import sqlalchemy.exc
from bluebook import generator, token_manager, database_manager, data_models, confguration


def concatenate_state_log(state_log: dict = None):
    if not state_log:
        global state
        num_of_questions =str(len(state['question_list']))
        return f"State[ {num_of_questions} questions, exam_id={state['exam_id']}, is_init={state['init']}]"
    else:
        num_of_questions =str(len(state_log['question_list']))
        return f"State[ {num_of_questions} questions, exam_id={state_log['exam_id']}, is_init={state_log['init']}]"


def state_to_json_string():
    global state
    questions = data_models.serialize_questions(state['question_list'])
    str_questions = json.dumps(questions)
    app.logger.debug(f"State [{concatenate_state_log()}] dumped to a json string.")
    return str_questions


def load_state_from_string(str_questions: str):
    global state
    app.logger.debug(f'Loading string into state; string length={len(str_questions)}.')
    try:
        serialised_questions = json.loads(str_questions)
        app.logger.debug("State string deserialised to python object successfully.")
    except:
        app.logger.debug("Invalid string. Reverting to {'questions': [], 'size': 0}.")
        serialised_questions = {'questions': [], 'size': 0}
    state['question_list'] = data_models.load_questions(serialised_questions)


def set_additional_request(value):
    if not value:
        session['additional_request'] = {'set': False, 'value': '', 'saved': False}
        app.logger.debug("Additional request cleared.")
    else:
        saved_request = db_manager.select_extra_req_by_value(value)
        app.logger.debug(f"Additional request set to {value}")
        if saved_request:
            session['additional_request'] = {'set': True, 'value': value, 'saved': True}
        else:
            session['additional_request'] = {'set': True, 'value': value, 'saved': False}


def ensure_session():
    if state['init']:
        state['init'] = False
        switch_state(state['exam_id'])
    if 'submitted' not in session:
        session['submitted'] = False
        app.logger.debug(f"session['submitted'] initialised to False.")
    if 'additional_request' not in session:
        set_additional_request(False)
    if 'latest_num' not in session:
        session['latest_num'] = '2'
        app.logger.debug(f"session['latest_num'] initialised to 2.")
    if 'TOKEN_PRESENT' not in session:
        session['TOKEN_PRESENT'] = False
        app.logger.debug(f"session['TOKEN_PRESENT'] initialised to False.")


def obtain_saved_topics():
    data = {}
    all_saved_topics = db_manager.select_all_extra_requests()
    size = len(all_saved_topics)
    data['size'] = size
    data['requests'] = []
    for topic in all_saved_topics:
        data['requests'].append(topic.to_dict())
    app.logger.debug(f"Saved topics retrieved for exam_id={state['exam_id']}. Size={data['size']}")
    return data

def obtain_exam_data():
    current_exam = db_manager.select_exam_by_id(state['exam_id'])
    exam_data =  {'exam_list': db_manager.select_all_exams(),
                  'current_exam': current_exam,
                  'built-in-indices': db_manager.get_built_in_indices()}
    if current_exam:
        app.logger.debug(f"Exam data retrieved: {len(exam_data['exam_list'])} total exams, current: name='{exam_data['current_exam']['name']}', id={exam_data['current_exam']['id']}")
    else:
        app.logger.debug(f"Exam data retrieved: {len(exam_data['exam_list'])} total exams, current exam is not in the database.")
    return exam_data


def switch_state(exam_id:int):
    app.logger.debug(f'Switching state to exam_id={exam_id}')
    app.logger.debug(f'Initial state: {concatenate_state_log()}')
    # Setting new state
    global state
    global db_manager
    state['exam_id'] = exam_id
    db_manager = database_manager.Database(exam_id=exam_id)
    loaded_state = db_manager.load_state(exam_id)
    load_state_from_string(loaded_state['state_str'])
    set_additional_request(loaded_state['additional_request'])
    if state['question_list']:
        session['submitted'] = True
        app.logger.debug(f"session['submitted'] changed to True.")
    else:
        session['submitted'] = False
        app.logger.debug(f"session['submitted'] changed to False.")
    app.logger.debug(f"New state: {concatenate_state_log()}")
    


def save_state():
    # Saving current state (per exam)
    current_exam_id = state['exam_id']
    current_state_str = state_to_json_string()
    app.logger.debug(f'Saving state: {concatenate_state_log()}')
    db_manager.save_state(state_str=current_state_str, exam_id=current_exam_id, additional_request=session['additional_request']['value'])


# Compute the directory of the current file
app_dir = os.path.dirname(os.path.abspath(__file__))

# Set the absolute paths for templates and static folders
template_dir = os.path.join(app_dir, 'templates')
static_dir = os.path.join(app_dir, 'static')


# Initialize the application and its state
app = Flask("blue-book", template_folder=template_dir, static_folder=static_dir)
state = {'question_list': list[data_models.Question](),
                   'exam_id': 0, 'init': True} # Initial exam - always sec+ as for now
app.secret_key = random.randbytes(32)
db_manager = database_manager.Database()


@app.route("/generate", methods=['POST'])
def generate():
    config = token_manager.load_config()
    ensure_session()

    if token_page:= token_manager.ensure_token(config):
        app.logger.debug(f"Token not found. Sending token page.")
        return token_page
    
    session['submitted'] = True
    app.logger.debug(f"session['submitted'] set to True")

    num_of_questions = int(request.form['num_of_questions'])
    session['latest_num'] = str(num_of_questions)
    app.logger.debug(f"session['latest_num'] set to {session['latest_num']}")

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
        app.logger.debug(f"Sending request to gemini...")
        gemini_response = generator.ask_gemini(exam_name=obtain_exam_data()['current_exam']['name'],
                                                question_num=num_of_questions,
                                                token=config['API_TOKEN'],
                                                additional_request=additional_request)
        app.logger.debug("Recieved response!")
    except google.genai.errors.ClientError:
        app.logger.debug(f"Token Error. Sending token page")
        return render_template("token_prompt.html.j2")
    global state
    state['question_list'] = gemini_response
    app.logger.debug(f"Updated state: {concatenate_state_log()}")
    return root()


@app.route("/")
def root():
    config = token_manager.load_config()
    ensure_session()
    global state
    serialized_state = data_models.serialize_questions(question_list=state['question_list'])
    if not serialized_state:
        serialized_state['size'] = 0
    if token_manager.is_token_present(config):
        session['TOKEN_PRESENT'] = True
    else:
        session['TOKEN_PRESENT'] = False
    return render_template("root.html.j2", data=serialized_state, saved_topics=obtain_saved_topics(), exams=obtain_exam_data())


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
    state['question_list'] = []
    if 'TOKEN_PRESENT' not in session:
        session['TOKEN_PRESENT'] = False
    app.logger.debug(f"Questions wiped. State: {concatenate_state_log()}")
    return root()


@app.route("/check", methods=["POST"])
def check():
    ensure_session()
    user_answers = {key: request.form[key] for key in request.form}
    app.logger.debug(user_answers)
    global state
    original_data = state['question_list']
    statistics = data_models.Statistics()
    data_out = {"original_data": data_models.serialize_questions(original_data), "user_answers": {}, "is_answer_correct":{}, "statistics": {}}
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
    return render_template("check.html.j2", data=data_out, saved_topics=obtain_saved_topics(), exams=obtain_exam_data())


@app.route('/save-the-topic', methods=['POST'])
def save_the_topic():
    ensure_session()
    if "topic" in request.form:
        topic_to_save = session['additional_request']['value']
        try:
            db_manager.add_extra_request(topic_to_save)
            set_additional_request(topic_to_save) # To update session
        except sqlalchemy.exc.IntegrityError:
            app.logger.debug(f"Topic {topic_to_save} was NOT saved: Already present.")
            pass
    return redirect("/")


@app.route('/remove-saved-topic', methods=['POST'])
def remove_saved_topic():
    ensure_session()
    if "additional_request_preset" in request.form:
        topic_to_delete = request.form['additional_request_preset']
        if db_manager.select_extra_req_by_value(topic_to_delete):
            app.logger.debug(f'Attempting to delete saved topic: {topic_to_delete}')
            db_manager.remove_extra_request_by_value(topic_to_delete)
            app.logger.debug(f'Topic was removed: {topic_to_delete}')
            set_additional_request(topic_to_delete) # To update session
    return redirect("/")


@app.route('/save-question', methods=['POST'])
def save_question():
    ensure_session()
    global state
    if "q_index" in request.form:
        question = state['question_list'][int(request.form['q_index'])]
        try:
            question.saved = True
            db_manager.add_question(question)
            app.logger.debug(f"Question {int(request.form['q_index'])} saved successfully.")
            return jsonify({"message": f"Question {int(request.form['q_index'])} saved successfully."})
        except sqlalchemy.exc.IntegrityError:
            app.logger.debug(f"Question {int(request.form['q_index'])} was already saved.")
            return jsonify({"message": f"Question {int(request.form['q_index'])} was already saved."})
    app.logger.debug(f"Question index not found in received form.")
        

@app.route('/remove-saved-question/endpoint', methods=['POST'])
def remove_saved_question():
    ensure_session()
    if "persistent_id" in request.form:
        id = int(request.form['persistent_id'])
        try:
            db_manager.remove_question_by_id(id)
            app.logger.debug(f"Remove question with id={id}.")
            return redirect('/saved-questions')
        except:
            app.logger.debug(f"Could not remove question with id={id}.")
            return redirect('/saved-questions')
    else:
        app.logger.debug(f"Persistent id not found.")
        return redirect('/saved-questions')


@app.route('/clear-persistent-storage', methods=['POST'])
def clear_persistent_storage():
    ensure_session()
    global state
    global db_manager
    confguration.Configuration.SystemPath.clear_persistent()
    for question in state['question_list']:
        question.saved = False
    db_manager = database_manager.Database()
    app.logger.debug(f"Database has been cleared and reinitialised.")
    if state['exam_id'] not in obtain_exam_data()['built-in-indices']:
        switch_state(confguration.Configuration.DefaultValues.DEFAULT_EXAM_ID)
    return redirect('/')


@app.route('/saved-questions', methods=['GET'])
def saved_questions():
    ensure_session()
    questions = db_manager.select_all_questions_pydantic()
    serialised_questions = (data_models.serialize_questions(questions))
    return render_template("saved_questions.html.j2", 
                           serialised_questions=serialised_questions, 
                           saved_topics=obtain_saved_topics(), 
                           exams=obtain_exam_data())


@app.route('/set-exam', methods=['POST'])
def set_exam():
    ensure_session()
    if 'exam-id' in request.form:
        new_exam_id = int(request.form['exam-id'])
        app.logger.debug(f'Switching to another exam with id={new_exam_id}')
        # Saving existing state
        save_state()
        # Switching to a new state if different from current
        if new_exam_id != state['exam_id']:
            switch_state(new_exam_id)
    return redirect('/')


@app.route('/exam-constructor', methods=['GET'])
def exam_constructor():
    ensure_session()
    custom = {'header': 'Exam Constructor'}
    return render_template('exam_constructor.html.j2', custom=custom, exams=obtain_exam_data())

@app.route('/exam-constructor/add-custom-exam', methods=['POST'])
def add_custom_exam():
    ensure_session()
    if 'new-exam-name' in request.form:
        exam_name = generator.sanitise_input(request.form['new-exam-name'])
        if exam_name:
            db_manager.add_new_exam(exam_name=exam_name)
        else:
            app.logger.debug(f"Exam name was not provided. Abort adding new exam.")
    else:
        app.logger.debug(f"Exam name not found in received form. Abort adding new exam.")
    return redirect('/exam-constructor')

@app.route('/exam-constructor/delete-custom-exam', methods=['POST'])
def delete_custom_exam():
    ensure_session()
    if "exam-id" in request.form:
        exam_id = int(request.form['exam-id'])
        if exam_id:
            db_manager.delete_exam(exam_id=exam_id)
            if state['exam_id'] == exam_id:
                switch_state(confguration.Configuration.DefaultValues.DEFAULT_EXAM_ID) # Switch back to default starting exam
        else:
            app.logger.debug(f"Received exam id is empty. Abort removing exam.")
    else:
        app.logger.debug(f"Exam id not present in request form. Abort removing exam.")
    return redirect('/exam-constructor')

@click.group()
def bluebook():
    '''
    Blue Book - advanced preparation questions generator for any exam. Based on gemini-flash-lite model
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
            'disable_existing_loggers': False,
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
            },
            'loggers': {
                'bluebook.database_manager': {
                'level': 'DEBUG',
                'handlers': ['wsgi'],
                'propagate': False
                },
                'bluebook.generator':{
                'level': 'DEBUG',
                'handlers': ['wsgi'],
                'propagate': False
                },
                'bluebook.token_manager': {
                'level': 'DEBUG',
                'handlers': ['wsgi'],
                'propagate': False
                },
                'bluebook.data_models': {
                'level': 'DEBUG',
                'handlers': ['wsgi'],
                'propagate': False
                }
            }
        })
        app.run("0.0.0.0", "5000", True, True)
    else:
        dictConfig({
            'version': 1,
            'disable_existing_loggers': False,
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