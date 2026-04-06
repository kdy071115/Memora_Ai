from fastapi import APIRouter

from app.models.schemas import (
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizGradeRequest,
    QuizGradeResponse,
)
from app.services import quiz_service, grading_service

router = APIRouter(prefix="/ai/quiz", tags=["Quiz"])


@router.post("/generate", response_model=QuizGenerateResponse)
async def generate(req: QuizGenerateRequest) -> QuizGenerateResponse:
    """강의 자료 기반 퀴즈 생성"""
    return quiz_service.generate(req)


@router.post("/grade", response_model=QuizGradeResponse)
async def grade(req: QuizGradeRequest) -> QuizGradeResponse:
    """퀴즈 자동 채점"""
    return grading_service.grade(req)
