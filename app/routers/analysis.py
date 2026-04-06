from fastapi import APIRouter

from app.models.schemas import AnalysisRequest, AnalysisResponse
from app.services import analysis_service

router = APIRouter(prefix="/ai/analysis", tags=["Analysis"])


@router.post("/learning", response_model=AnalysisResponse)
async def analyze_learning(req: AnalysisRequest) -> AnalysisResponse:
    """학습 데이터 기반 진단/추천"""
    return analysis_service.analyze(req)
