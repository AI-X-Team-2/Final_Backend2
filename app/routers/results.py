# app/routers/feedback.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload
from app.database import get_db
from app.models import (
    Feedback,
    SyllableFeedback,
    PronunciationFeedback,   # ✅ 단일 1:1 상세 테이블
)
from app.schemas import (
    FeedbackCreate,          # ✅ payload.pronunciation, payload.syllable_feedbacks 를 포함하도록 정의되어 있어야 함
    FeedbackOut,             # ✅ 응답 스키마에 pronunciation, syllable_feedbacks 포함
)
from typing import List

router = APIRouter()

# 생성: 상위 Feedback + (1:1 발음 상세) + (음절 상세 0..N)
@router.post("/feedbacks", response_model=FeedbackOut)
def create_feedback(payload: FeedbackCreate, db: Session = Depends(get_db)):
    # 1) 부모 생성
    fb = Feedback(
        user_id=payload.user_id,                 # 사용자 부분은 유효한 id가 넘어온다고 가정
        feedback_type=payload.feedback_type,     # "basic" | "real_life"
    )
    db.add(fb)
    db.flush()  # feedback_id 확보

    # 2) 1:1 발음 상세 (선택)
    if payload.pronunciation:
        pf = PronunciationFeedback(
            feedback_id=fb.feedback_id,
            **payload.pronunciation.model_dump(exclude_none=True),
        )
        db.add(pf)

    # 3) 음절 상세(선택, 0..N)
    if payload.syllable_feedbacks:
        for sf in payload.syllable_feedbacks:
            db.add(SyllableFeedback(
                feedback_id=fb.feedback_id,
                **sf.model_dump(exclude_none=True),
            ))

    db.commit()

    # 4) 응답용으로 관계까지 로드해서 반환
    fb_full = (
        db.query(Feedback)
          .options(
              joinedload(Feedback.pronunciation),        # ✅ 단일 1:1
              selectinload(Feedback.syllable_feedbacks), # ✅ 1:N
          )
          .filter(Feedback.feedback_id == fb.feedback_id)
          .one()
    )
    return fb_full


# 조회: 특정 유저의 모든 피드백 목록
@router.get("/feedbacks/user/{user_id}", response_model=List[FeedbackOut])
def list_user_feedbacks(user_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(Feedback)
          .options(
              joinedload(Feedback.pronunciation),
              selectinload(Feedback.syllable_feedbacks),
          )
          .filter(Feedback.user_id == user_id)
          .order_by(Feedback.created_at.desc())
          .all()
    )
    return rows


# (선택) 단건 조회
@router.get("/feedbacks/{feedback_id}", response_model=FeedbackOut)
def get_feedback(feedback_id: int, db: Session = Depends(get_db)):
    fb = (
        db.query(Feedback)
          .options(
              joinedload(Feedback.pronunciation),
              selectinload(Feedback.syllable_feedbacks),
          )
          .filter(Feedback.feedback_id == feedback_id)
          .first()
    )
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return fb
