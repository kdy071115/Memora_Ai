from fastapi import APIRouter

from app.models.schemas import DailyMissionRequest, DailyMissionResponse
from app.services import daily_missions_service

router = APIRouter(prefix="/ai/daily-missions", tags=["DailyMissions"])


@router.post("", response_model=DailyMissionResponse)
async def generate(req: DailyMissionRequest) -> DailyMissionResponse:
    """학생 개인화 데일리 학습 미션 생성."""
    return daily_missions_service.generate(req)
