import logging
import httpx
import boto3
from typing import Optional

from langchain_openai import ChatOpenAI

from app.config import settings
from app.utils.pdf_parser import extract_text_from_pdf
from app.utils.text_splitter import split_pages
from app.prompts.summary import SUMMARY_PROMPT
from app.services.embedding_service import embedding_service
from app.models.schemas import DocumentProcessRequest, DocumentCallbackPayload, ChunkData

logger = logging.getLogger(__name__)

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.aws_access_key_id or None,
    aws_secret_access_key=settings.aws_secret_access_key or None,
    region_name=settings.aws_region,
)

llm = ChatOpenAI(
    model=settings.llm_model,
    api_key=settings.openai_api_key,
    temperature=0.3,
)


async def process_document(req: DocumentProcessRequest):
    """문서 처리: 다운로드 → 텍스트 추출 → 청킹 → 임베딩 → 요약 → 콜백"""
    try:
        logger.info(f"문서 처리 시작: documentId={req.documentId}")

        # 1. S3에서 파일 다운로드
        file_bytes = _download_file(req.storedPath)

        # 2. PDF 텍스트 추출
        pages = extract_text_from_pdf(file_bytes)
        if not pages:
            raise ValueError("PDF에서 텍스트를 추출할 수 없습니다.")

        # 3. 청킹
        chunks = split_pages(pages, chunk_size=800, chunk_overlap=100)
        logger.info(f"청크 생성: {len(chunks)}개")

        # 4. 임베딩 + FAISS 저장
        chunk_inputs = [
            {
                "chunk_index": c["chunk_index"],
                "content": c["content"],
                "page_number": c["page_number"],
                "document_id": req.documentId,
                "document_name": req.storedPath.split("/")[-1],
            }
            for c in chunks
        ]
        embedding_ids = embedding_service.add_documents(req.lectureId, chunk_inputs)

        # 5. 요약 생성 (앞부분 12000자 제한)
        full_text = "\n\n".join(c["content"] for c in chunks)[:12000]
        summary = _generate_summary(full_text)

        # 6. 콜백
        callback_chunks = [
            ChunkData(
                chunkIndex=c["chunk_index"],
                content=c["content"],
                pageNumber=c["page_number"],
                tokenCount=len(c["content"]) // 4,
                embeddingId=embedding_ids[i] if i < len(embedding_ids) else None,
            )
            for i, c in enumerate(chunks)
        ]
        payload = DocumentCallbackPayload(
            documentId=req.documentId,
            status="COMPLETED",
            summary=summary,
            chunks=callback_chunks,
        )
        await _send_callback(req.callbackUrl, payload)
        logger.info(f"문서 처리 완료: documentId={req.documentId}")
    except Exception as e:
        logger.error(f"문서 처리 실패: documentId={req.documentId}, error={e}")
        try:
            await _send_callback(
                req.callbackUrl,
                DocumentCallbackPayload(documentId=req.documentId, status="FAILED"),
            )
        except Exception as cb_err:
            logger.error(f"실패 콜백 전송 실패: {cb_err}")


def _download_file(stored_path: str) -> bytes:
    response = s3_client.get_object(Bucket=settings.aws_s3_bucket, Key=stored_path)
    return response["Body"].read()


def _generate_summary(text: str) -> str:
    prompt = SUMMARY_PROMPT.format(document_text=text)
    response = llm.invoke(prompt)
    return response.content


async def _send_callback(callback_path: str, payload: DocumentCallbackPayload):
    url = f"{settings.callback_base_url}{callback_path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.post(url, json=payload.model_dump())
