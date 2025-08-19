from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import StudySession, User   # ✅ StudyResult 추가
from app.auth import get_current_user
from app.schemas import StudySessionOut

router = APIRouter()

@router.patch("/{session_id}/complete", response_model=StudySessionOut, status_code=status.HTTP_200_OK)
def complete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 내 세션 조회
    session = (
        db.query(StudySession)
        .filter(
            StudySession.session_id == session_id,
            StudySession.user_id == current_user.user_id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없거나 권한이 없습니다.")

    # ✅ 완료 처리 + 통과 여부 저장
    if session.status != "completed":
        session.status = "completed"
        session.completed_at = func.now()
        
    # =====================================
    # ✅ 통과 여부 계산 (correct_count vs total_words)
    # =====================================
    total_words = session.total_words or 0
    correct_count = session.correct_count or 0

    # 절반 초과 조건 → correct_count > total_words / 2
    is_passed_bool = correct_count > (total_words / 2)

    # (선택) 세션 테이블에 is_passed 같은 컬럼이 있으면 저장
    if hasattr(session, "is_passed"):
        session.is_passed = is_passed_bool

    if is_passed_bool:
        user = db.query(User).filter(User.user_id == current_user.user_id).first()
        if user:
            curr = user.max_level or []
            # [0]이면 그대로 유지
            if curr == [0]:
                pass
            else:
                # 이미 2가 없고 1이 있으면 [1,2]로 (정렬/중복제거 포함)
                if 2 not in curr and 1 in curr:
                    new_levels = sorted(set(curr + [2]))
                    # 🔴 중요: JSON은 새 리스트로 재할당해야 변경 감지됨
                    user.max_level = new_levels
                    db.add(user)

    db.add(session)
    db.commit()
    db.refresh(session)

    # 응답은 bool로 반환 (스키마가 bool이면 더 안전)
    return StudySessionOut(
        session_id=session.session_id,
        user_id=session.user_id,
        status=session.status,
        created_at=session.created_at,
        completed_at=session.completed_at,
        total_words=session.total_words,
        level=session.level,
        isPassed=is_passed_bool,  # ✅ bool로 반환
        correct_count=correct_count,  # ✅ 추가: 학습 결과 포함
    )
