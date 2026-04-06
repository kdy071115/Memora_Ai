import logging
from typing import List
from langchain_openai import ChatOpenAI

from app.config import settings
from app.prompts.qa import QA_PROMPT
from app.services.embedding_service import embedding_service
from app.models.schemas import QaAskRequest, QaAskResponse, SourceRef

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model=settings.llm_model,
    api_key=settings.openai_api_key,
    temperature=0.5,
)


def ask(req: QaAskRequest) -> QaAskResponse:
    # 1. 벡터 검색
    results = embedding_service.search(req.lectureId, req.question, top_k=5)

    if not results:
        return QaAskResponse(
            answer="제공된 자료에는 해당 내용이 없습니다. 다른 질문을 시도해보세요.",
            sources=[],
        )

    # 2. 컨텍스트 구성
    context_parts = []
    for i, r in enumerate(results, 1):
        context_parts.append(
            f"[{i}] (페이지 {r.get('page_number', '?')})\n{r['content']}"
        )
    retrieved_chunks = "\n\n".join(context_parts)

    # 3. 이전 대화 구성
    history_text = "\n".join(
        f"{m.role}: {m.content}" for m in req.history[-6:]
    ) if req.history else "(없음)"

    # 4. LLM 호출
    prompt = QA_PROMPT.format(
        retrieved_chunks=retrieved_chunks,
        chat_history=history_text,
        question=req.question,
        difficulty=req.difficulty,
    )
    response = llm.invoke(prompt)
    answer = response.content

    # 5. 출처 변환
    sources: List[SourceRef] = [
        SourceRef(
            documentId=r.get("document_id"),
            documentName=r.get("document_name"),
            pageNumber=r.get("page_number"),
            preview=r["content"][:200],
        )
        for r in results
    ]

    return QaAskResponse(answer=answer, sources=sources)
