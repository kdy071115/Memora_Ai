import json
import logging
import re
from langchain_openai import ChatOpenAI

from app.config import settings
from app.prompts.analysis import ANALYSIS_PROMPT
from app.models.schemas import AnalysisRequest, AnalysisResponse

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model=settings.llm_model,
    api_key=settings.openai_api_key,
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
    )


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
