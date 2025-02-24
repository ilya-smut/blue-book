from flask import Flask, render_template, request
from dotenv import dotenv_values
import generator

app = Flask("blue-book", template_folder="templates", static_folder="static")
config = dotenv_values(".env")
state = {}


@app.route("/generate")
def generate():
    num_of_questions = int(request.args.to_dict()['num_of_questions'])
    app.logger.debug(f"Generating {num_of_questions} new questions")
    gemini_response = generator.ask_gemini(num_of_questions)
    global state
    state = gemini_response
    return root()


@app.route("/")
def root():
    global state
    if not state:
        state['size'] = 0
    app.logger.debug(state)
    return render_template("root.html.j2", data=state)


@app.route("/check", methods=["POST"])
def check():
    user_answers = {key: request.form[key] for key in request.form}
    app.logger.debug(user_answers)
    global state
    original_data = state
    data_out = {"original_data": original_data, "user_answers": {}, "is_answer_correct":{}}
    for i in range(original_data['size']):
        if original_data['questions'][i]['choices'][int(user_answers[str(i)])]['is_correct']:
            app.logger.debug(f"Question {i} Correct!")
            data_out["user_answers"][i] = int(user_answers[str(i)])
            data_out["is_answer_correct"][i] = True
        else:
            app.logger.debug(f"Question {i} Incorrect!")
            data_out["user_answers"][i] = int(user_answers[str(i)])
            data_out["is_answer_correct"][i] = False
    app.logger.debug(data_out)
    return render_template("check.html.j2", data=data_out)


if __name__ == "__main__":
    app.run("localhost", "5000", True, True)