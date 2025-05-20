![Bluebook Logo](https://github.com/ilya-smut/blue-book/blob/main/bluebook/static/images/book.png?raw=true)
# Blue Book
![demo-gif](https://github.com/ilya-smut/blue-book/blob/main/examples/videos/bluebook%20gif.gif?raw=true)

Blue Book is an application that generates multiple-choice questions for IT certifications, e.g.  **CompTIA A+**, **Network+**, and **Security+**. It uses the Gemini API to generate questions and provides instant feedback on answers.

[Project's Homepage](https://student-bluebook.notion.site/)

## Features

- Generate multiple-choice questions for any IT certifications, including **CompTIA A+**, **Network+**, and **Security+**. Add more certifications using **Exam Constructor**
- Easily switch between preset exams or add your own custom certifications.
- Focus question generation on specific topics or objectives.
- Save and access custom topics for future use, per certification.
- Submit answers and receive immediate feedback with detailed explanations.
- Get personalized study recommendations based on your answers.
- Save individual questions for later revision.
- **Persistent state**: all saved questions and topics are retained across sessions.
- **Isolated storage** per certification ensures organized progress tracking.
- Run the app in a Docker container with a single command and minimal setup.


### Switching between certifications
![switching-exam](https://github.com/ilya-smut/blue-book/blob/main/examples/videos/switching_exam.gif?raw=true)

Easily switch between built-in certifications.


### Add more certifications
![exam-constructor](https://github.com/ilya-smut/blue-book/blob/main/examples/videos/exam_constructor.gif?raw=true)

Use Exam constructor to add more certifications to the list.


### All certs have their own state
![isolated-exams](https://github.com/ilya-smut/blue-book/blob/main/examples/videos/isolated_exams.gif?raw=true)

All exams have their own space for saved topics and saved questions.


## Installation

You can install bluebook with pip:
   ```sh
   pip install student-bluebook
   ```

With pipx
   ```sh
   pipx install student-bluebook
   ```

Or you can simply run it in a docker container
   ```sh
   docker run -d -p 5000:5000 --platform linux/amd64 ilyasmut/student-bluebook
   ```
   or
   ```sh
   git clone https://github.com/ilya-smut/blue-book
   cd blue-book/
   docker compose up -d
   ```

## Usage

Please see bluebook's interface and capabilities on this wiki page [wiki page](https://github.com/ilya-smut/blue-book/wiki):

To start the application, use the following command:
```sh
bluebook start
```

## Contributing
If you’d like to contribute to Blue Book, feel free to submit a pull request or open an issue.

## License
This project is licensed under the GPLv3

## Contact
For any questions or feedback, feel free to reach out.

