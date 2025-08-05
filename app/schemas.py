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
        orm_mode = True

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
        orm_mode = True
