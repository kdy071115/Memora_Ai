import json
import logging
import re
from langchain_anthropic import ChatAnthropic

from app.config import settings
from app.prompts.analysis import ANALYSIS_PROMPT
from app.models.schemas import AnalysisRequest, AnalysisResponse

logger = logging.getLogger(__name__)

# 프론트엔드 레이더 차트가 기대하는 고정 6개 역량 (순서 유지)
COMPETENCY_KEYS = [
    "개념 이해력",
    "수학적 사고",
    "비판적 추론",
    "암기력",
    "응용력",
    "문제 해결",
]

llm = ChatAnthropic(
    model=settings.llm_model,
    api_key=settings.anthropic_api_key,
    temperature=0.5,
)


def analyze(req: AnalysisRequest) -> AnalysisResponse:
    prompt = ANALYSIS_PROMPT.format(
        correct_rate=f"{req.correctRate * 100:.1f}%",
        weak_concepts=", ".join(req.weakConcepts) if req.weakConcepts else "(없음)",
        question_patterns=", ".join(req.questionPatterns) if req.questionPatterns else "(없음)",
        study_time_trend=req.studyTimeTrend or "(데이터 부족)",
    )
    response = llm.invoke(prompt)
    parsed = _parse_json(response.content)

    return AnalysisResponse(
        diagnosis=parsed.get("diagnosis", ""),
        weakConceptAnalysis=parsed.get("weakConceptAnalysis", ""),
        recommendations=parsed.get("recommendations", []),
        motivation=parsed.get("motivation", ""),
        competencies=_sanitize_competencies(parsed.get("competencies"), req.correctRate),
        maxGrowthIndicator=parsed.get("maxGrowthIndicator", "") or "꾸준한 학습이 누적되고 있습니다",
    )


def _sanitize_competencies(raw, correct_rate: float) -> dict[str, int]:
    """
    LLM 결과를 검증해 고정 6개 키 / 0~150 정수 딕셔너리로 정규화.
    키가 누락되었거나 파싱 실패 시 정답률 기반 기본값으로 채움.
    """
    # 정답률(0~1) → 40~140 기본값 (평균 100 근처)
    default_score = max(40, min(140, int(40 + correct_rate * 100)))

    if not isinstance(raw, dict):
        return {k: default_score for k in COMPETENCY_KEYS}

    result: dict[str, int] = {}
    for key in COMPETENCY_KEYS:
        value = raw.get(key)
        if isinstance(value, (int, float)):
            result[key] = max(0, min(150, int(value)))
        else:
            result[key] = default_score
    return result


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
