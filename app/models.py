from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(10), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    results = relationship("Result", back_populates="user", passive_deletes=True)

class Levels(Base):
    __tablename__ = "levels"
    id = Column(Integer, primary_key=True, index=True)
    levels = Column(String(5), unique=True, nullable=False)
    results = relationship("Result", back_populates="levels")

class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="cascade"), nullable=False)
    levels_id = Column(Integer, ForeignKey("levels.id"), nullable=False)
    score = Column(Integer, nullable=False)
    my_text = Column(String(50), nullable=False)
    target_word = Column(String(50), nullable=False)
    target_video_url = Column(String(255))
    my_video_url = Column(String(255))
    user = relationship("User", back_populates="results")
    levels = relationship("Levels", back_populates="results")
    feedback = relationship("DetailedFeedback", back_populates="result", cascade="all, delete-orphan")

class DetailedFeedback(Base):
    __tablename__ = "detailed_feedback"
    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(Integer, ForeignKey("results.id", ondelete="cascade"), nullable=False)
    wrong_text = Column(String(255))
    teaching_point = Column(String(255))
    correct_img_url = Column(String(255))
    mouth_feedback = Column(String(255))
    tongue_position_feedback = Column(String(255))
    breathing_feedback = Column(String(255))
    result = relationship("Result", back_populates="feedback", passive_deletes=True)


class PronunciationData(Base):
    __tablename__ = "pronunciation_data"

    id = Column(Integer, primary_key=True, index=True)
    # 'ㄱ', 'ㅏ' 등 한글 자모음
    hangul_char = Column(String, unique=True, index=True, nullable=False)
    # /static/images/c-g.png 와 같은 기존 이미지 경로
    image_url = Column(String, nullable=True)
    # Cloudinary에 저장된 영상의 URL
    video_url = Column(String, nullable=True)
    
#위 모델을 추가한 후, Base.metadata.create_all(bind=engine) 코드가 실행될 때 pronunciation_data 테이블이 새로 생성됩니다.