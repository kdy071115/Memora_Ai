from fastapi import APIRouter

from app.models.schemas import CareMessageRequest, CareMessageResponse
from app.services import care_message_service

router = APIRouter(prefix="/ai/care-message", tags=["CareMessage"])


@router.post("", response_model=CareMessageResponse)
async def generate(req: CareMessageRequest) -> CareMessageResponse:
    """강사 → 위험 학생 케어 메시지 초안 생성."""
    return care_message_service.generate(req)
