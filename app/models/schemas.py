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


# ====== Self-Explanation Coaching ======
class SelfExplainRequest(BaseModel):
    lectureId: int
    explanation: str
    focusTopic: Optional[str] = None  # 학생이 특정 주제에 한해 설명할 때 (옵션)


class SelfExplainResponse(BaseModel):
    overallScore: int  # 0-100
    grade: Literal["EXCELLENT", "GOOD", "NEEDS_WORK"]
    strengths: List[str] = Field(default_factory=list)
    missingConcepts: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    feedback: str
    suggestedNextSteps: List[str] = Field(default_factory=list)


# ====== Assignment Feedback ======
class AssignmentFeedbackRequest(BaseModel):
    """강사가 학생 제출물에 대해 AI 피드백 초안을 요청.

    `attachmentBase64` 가 있으면 백엔드가 디스크에서 읽어 base64 로 인코딩해 보낸 것.
    파일 이름의 확장자에 따라 PDF 추출 또는 plain text 디코딩으로 처리한다.
    """

    assignmentTitle: str
    assignmentDescription: str
    studentName: Optional[str] = None
    submissionContent: str = ""
    attachmentName: Optional[str] = None
    attachmentBase64: Optional[str] = None


class AssignmentFeedbackResponse(BaseModel):
    overallScore: int  # 0-100
    grade: Literal["EXCELLENT", "GOOD", "AVERAGE", "NEEDS_WORK"]
    summary: str  # 1-2 줄 종합 평가
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    missingPoints: List[str] = Field(default_factory=list)  # 과제 주제에 비추어 빠뜨린 것
    suggestions: List[str] = Field(default_factory=list)  # 다음 단계 제안
    instructorDraft: str  # 강사가 댓글창에 그대로 붙여넣을 수 있는 자연어 피드백 초안
