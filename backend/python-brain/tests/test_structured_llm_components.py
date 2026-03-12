from app.llm.prompts import render_interview_question_prompt
from app.llm.structured import parse_question_output, question_output_format_instructions


def test_parse_question_output_accepts_valid_schema() -> None:
    data = parse_question_output({"question": "Explain retry strategy."})
    assert data.question


def test_prompt_template_renders() -> None:
    text = render_interview_question_prompt(
        target_role="Agent Engineer",
        topic="Retry",
        answer="I use exponential backoff",
    )
    assert "Agent Engineer" in text
    assert "Retry" in text


def test_question_output_format_instructions_non_empty() -> None:
    instructions = question_output_format_instructions()
    assert instructions
