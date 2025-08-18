from pydantic import BaseModel
from typing import Optional, List

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

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
    mouth_feedback: str
    tongue_position_feedback: str
    breathing_feedback: str

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
