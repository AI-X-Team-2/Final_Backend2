# app/routers/progress.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, load_only

from app.database import get_db
from app.models import User
from app.schemas import ProgressOut
from app.auth import SECRET_KEY, ALGORITHM
from fastapi.security import OAuth2PasswordBearer
import jwt

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    # PyJWT 기반 인증 (auth.py의 SECRET_KEY/ALGORITHM과 동일해야 함)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        username = payload.get("sub")
        if not user_id and not username:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰에 사용자 정보가 없습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다.")
    except jwt.InvalidTokenError:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

    # 필요한 컬럼만 조회 (최소 I/O)
    q = db.query(User).options(load_only(User.user_id, User.username, User.max_stage, User.max_step, User.max_level))
    db_user = q.filter(User.user_id == user_id).first() if user_id is not None else q.filter(User.username == username).first()
    if not db_user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return db_user


@router.get("/me", response_model=ProgressOut)
def read_my_progress(
    current_user: User = Depends(get_current_user),
):
    # 값이 None일 수 있으면 0으로 내려보내고 싶다면 아래처럼 바꾸세요:
    return ProgressOut(
        max_stage=current_user.max_stage or 0,
        max_step=current_user.max_step or 0,
        max_level=current_user.max_level or 0,
    )
    # return ProgressOut(
    #     max_stage=current_user.max_stage,
    #     max_step=current_user.max_step,
    #     max_level=current_user.max_level,
    # )
