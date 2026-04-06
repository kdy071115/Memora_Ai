import logging
import os
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

# AWS 자격증명이 모두 채워져 있을 때만 S3 클라이언트 생성
_use_s3 = bool(settings.aws_access_key_id and settings.aws_secret_access_key)
s3_client = (
    boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )
    if _use_s3
    else None
)
logger.info("[Storage] mode=%s", "S3" if _use_s3 else "LOCAL")

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
    """
    storedPath 가 절대 경로(`/...`) 또는 윈도우 드라이브(`C:\\...`) 면 디스크에서 직접 읽고,
    아니면 S3 키로 간주해 다운로드합니다.
    """
    if _is_local_path(stored_path):
        if not os.path.exists(stored_path):
            raise FileNotFoundError(f"로컬 파일을 찾을 수 없습니다: {stored_path}")
        with open(stored_path, "rb") as f:
            return f.read()

    if s3_client is None:
        raise RuntimeError(
            "AWS 자격증명이 없어 S3 다운로드가 불가합니다. "
            "백엔드가 로컬 저장 모드인지 확인하세요."
        )
    response = s3_client.get_object(Bucket=settings.aws_s3_bucket, Key=stored_path)
    return response["Body"].read()


def _is_local_path(path: str) -> bool:
    if not path:
        return False
    return path.startswith("/") or (len(path) > 2 and path[1] == ":")


def _generate_summary(text: str) -> str:
    prompt = SUMMARY_PROMPT.format(document_text=text)
    response = llm.invoke(prompt)
    return response.content


async def _send_callback(callback_path: str, payload: DocumentCallbackPayload):
    url = f"{settings.callback_base_url}{callback_path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.post(url, json=payload.model_dump())
