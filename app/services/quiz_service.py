import json
import logging
import re
from typing import List
from langchain_openai import ChatOpenAI

from app.config import settings
from app.prompts.quiz import QUIZ_PROMPT
from app.services.embedding_service import embedding_service
from app.models.schemas import QuizGenerateRequest, QuizGenerateResponse, GeneratedQuiz

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model=settings.llm_model,
    api_key=settings.openai_api_key,
    temperature=0.7,
)


def generate(req: QuizGenerateRequest) -> QuizGenerateResponse:
    # 강의 컨텍스트 수집: 임의의 chunk 검색 (concept_tags 또는 일반)
    query = " ".join(req.conceptTags) if req.conceptTags else "핵심 개념 요약"
    results = embedding_service.search(req.lectureId, query, top_k=8)

    if not results:
        return QuizGenerateResponse(quizzes=[])

    lecture_content = "\n\n".join(r["content"] for r in results)[:8000]

    prompt = QUIZ_PROMPT.format(
        lecture_content=lecture_content,
        count=req.count,
        quiz_types=", ".join(req.types),
        difficulty=req.difficulty,
        concept_tags=", ".join(req.conceptTags) if req.conceptTags else "전체",
    )

    response = llm.invoke(prompt)
    raw = response.content

    # JSON 추출
    quizzes_data = _parse_json_array(raw)

    quizzes = []
    for q in quizzes_data[: req.count]:
        try:
            quizzes.append(GeneratedQuiz(
                question=q.get("question", ""),
                quizType=q.get("quizType", "MULTIPLE_CHOICE"),
                options=q.get("options"),
                correctAnswer=str(q.get("correctAnswer", "")),
                explanation=q.get("explanation", ""),
                conceptTag=q.get("conceptTag"),
                difficulty=q.get("difficulty", req.difficulty),
            ))
        except Exception as e:
            logger.warning(f"퀴즈 파싱 실패: {e}")

    return QuizGenerateResponse(quizzes=quizzes)


def _parse_json_array(text: str) -> List[dict]:
    """LLM 응답에서 JSON 배열 추출"""
    # 코드 블록 제거
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 배열 부분만 추출 시도
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return []
