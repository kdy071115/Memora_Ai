from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ====== Document ======
class DocumentProcessRequest(BaseModel):
    documentId: int
    lectureId: int
    storedPath: str
    callbackUrl: str


class ChunkData(BaseModel):
    chunkIndex: int
    content: str
    pageNumber: Optional[int] = None
    tokenCount: Optional[int] = None
    embeddingId: Optional[str] = None


class DocumentCallbackPayload(BaseModel):
    documentId: int
    status: Literal["COMPLETED", "FAILED"]
    summary: Optional[str] = None
    chunks: List[ChunkData] = Field(default_factory=list)


# ====== QA ======
class QaSourceMessage(BaseModel):
    role: Literal["USER", "ASSISTANT"]
    content: str


class QaAskRequest(BaseModel):
    lectureId: int
    question: str
    difficulty: Literal["EASY", "MEDIUM", "HARD"] = "MEDIUM"
    history: List[QaSourceMessage] = Field(default_factory=list)


class SourceRef(BaseModel):
    documentId: Optional[int] = None
    documentName: Optional[str] = None
    pageNumber: Optional[int] = None
    preview: str


class QaAskResponse(BaseModel):
    answer: str
    sources: List[SourceRef]


# ====== Quiz ======
class QuizGenerateRequest(BaseModel):
    lectureId: int
    count: int = 5
    types: List[str] = Field(default_factory=lambda: ["MULTIPLE_CHOICE"])
    difficulty: Literal["EASY", "MEDIUM", "HARD"] = "MEDIUM"
    conceptTags: List[str] = Field(default_factory=list)


class GeneratedQuiz(BaseModel):
    question: str
    quizType: str
    options: Optional[List[str]] = None
    correctAnswer: str
    explanation: str
    conceptTag: Optional[str] = None
    difficulty: str


class QuizGenerateResponse(BaseModel):
    quizzes: List[GeneratedQuiz]


class QuizGradeRequest(BaseModel):
    question: str
    quizType: str
    correctAnswer: str
    userAnswer: str


class QuizGradeResponse(BaseModel):
    isCorrect: bool
    score: int
    feedback: str
    improvement: Optional[str] = None


# ====== Analysis ======
class AnalysisRequest(BaseModel):
    correctRate: float
    weakConcepts: List[str] = Field(default_factory=list)
    questionPatterns: List[str] = Field(default_factory=list)
    studyTimeTrend: Optional[str] = None


class AnalysisResponse(BaseModel):
    diagnosis: str
    weakConceptAnalysis: str
    recommendations: List[str]
    motivation: str
    # 프론트엔드 레이더 차트용 (고정 6개 역량, 0~150 스케일)
    competencies: dict[str, int] = Field(default_factory=dict)
    # 최대 성장 지표 문구 (예: "개념 이해력이 지난주 대비 30% 상승")
    maxGrowthIndicator: str = ""
