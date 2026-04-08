from fastapi import APIRouter

from app.models.schemas import AssignmentFeedbackRequest, AssignmentFeedbackResponse
from app.services import assignment_feedback_service

router = APIRouter(prefix="/ai/assignment-feedback", tags=["AssignmentFeedback"])


@router.post("", response_model=AssignmentFeedbackResponse)
async def evaluate(req: AssignmentFeedbackRequest) -> AssignmentFeedbackResponse:
    """강사용 — 학생 제출물(글 + 첨부)을 과제 주제와 비교해 피드백 초안을 생성."""
    return assignment_feedback_service.evaluate(req)
