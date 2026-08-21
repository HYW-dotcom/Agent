from fastapi import APIRouter
from pydantic import BaseModel

from dao import app_info_dao

# 创建路由对象
auth_router = APIRouter()


# =============================请求体模型=============================
class Auth(BaseModel):
    app_key: str
    app_secret: str


# =============================路由接口=============================
@auth_router.post("/token")
async def create_token(auth: Auth):
    return app_info_dao.create_token(auth.app_key, auth.app_secret)