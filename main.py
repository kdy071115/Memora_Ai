from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.routers import health, document, qa, quiz, analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ======================================================================
# OpenAPI / Swagger 설정
# ======================================================================
API_DESCRIPTION = """
## Memora AI Server

LangChain + FAISS 기반 RAG 파이프라인을 제공하는 FastAPI AI 서버.

Spring Boot 백엔드(`Memora_Server`)에서 호출되며, 단독 실행도 가능합니다.

### 주요 기능
- **Document**: PDF/문서 임베딩 → 강의별 FAISS 인덱스 구축
- **QA**: RAG 기반 질의응답 (대화 히스토리 + 출처 청크 반환)
- **Quiz**: 강의 내용 기반 자동 퀴즈 생성 / 채점
- **Analysis**: 학습 데이터 기반 진단 및 추천

### 인증
현재 내부 서비스 간 통신용으로 인증이 없습니다. 운영 환경에서는 reverse proxy 또는
별도 토큰을 적용하세요.

### 문서 엔드포인트
- Swagger UI : `/docs`
- ReDoc      : `/redoc`
- OpenAPI JSON: `/openapi.json`
"""

OPENAPI_TAGS = [
    {"name": "Health", "description": "헬스 체크 엔드포인트"},
    {"name": "Document", "description": "문서 임베딩 / 인덱스 관리"},
    {"name": "QA", "description": "RAG 기반 질의응답"},
    {"name": "Quiz", "description": "퀴즈 생성 및 채점"},
    {"name": "Analysis", "description": "학습 데이터 진단 및 추천"},
]


app = FastAPI(
    title="Memora AI Server",
    description=API_DESCRIPTION,
    version="1.0.0",
    contact={
        "name": "Memora Team",
        "url": "https://github.com/kdy071115/Memora_Server",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=OPENAPI_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "displayRequestDuration": True,
        "docExpansion": "none",
        "filter": True,
        "tagsSorter": "alpha",
        "operationsSorter": "alpha",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(document.router)
app.include_router(qa.router)
app.include_router(quiz.router)
app.include_router(analysis.router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Memora AI Server is running",
        "docs": "/docs",
        "redoc": "/redoc",
    }
