import re

from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models import Levels

def is_valid_email(email: str) -> bool:
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

def is_blank(field: str) -> bool:
    return not field or field.strip() == ""


def init_levels():
    db = SessionLocal()
    try:
        if db.query(Levels).count() == 0:
            db.add_all([
                Levels(levels="초급"),
                Levels(levels="중급"),
                Levels(levels="고급")
            ])
            db.commit()
            print("✅ Levels 테이블 초기값이 삽입되었습니다.")
        else:
            print("ℹ️ Levels 테이블에 이미 값이 존재합니다. 삽입 생략.")
    except IntegrityError:
        db.rollback()
        print("⚠️ 무결성 오류로 초기값 삽입 실패")
    finally:
        db.close()