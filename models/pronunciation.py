# models/pronunciation.py
# API 응답을 위한 Pydantic 데이터 모델입니다.

from pydantic import BaseModel
from typing import List

class IncorrectPoint(BaseModel):
    expected: str
    actual: str
    img: str
    diff_detail: str
    mouth_shape: str
    tongue_shape: str
    breathing: str

class PronunciationAnalysisResponse(BaseModel):
    score: str
    transcription: str
    incorrect_points: List[IncorrectPoint]