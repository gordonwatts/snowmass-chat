from pathlib import Path

from chathelper.questions import (
    Question,
    QuestionSequence,
    ask_questions,
    load_questions,
)


def test_load_questions():
    q = load_questions(Path("tests/test_questions.yaml"))

    assert q.title == "Test Questions"
    assert len(q.questions) == 2
    assert q.questions[0].question == "Q1"
    assert q.questions[1].question == "Q2"


def test_ask_question():
    questions = QuestionSequence(
        title="Some Questions", questions=[Question(question="what is up")]
    )

    r = ask_questions(questions, description="desc1", model=lambda x: f"{x} - answer")

    assert r.title == "Some Questions"
    assert r.description == "desc1"
    assert len(r.questions) == 1
    assert r.questions[0].question == questions.questions[0].question
    assert r.questions[0].answer == f"{questions.questions[0].question} - answer"
