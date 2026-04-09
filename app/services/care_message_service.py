import json
import logging
import re
from langchain_anthropic import ChatAnthropic

from app.config import settings
from app.prompts.care_message import CARE_MESSAGE_PROMPT
from app.models.schemas import CareMessageRequest, CareMessageResponse

logger = logging.getLogger(__name__)

llm = ChatAnthropic(
    model=settings.llm_model,
    api_key=settings.anthropic_api_key,
    temperature=0.6,
    max_tokens=1024,
)


def generate(req: CareMessageRequest) -> CareMessageResponse:
    logger.info("케어 메시지 생성 student=%s reasons=%d", req.studentName, len(req.riskReasons))

    prompt = CARE_MESSAGE_PROMPT.format(
        student_name=req.studentName,
        course_title=req.courseTitle or "(강의명 없음)",
        instructor_name=req.instructorName or "강사",
        risk_reasons="\n".join(f"- {r}" for r in req.riskReasons) or "(특이사항 없음)",
        weak_concepts=", ".join(req.weakConcepts) or "(없음)",
        days_since_last_active=str(req.daysSinceLastActive) if req.daysSinceLastActive is not None else "기록 없음",
        average_score=str(req.averageScore) if req.averageScore is not None else "기록 없음",
    )

    try:
        response = llm.invoke(prompt)
    except Exception as e:
        logger.error("케어 메시지 LLM 호출 실패: %s", e)
        return _fallback(req.studentName)

    parsed = _parse_json(response.content)
    if parsed is None:
        return _fallback(req.studentName)

    return CareMessageResponse(
        message=str(parsed.get("message", "")),
        suggestedActions=list(parsed.get("suggestedActions", [])),
    )


def _fallback(student_name: str) -> CareMessageResponse:
    return CareMessageResponse(
        message=f"{student_name}님, 최근 학습이 좀 뜸하신 것 같아 걱정되어 연락드려요. 어려운 부분이 있으시면 언제든 편하게 말씀해주세요. 같이 천천히 풀어가요!",
        suggestedActions=["1:1 면담 제안", "맞춤 학습 자료 공유"],
    )


def _parse_json(text):
    if text is None:
        return None
    cleaned = re.sub(r"^```(?:json)?\s*", "", str(text).strip())
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
