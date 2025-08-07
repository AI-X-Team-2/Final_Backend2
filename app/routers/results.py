from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Result, DetailedFeedback
from app.schemas import ResultCreate, ResultResponse, FeedbackCreate, FeedbackResponse
from typing import List

router = APIRouter()

@router.post("/results", response_model=ResultResponse)
def create_result(result: ResultCreate, db: Session = Depends(get_db)):
    db_result = Result(**result.dict())
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

@router.get("/results/{user_id}", response_model=List[ResultResponse])
def get_user_results(user_id: int, db: Session = Depends(get_db)):
    return db.query(Result).filter(Result.user_id == user_id).all()

@router.post("/feedback", response_model=FeedbackResponse)
def create_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db)):
    db_feedback = DetailedFeedback(**feedback.dict())
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback
