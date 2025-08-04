# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from routes import pronunciation

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# --- FastAPI 앱 초기화 및 설정 ---
app = FastAPI()

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 실제 배포 시 ["https://your-frontend-domain.com"] 특정 출처를 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 경로 설정
app.mount("/static/images", StaticFiles(directory="static/images"), name="static_images")

# 라우터 포함
#routes/pronunciation.py 파일에 정의된 모든 API 경로들(/, /analyze 등)을 메인 app에 연결하여 실제로 동작하도록 "플러그인"처럼 장착함
app.include_router(pronunciation.router)