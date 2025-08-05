from fastapi import FastAPI
from app.database import Base, engine
from app.routers import users, results
from app.utils import init_levels

# 테이블 생성
Base.metadata.create_all(bind=engine)
init_levels()
app = FastAPI(title="유음 database")

# 라우터 등록
app.include_router(users.router)
app.include_router(results.router)
