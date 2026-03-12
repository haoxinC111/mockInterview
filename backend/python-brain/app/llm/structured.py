from __future__ import annotations

from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


class QuestionOutput(BaseModel):
    question: str = Field(min_length=1)


_QUESTION_PARSER = PydanticOutputParser(pydantic_object=QuestionOutput)


def question_output_format_instructions() -> str:
    return _QUESTION_PARSER.get_format_instructions()


def parse_question_output(payload: dict[str, Any]) -> QuestionOutput:
    return QuestionOutput.model_validate(payload)
