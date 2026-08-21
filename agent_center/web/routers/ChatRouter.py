from typing import AsyncIterable

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from agent import AGENTS
from agent.BaseAgent import make_sse_event
from config import logger
from dao import chat_session_dao

# 创建路由对象
chat_router = APIRouter()


# ========================= SSE 错误流 =========================
async def error_stream(message: str) -> AsyncIterable[str]:
    """
    异步生成错误消息的 SSE 流
    """
    yield make_sse_event(404, message)  # 将错误信息包装成 SSE 格式


# ========================= SSE 响应封装 =========================
def stream(data: AsyncIterable[str]) -> StreamingResponse:
    """
    将异步迭代对象封装为 StreamingResponse，返回 SSE 流
    """
    return StreamingResponse(
        data,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}  # 禁止缓存
    )


# =============================请求体模型=============================
class ChatModel(BaseModel):
    """
    用户发送给智能体的请求体
    """
    question: str  # 用户提出的问题
    sessionId: str  # 会话ID，用于关联上下文
    userToken: str  # 用户身份token，用于调用业务系统接口
    agentId: int  # 智能体ID


# =============================接口=============================
@chat_router.post("")
async def chat(chatModel: ChatModel):
    logger.debug(
        f"【ChatRouter】收到请求：question = {chatModel.question}, sessionId = {chatModel.sessionId}, agentId = {chatModel.agentId}")

    # 根据智能体id定位负责处理请求的智能体
    agent = AGENTS.get(chatModel.agentId)
    if agent is None:
        error_msg = f"Agent not found (agentId={chatModel.agentId})"
        return stream(error_stream(error_msg))  # 返回错误 SSE 流

    return stream(agent.execute(chatModel.question, chatModel.sessionId, chatModel.userToken))

# ========================= 停止会话接口 =========================
@chat_router.post("/stop")
def stop(session_id: str, agent_id: int):
    """
    停止指定 session 的对话：
    - 根据 agent_id 获取智能体
    - 调用 agent.stop(session_id) 停止该会话
    """
    logger.debug(f"【ChatRouter】收到停止请求：sessionId = {session_id}")

    # 获取智能体
    agent = AGENTS.get(agent_id, None)
    if agent is None:
        error_msg = f"Agent not found (agentId={agent_id})"
        return {"status": "ok", "message": error_msg}

    # 停止会话
    agent.stop(session_id)
    return {"status": "ok"}  # 返回成功状态