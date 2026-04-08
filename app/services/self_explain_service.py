import json
import logging
import re
from langchain_anthropic import ChatAnthropic

from app.config import settings
from app.prompts.self_explain import SELF_EXPLAIN_PROMPT
from app.services.embedding_service import embedding_service
from app.models.schemas import SelfExplainRequest, SelfExplainResponse

logger = logging.getLogger(__name__)

llm = ChatAnthropic(
    model=settings.llm_model,
    api_key=settings.anthropic_api_key,
    temperature=0.3,
    max_tokens=2048,
)


def evaluate(req: SelfExplainRequest) -> SelfExplainResponse:
    logger.info(
        f"자기 설명 평가 시작 lectureId={req.lectureId} explanation_len={len(req.explanation)}"
    )

    # 학생 설명을 쿼리로 사용해 가장 관련 있는 청크를 검색
    # focusTopic 이 있으면 그걸 우선 검색에 사용
    query = req.focusTopic or req.explanation[:500] or "핵심 개념"
    results = embedding_service.search(req.lectureId, query, top_k=8)

    if not results:
        logger.warning(f"자기 설명 평가 — 임베딩 인덱스 비어있음 lectureId={req.lectureId}")
        return SelfExplainResponse(
            overallScore=0,
            grade="NEEDS_WORK",
            strengths=[],
            missingConcepts=[],
            misconceptions=[],
            feedback="강의 자료가 아직 분석되지 않았어요. 자료가 처리되면 다시 시도해주세요.",
            suggestedNextSteps=["자료 처리가 완료될 때까지 기다린 뒤 다시 시도하세요."],
        )

    lecture_content = "\n\n".join(r["content"] for r in results)[:8000]

    focus_section = ""
    if req.focusTopic:
        focus_section = f"\n[학생이 집중한 주제]\n{req.focusTopic}\n"

    prompt = SELF_EXPLAIN_PROMPT.format(
        lecture_content=lecture_content,
        student_explanation=req.explanation,
        focus_topic_section=focus_section,
    )

    try:
        response = llm.invoke(prompt)
    except Exception as e:
        logger.error(f"자기 설명 평가 LLM 호출 실패: {e}")
        return _fallback_response("AI 코치 호출 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.")

    raw = response.content
    parsed = _parse_json(raw)
    if parsed is None:
        logger.warning(f"자기 설명 평가 JSON 파싱 실패. raw 앞부분: {raw[:300]}")
        return _fallback_response("AI 응답 형식을 해석하지 못했어요. 다시 한 번 시도해주세요.")

    try:
        return SelfExplainResponse(
            overallScore=int(parsed.get("overallScore", 0)),
            grade=parsed.get("grade", "NEEDS_WORK"),
            strengths=list(parsed.get("strengths", [])),
            missingConcepts=list(parsed.get("missingConcepts", [])),
            misconceptions=list(parsed.get("misconceptions", [])),
            feedback=str(parsed.get("feedback", "")),
            suggestedNextSteps=list(parsed.get("suggestedNextSteps", [])),
        )
    except Exception as e:
        logger.error(f"자기 설명 평가 응답 매핑 실패: {e}")
        return _fallback_response("AI 응답을 정리하는 중 문제가 생겼어요.")


def _fallback_response(message: str) -> SelfExplainResponse:
    return SelfExplainResponse(
        overallScore=0,
        grade="NEEDS_WORK",
        strengths=[],
        missingConcepts=[],
        misconceptions=[],
        feedback=message,
        suggestedNextSteps=[],
    )


def _parse_json(text: str):
    """LLM 응답에서 JSON 객체 추출"""
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None
