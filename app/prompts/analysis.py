ANALYSIS_PROMPT = """당신은 학습 데이터 분석 전문가입니다.
아래 학생의 학습 데이터를 분석하여 맞춤형 학습 조언을 생성하세요.

[학습 데이터]
- 퀴즈 정답률: {correct_rate}
- 취약 개념: {weak_concepts}
- 질문 패턴: {question_patterns}
- 학습 시간 추이: {study_time_trend}

다음 JSON 형식으로만 응답하세요:
{{
  "diagnosis": "현재 학습 상태 진단 (강점과 약점)",
  "weakConceptAnalysis": "취약 개념 분석 (왜 어려워하는지 추정)",
  "recommendations": ["맞춤형 학습 추천 1", "추천 2", "추천 3"],
  "motivation": "동기 부여 메시지"
}}
"""
