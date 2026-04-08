from fastapi import APIRouter

from app.models.schemas import SelfExplainRequest, SelfExplainResponse
from app.services import self_explain_service

router = APIRouter(prefix="/ai/self-explain", tags=["SelfExplain"])


@router.post("", response_model=SelfExplainResponse)
async def evaluate(req: SelfExplainRequest) -> SelfExplainResponse:
    """학생의 자기 설명을 평가하여 강점/약점/오개념을 진단"""
    return self_explain_service.evaluate(req)
