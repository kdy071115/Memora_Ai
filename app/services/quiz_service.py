import json
import logging
import random
import re
from typing import List
from langchain_anthropic import ChatAnthropic

from app.config import settings
from app.prompts.quiz import QUIZ_PROMPT
from app.services.embedding_service import embedding_service
from app.models.schemas import QuizGenerateRequest, QuizGenerateResponse, GeneratedQuiz

logger = logging.getLogger(__name__)

llm = ChatAnthropic(
    model=settings.llm_model,
    api_key=settings.anthropic_api_key,
    temperature=0.7,
)


def generate(req: QuizGenerateRequest) -> QuizGenerateResponse:
    logger.info(
        f"퀴즈 생성 시작 lectureId={req.lectureId} count={req.count} "
        f"types={req.types} difficulty={req.difficulty}"
    )

    # 강의 컨텍스트 수집: 임의의 chunk 검색 (concept_tags 또는 일반)
    query = " ".join(req.conceptTags) if req.conceptTags else "핵심 개념 요약"
    results = embedding_service.search(req.lectureId, query, top_k=8)

    if not results:
        logger.warning(
            f"퀴즈 생성 실패 — 임베딩 인덱스가 비어있음 lectureId={req.lectureId}. "
            f"문서 처리(process_document)가 완료되었는지 확인하세요."
        )
        return QuizGenerateResponse(quizzes=[])

    logger.info(f"검색된 chunk {len(results)}개로 퀴즈 생성 시도")
    lecture_content = "\n\n".join(r["content"] for r in results)[:8000]

    prompt = QUIZ_PROMPT.format(
        lecture_content=lecture_content,
        count=req.count,
        quiz_types=", ".join(req.types),
        difficulty=req.difficulty,
        concept_tags=", ".join(req.conceptTags) if req.conceptTags else "전체",
    )

    try:
        response = llm.invoke(prompt)
    except Exception as e:
        logger.error(f"LLM 호출 실패: {e}")
        return QuizGenerateResponse(quizzes=[])

    raw = response.content

    # JSON 추출
    quizzes_data = _parse_json_array(raw)
    if not quizzes_data:
        logger.warning(
            f"LLM 응답에서 JSON 배열을 추출하지 못함. raw 응답 앞부분: {raw[:500]}"
        )
        return QuizGenerateResponse(quizzes=[])

    quizzes = []
    for q in quizzes_data[: req.count]:
        try:
            quiz_type = q.get("quizType", "MULTIPLE_CHOICE")
            options = q.get("options")
            correct_answer = str(q.get("correctAnswer", ""))

            # 객관식의 경우 LLM 이 정답을 항상 첫 번째에 배치하는 편향이 있어
            # 옵션 순서를 무작위로 섞습니다. 정답은 텍스트 매칭이라 셔플해도 안전.
            if quiz_type == "MULTIPLE_CHOICE" and options and len(options) > 1:
                options = list(options)
                random.shuffle(options)

            quizzes.append(GeneratedQuiz(
                question=q.get("question", ""),
                quizType=quiz_type,
                options=options,
                correctAnswer=correct_answer,
                explanation=q.get("explanation", ""),
                conceptTag=q.get("conceptTag"),
                difficulty=q.get("difficulty", req.difficulty),
            ))
        except Exception as e:
            logger.warning(f"퀴즈 파싱 실패: {e}")

    logger.info(f"퀴즈 생성 완료: {len(quizzes)}개")
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
