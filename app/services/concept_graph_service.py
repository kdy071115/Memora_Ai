import json
import logging
import re
from langchain_anthropic import ChatAnthropic

from app.config import settings
from app.prompts.concept_graph import CONCEPT_GRAPH_PROMPT
from app.models.schemas import ConceptGraphRequest, ConceptGraphResponse, ConceptNode, ConceptEdge
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

llm = ChatAnthropic(
    model=settings.llm_model,
    api_key=settings.anthropic_api_key,
    temperature=0.3,
    max_tokens=2048,
)


def generate(req: ConceptGraphRequest) -> ConceptGraphResponse:
    logger.info("개념 그래프 생성 lectureId=%d", req.lectureId)

    # 강의 전체 자료에서 가장 중요한 청크를 넉넉히 가져온다
    results = embedding_service.search(req.lectureId, "핵심 개념 전체", top_k=15)
    if not results:
        return ConceptGraphResponse(nodes=[], edges=[])

    content = "\n\n".join(r["content"] for r in results)[:12000]

    prompt = CONCEPT_GRAPH_PROMPT.format(lecture_content=content)

    try:
        response = llm.invoke(prompt)
    except Exception as e:
        logger.error("개념 그래프 LLM 호출 실패: %s", e)
        return ConceptGraphResponse(nodes=[], edges=[])

    parsed = _parse_json(response.content)
    if parsed is None:
        logger.warning("개념 그래프 JSON 파싱 실패")
        return ConceptGraphResponse(nodes=[], edges=[])

    try:
        nodes = [
            ConceptNode(
                id=str(n.get("id", "")),
                label=str(n.get("label", "")),
                importance=int(n.get("importance", 50)),
            )
            for n in parsed.get("nodes", [])
        ]
        node_ids = {n.id for n in nodes}
        edges = [
            ConceptEdge(
                source=str(e.get("source", "")),
                target=str(e.get("target", "")),
                label=str(e.get("label", "관련")),
            )
            for e in parsed.get("edges", [])
            if str(e.get("source", "")) in node_ids and str(e.get("target", "")) in node_ids
        ]
        return ConceptGraphResponse(nodes=nodes, edges=edges)
    except Exception as e:
        logger.error("개념 그래프 응답 매핑 실패: %s", e)
        return ConceptGraphResponse(nodes=[], edges=[])


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
