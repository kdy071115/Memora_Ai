from fastapi import APIRouter

from app.models.schemas import QaAskRequest, QaAskResponse
from app.services import qa_service

router = APIRouter(prefix="/ai/qa", tags=["QA"])


@router.post("/ask", response_model=QaAskResponse)
async def ask(req: QaAskRequest) -> QaAskResponse:
    """RAG 기반 질의응답"""
    return qa_service.ask(req)
