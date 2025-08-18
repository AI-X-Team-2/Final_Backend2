# main.py
# FastAPI 앱을 실행하는 진입점입니다.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# 데이터베이스 설정 및 모델 임포트
from app.database import Base, engine

# 라우터 임포트
from app.routers import users, results, pronunciation, progress, sessions, video # 기존 routers/pronunciation.py

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 데이터베이스 테이블 생성
# Base.metadata.create_all(bind=engine)
# --- [설명] ---
# 위 코드는 개발 환경에서는 편리하지만, 실제 배포 환경에서는 사용하지 않는 것이 좋습니다.
# 데이터베이스 스키마(테이블 구조)는 별도의 .sql 파일이나 Alembic과 같은 마이그레이션 도구로 관리해야 합니다.
# 백엔드 서버는 DB 스키마를 변경하는 권한을 갖지 않는 것이 보안상 안전합니다.

# FastAPI 앱 생성 및 설정
app = FastAPI(title="유음 database")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터들을 메인 앱에 포함시킵니다.
app.include_router(pronunciation.router)
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(results.router, prefix="/api/results", tags=["Results"])
app.include_router(progress.router, prefix="/api/progress", tags=["Progress"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Study Sessions"])
app.include_router(video.router, prefix="/api", tags=["Video Processing"])


# 정적 파일(이미지)을 서빙할 경로를 마운트합니다.
app.mount("/static/images", StaticFiles(directory="static/images"), name="static_images")

# 루트 엔드포인트
@app.get("/")
async def root():
    return {"message": "의사소통 보조 AI 유음"}