import json
import logging
import re
from langchain_anthropic import ChatAnthropic

from app.config import settings
from app.prompts.grading import GRADING_PROMPT
from app.models.schemas import QuizGradeRequest, QuizGradeResponse

logger = logging.getLogger(__name__)

llm = ChatAnthropic(
    model=settings.llm_model,
    api_key=settings.anthropic_api_key,
    temperature=0.2,
)


def grade(req: QuizGradeRequest) -> QuizGradeResponse:
    # 객관식은 LLM 없이 즉시 채점
    if req.quizType == "MULTIPLE_CHOICE":
        is_correct = _normalize(req.userAnswer) == _normalize(req.correctAnswer)
        return QuizGradeResponse(
            isCorrect=is_correct,
            score=100 if is_correct else 0,
            feedback="정답입니다!" if is_correct else f"틀렸습니다. 정답은 {req.correctAnswer}입니다.",
            improvement=None if is_correct else "해설을 다시 한 번 확인해보세요.",
        )

    # 서술형/주관형: LLM 채점
    prompt = GRADING_PROMPT.format(
        question=req.question,
        correct_answer=req.correctAnswer,
        user_answer=req.userAnswer,
        quiz_type=req.quizType,
    )
    response = llm.invoke(prompt)
    parsed = _parse_json(response.content)

    return QuizGradeResponse(
        isCorrect=parsed.get("isCorrect", False),
        score=int(parsed.get("score", 0)),
        feedback=parsed.get("feedback", ""),
        improvement=parsed.get("improvement"),
    )


def _normalize(s: str) -> str:
    return s.strip().upper().replace(".", "").replace(" ", "")


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}
