<<<<<<< HEAD
from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Literal
from datetime import datetime

# =========================
# 공용 타입
# =========================
FeedbackType = Literal["basic", "real_life"]

# =========================
# 사용자 스키마
# =========================
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

# =========================
# 사용자 로그인 스키마
# =========================
=======
from pydantic import BaseModel
from typing import Optional, List

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

>>>>>>> origin/develop
class UserLogin(BaseModel):
    username: str
    password: str

<<<<<<< HEAD
# =========================
# 사용자 삭제 스키마
# =========================
class UserDelete(BaseModel):
    email: EmailStr
    password: str

# =========================
# 사용자 응답 스키마
# =========================
class UserOut(BaseModel):
    # Pydantic v2: ORM 객체를 바로 검증 가능
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: EmailStr
    # 리스트(JSON)로 변경
    max_level: List[int] = Field(default_factory=list)



# =========================
# 단일 1:1 상세 (PronunciationFeedback)
# =========================
class PronunciationIn(BaseModel):
    score: int
    pronounced_word: str
    problem_word: str

# =========================
# 단일 1:1 상세 응답 (PronunciationFeedback)
# =========================
class PronunciationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feedback_id: int
    score: int
    pronounced_word: str
    problem_word: str

# =========================
# (선택) 발음 분석 응답 포맷 (서비스 레이어 전용 DTO)
# =========================
class AnalysisPoint(BaseModel):
    wrong_text: str
    expected: str
    teaching_point: str
    correct_img_url: Optional[str] = None
    correct_video_url: Optional[str] = None
=======
class UserDelete(BaseModel):
    email: str
    password: str

# ----- 발음 분석 응답 상세 항목 스키마 -----
class PronunciationFeedback(BaseModel):
    wrong_text: str
    expected: str
    teaching_point: str
    # DB 조회 결과 이미지나 비디오가 없을 수도 있으므로 Optional로 변경하는 것이 안전합니다.
    correct_img_url: Optional[str] = None 
    correct_video_url: Optional[str] = None  
>>>>>>> origin/develop
    mouth_feedback: str
    tongue_position_feedback: str
    breathing_feedback: str

<<<<<<< HEAD
# =========================
# 발음 분석 응답 스키마
# =========================
class PronunciationAnalysisResponse(BaseModel):
    score: int
    my_text: str
    target_word: str
    incorrect_points: List[AnalysisPoint]

# =========================
# 단계 응답 스키마
# =========================
class ProgressOut(BaseModel):
    max_level: List[int] = Field(default_factory=lambda: [1])   # ✅ 항상 [1] 기본값

# =========================
# 학습 세션 생성 스키마
# =========================
class PracticeSessionCreate(BaseModel):
    mode: Literal["daily", "basic"]
    level: int = Field(0, ge=0, description="프론트는 단일 정수로 보냄. 서버가 [level]로 저장")
    total_words: int = Field(default=0, ge=0, description="총 단어 수 (기본값: 0, 음수 불가)")

class PracticeSessionCreateResponse(BaseModel):
    session_id: str  # UUID

# 수정 가능한 필드만 받는 스키마
class StudySessionUpdate(BaseModel):
    status: Optional[Literal["in_progress", "completed", "abandoned"]] = None
    # 필요하다면 다른 필드도 부분수정 허용 가능:
    # total_words: Optional[int] = Field(None, ge=0)
    # level: Optional[list[int]] = None

class StudySessionOut(BaseModel):
    session_id: str
    user_id: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    total_words: int
    level: list[int]
    isPassed: bool  # "true" / "false" 문자열로 저장
=======
# ----- 발음 분석 응답 전체 스키마 -----
class PronunciationAnalysisResponse(BaseModel):
    score: str
    my_text: str                      
    target_word: str
    incorrect_points: List[PronunciationFeedback]

#-- 데이터 베이스 관련 스키마 --
class FeedbackCreate(BaseModel):
    result_id: int
    wrong_text: str
    teaching_point: Optional[str] = None
    correct_img_url: Optional[str] = None
    mouth_feedback: Optional[str] = None
    tongue_position_feedback: Optional[str] = None
    breathing_feedback: Optional[str] = None

class FeedbackResponse(BaseModel):
    wrong_text: str
    teaching_point: Optional[str]
    correct_img_url: Optional[str]
    mouth_feedback: Optional[str]
    tongue_position_feedback: Optional[str]
    breathing_feedback: Optional[str]
    class Config:
        from_attributes = True #orm_mode = True

class ResultCreate(BaseModel):
    user_id: int
    levels_id: int
    score: int
    my_text: str
    target_word: str
    target_video_url: Optional[str] = None
    my_video_url: Optional[str] = None

class ResultResponse(BaseModel):
    id: int
    user_id: int
    levels_id: int
    score: int
    my_text: str
    target_word: str
    target_video_url: Optional[str]
    my_video_url: Optional[str]
    feedback: List[FeedbackResponse] = []
    class Config:
        from_attributes = True #orm_mode = True
>>>>>>> origin/develop
