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
        is_correct = _mc_match(req.userAnswer, req.correctAnswer)
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


# 객관식 "A.", "B." 접두사 제거 — "A. 텍스트" → "텍스트"
_LABEL_PREFIX = re.compile(r"^[A-Da-d][.)]\s*")


def _strip_label(s: str) -> str:
    return _LABEL_PREFIX.sub("", s.strip())


def _mc_match(user_answer: str, correct_answer: str) -> bool:
    """
    객관식 정답 비교. 다음 케이스를 모두 처리:
      1. 둘 다 전체 텍스트 → 정규 비교
      2. correctAnswer 가 라벨만("A") → userAnswer 가 "A. ..." 로 시작하는지
      3. 한쪽에만 "A." 접두사가 붙은 경우 → 접두사를 떼고 비교
    """
    # 1) 정규 비교
    if _normalize(user_answer) == _normalize(correct_answer):
        return True
    # 2) correctAnswer 가 단일 라벨(A~D)인 경우
    ca = correct_answer.strip().upper()
    if len(ca) == 1 and ca in "ABCD":
        ua = user_answer.strip()
        if ua.upper().startswith(ca + ".") or ua.upper().startswith(ca + ")"):
            return True
    # 3) 접두사 제거 후 비교
    if _normalize(_strip_label(user_answer)) == _normalize(_strip_label(correct_answer)):
        return True
    return False


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
