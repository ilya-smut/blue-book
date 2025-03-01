from flask import Flask, render_template, request
from logging.config import dictConfig
import google.genai.errors
from bluebook import generator
import os
import json
import click

# Compute the directory of the current file
app_dir = os.path.dirname(os.path.abspath(__file__))

# Set the absolute paths for templates and static folders
template_dir = os.path.join(app_dir, 'templates')
static_dir = os.path.join(app_dir, 'static')


# Determine the correct config directory based on OS
def get_config_directory():
    if os.name == "nt":  # Windows
        return os.path.join(os.getenv("APPDATA"), "bluebook")
    else:  # macOS/Linux
        return os.path.join(os.path.expanduser("~"), ".config", "bluebook")

# Ensure the directory exists
CONFIG_DIR = get_config_directory()
os.makedirs(CONFIG_DIR, exist_ok=True)
# Set the path for the config file
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

# Function to load configuration
def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

# Function to save configuration
def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

app = Flask("blue-book", template_folder=template_dir, static_folder=static_dir)
state: list[generator.Question] = []


@app.route("/generate")
def generate():
    config = load_config()
    if "API_TOKEN" not in config:
        return render_template("token_prompt.html.j2")
    num_of_questions = int(request.args.to_dict()['num_of_questions'])
    app.logger.debug(f"Generating {num_of_questions} new questions")
    try:
        gemini_response = generator.ask_gemini(num_of_questions, config['API_TOKEN'])
    except google.genai.errors.ClientError:
        return render_template("token_prompt.html.j2")
    global state
    state = gemini_response
    return root()


@app.route("/")
def root():
    config = load_config()
    if "API_TOKEN" not in config:
        return render_template("token_prompt.html.j2")  # Show input form
    global state
    serialized_state = generator.serialize_questions(question_list=state)
    if not serialized_state:
        serialized_state['size'] = 0
    app.logger.debug(serialized_state)
    return render_template("root.html.j2", data=serialized_state)


@app.route("/save_token", methods=["POST"])
def save_token():
    api_token = request.form.get("API_TOKEN")
    config = load_config()
    config["API_TOKEN"] = api_token
    save_config(config)
    return root()


@app.route("/check", methods=["POST"])
def check():
    user_answers = {key: request.form[key] for key in request.form}
    app.logger.debug(user_answers)
    global state
    original_data = state
    data_out = {"original_data": generator.serialize_questions(original_data), "user_answers": {}, "is_answer_correct":{}}
    for i in range(len(original_data)):
        if original_data[i].choices[int(user_answers[str(i)])].is_correct:
            app.logger.debug(f"Question {i} Correct!")
            data_out["user_answers"][i] = int(user_answers[str(i)])
            data_out["is_answer_correct"][i] = True
        else:
            app.logger.debug(f"Question {i} Incorrect!")
            data_out["user_answers"][i] = int(user_answers[str(i)])
            data_out["is_answer_correct"][i] = False
    app.logger.debug(data_out)
    return render_template("check.html.j2", data=data_out)


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
        app.run("localhost", "5000", True, True)
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
        app.run("127.0.0.1", "5000", False, True)


if __name__ == "__main__":
    bluebook()