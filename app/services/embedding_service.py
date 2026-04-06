import os
import logging
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document as LcDocument

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """lecture_id 단위로 FAISS 인덱스를 분리 관리"""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        self.stores: dict[str, FAISS] = {}
        os.makedirs(settings.vector_store_path, exist_ok=True)

    def _index_path(self, lecture_id: int) -> str:
        return os.path.join(settings.vector_store_path, f"lecture_{lecture_id}")

    def add_documents(self, lecture_id: int, chunks: List[dict]) -> List[str]:
        """
        chunks: [{chunk_index, content, page_number, document_id, document_name}]
        Returns embedding ids (FAISS internal ids as strings).
        """
        docs = [
            LcDocument(
                page_content=c["content"],
                metadata={
                    "chunk_index": c["chunk_index"],
                    "page_number": c.get("page_number"),
                    "document_id": c.get("document_id"),
                    "document_name": c.get("document_name"),
                },
            )
            for c in chunks
        ]

        key = str(lecture_id)
        if key in self.stores:
            ids = self.stores[key].add_documents(docs)
        else:
            store = FAISS.from_documents(docs, self.embeddings)
            self.stores[key] = store
            ids = list(store.docstore._dict.keys())

        self.save_index(lecture_id)
        return [str(i) for i in ids]

    def search(self, lecture_id: int, query: str, top_k: int = 5) -> List[dict]:
        store = self._get_or_load(lecture_id)
        if store is None:
            return []

        results = store.similarity_search_with_score(query, k=top_k)
        output = []
        for doc, score in results:
            output.append({
                "content": doc.page_content,
                "score": float(score),
                "chunk_index": doc.metadata.get("chunk_index"),
                "page_number": doc.metadata.get("page_number"),
                "document_id": doc.metadata.get("document_id"),
                "document_name": doc.metadata.get("document_name"),
            })
        return output

    def save_index(self, lecture_id: int):
        key = str(lecture_id)
        if key in self.stores:
            try:
                self.stores[key].save_local(self._index_path(lecture_id))
            except Exception as e:
                logger.error(f"FAISS 저장 실패 lecture_id={lecture_id}: {e}")

    def _get_or_load(self, lecture_id: int) -> Optional[FAISS]:
        key = str(lecture_id)
        if key in self.stores:
            return self.stores[key]

        path = self._index_path(lecture_id)
        if os.path.exists(path):
            try:
                self.stores[key] = FAISS.load_local(
                    path, self.embeddings, allow_dangerous_deserialization=True
                )
                return self.stores[key]
            except Exception as e:
                logger.error(f"FAISS 로드 실패 lecture_id={lecture_id}: {e}")
        return None


# Singleton
embedding_service = EmbeddingService()
