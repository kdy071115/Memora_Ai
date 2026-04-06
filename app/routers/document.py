from fastapi import APIRouter, BackgroundTasks, status

from app.models.schemas import DocumentProcessRequest
from app.services import document_service

router = APIRouter(prefix="/ai/documents", tags=["Document"])


@router.post("/process", status_code=status.HTTP_202_ACCEPTED)
async def process_document(req: DocumentProcessRequest, background_tasks: BackgroundTasks):
    """문서 처리 요청 (비동기). 처리 결과는 callbackUrl로 전송됨."""
    background_tasks.add_task(document_service.process_document, req)
    return {"status": "ACCEPTED", "documentId": req.documentId}
