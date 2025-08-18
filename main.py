# main.py
# FastAPI 앱을 실행하는 진입점입니다.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# 데이터베이스 설정 및 모델 임포트
from app.database import Base, engine
from app.routers import users, results, pronunciation # router 파일 임포트
from app.utils.utils import init_levels

# 라우터 임포트
from app.routers import users, results, pronunciation # 기존 routers/pronunciation.py

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)
# Levels 테이블 초기값 삽입
init_levels()

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

# 정적 파일(이미지)을 서빙할 경로를 마운트합니다.
app.mount("/static/images", StaticFiles(directory="static/images"), name="static_images")

# 루트 엔드포인트
@app.get("/")
async def root():
    return {"message": "의사소통 보조 AI 유음"}