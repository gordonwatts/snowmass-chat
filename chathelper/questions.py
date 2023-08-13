from pathlib import Path
from typing import Callable, List
from pydantic import BaseModel
import yaml


class Question(BaseModel):
    # The question text to submit to the model
    question: str


class QuestionSequence(BaseModel):
    # List of questions submitted to the model
    questions: list[Question]

    # Title of the question sequence
    title: str


class QuestionAndAnswer(BaseModel):
    # The question text to submitted to the model
    question: str
    # The answer text returned by the model
    answer: str


class QandASequence(BaseModel):
    # List of questions and answers
    questions: list[QuestionAndAnswer]
    # Title of the question sequence
    title: str
    # Description of the model config that generated these answers
    description: str


def load_questions(file_path: Path) -> QuestionSequence:
    """Load the question sequence from a yaml file.

    Args:
        file_path (Path): Location of the file to load

    Returns:
        QuestionSequence: The loaded question sequence
    """
    with open(file_path, "r") as f:
        return QuestionSequence(**yaml.safe_load(f))


def load_qanda(file_path: Path) -> QandASequence:
    """Load the question and answer sequence from a yaml file.

    Args:
        file_path (Path): Location of the file to load

    Returns:
        QandASequence: The loaded question and answer sequence
    """
    with open(file_path, "r") as f:
        return QandASequence(**yaml.safe_load(f))


def ask_questions(
    question_sequence: QuestionSequence, description: str, model: Callable[[str], str]
) -> QandASequence:
    """Ask the model the questions in the question sequence.

    Args:
        question_sequence (QuestionSequence): The questions to ask the model
        description (str): Description of the model config that generated these answers

    Returns:
        QandASequence: The questions and answers
    """
    questions_and_answers: List[QuestionAndAnswer] = []
    for question in question_sequence.questions:
        answer = model(question.question)
        questions_and_answers.append(
            QuestionAndAnswer(question=question.question, answer=answer)
        )
    return QandASequence(
        questions=questions_and_answers,
        title=question_sequence.title,
        description=description,
    )
