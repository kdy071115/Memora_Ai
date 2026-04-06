from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.routers import health, document, qa, quiz, analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Memora AI Server",
    description="Memora 학습 코파일럿 AI 서버",
    version="1.0.0",
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


@app.get("/")
async def root():
    return {"message": "Memora AI Server is running"}
