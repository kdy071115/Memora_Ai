import json
import logging
import re
from langchain_anthropic import ChatAnthropic

from app.config import settings
from app.prompts.daily_missions import DAILY_MISSIONS_PROMPT
from app.models.schemas import DailyMissionRequest, DailyMissionResponse, DailyMissionItem

logger = logging.getLogger(__name__)

llm = ChatAnthropic(
    model=settings.llm_model,
    api_key=settings.anthropic_api_key,
    temperature=0.7,
    max_tokens=1536,
)


def generate(req: DailyMissionRequest) -> DailyMissionResponse:
    logger.info("데일리 미션 생성 student=%s weak=%d", req.studentName, len(req.weakConcepts))

    prompt = DAILY_MISSIONS_PROMPT.format(
        student_name=req.studentName,
        weak_concepts=", ".join(req.weakConcepts) or "(없음)",
        pending_assignments="\n".join(f"- {a}" for a in req.pendingAssignments) or "(없음)",
        upcoming_lectures="\n".join(f"- {t}" for t in req.upcomingLectureTitles) or "(없음)",
        average_score=str(req.averageScore) if req.averageScore is not None else "기록 없음",
        last_self_explain_score=str(req.lastSelfExplainScore) if req.lastSelfExplainScore is not None else "기록 없음",
        days_since_last_study=str(req.daysSinceLastStudy) if req.daysSinceLastStudy is not None else "오늘 학습함",
    )

    try:
        response = llm.invoke(prompt)
    except Exception as e:
        logger.error("데일리 미션 LLM 호출 실패: %s", e)
        return _fallback(req.studentName)

    parsed = _parse_json(response.content)
    if parsed is None:
        return _fallback(req.studentName)

    try:
        items = [
            DailyMissionItem(
                type=str(m.get("type", "REVIEW")),
                title=str(m.get("title", "")),
                description=str(m.get("description", "")),
                estimatedMinutes=int(m.get("estimatedMinutes", 10)),
                why=str(m.get("why", "")),
            )
            for m in parsed.get("missions", [])
        ]
        return DailyMissionResponse(
            summary=str(parsed.get("summary", "")),
            missions=items,
            motivation=str(parsed.get("motivation", "")),
        )
    except Exception as e:
        logger.error("데일리 미션 파싱 실패: %s", e)
        return _fallback(req.studentName)


def _fallback(student_name: str) -> DailyMissionResponse:
    return DailyMissionResponse(
        summary="오늘은 어제 배운 내용을 한 번 더 정리해보세요",
        missions=[
            DailyMissionItem(
                type="REVIEW",
                title="어제 학습 내용 5분 회고",
                description="가장 최근 차시 자료를 한 번 훑어보고, 가장 인상 깊었던 부분 한 가지를 떠올려보세요.",
                estimatedMinutes=5,
                why="짧은 회고가 장기 기억에 가장 효과적이에요",
            )
        ],
        motivation="작은 한 걸음이 큰 차이를 만들어요!",
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
