from fastapi import APIRouter

from app.models.schemas import ConceptGraphRequest, ConceptGraphResponse
from app.services import concept_graph_service

router = APIRouter(prefix="/ai/concept-graph", tags=["ConceptGraph"])


@router.post("", response_model=ConceptGraphResponse)
async def generate(req: ConceptGraphRequest) -> ConceptGraphResponse:
    """강의 자료에서 핵심 개념 + 의존관계를 추출해 지식 그래프로 반환."""
    return concept_graph_service.generate(req)
