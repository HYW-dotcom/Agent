from fastapi import APIRouter

from agent import AGENTS
from dao import chat_session_dao

# 创建路由对象
session_router = APIRouter()


# =============================请求体模型=============================

# =============================路由接口=============================
@session_router.post("")
async def create_session(n: int, agent_id: int, user_id: int):
    """
    创建新的聊天会话，并返回会话VO
    - n: 随机选取的示例数量
    - agent_id: 智能体ID
    - user_id: 用户ID
    """
# 查询历史会话
@session_router.get("/history")
async def query_history_session(agent_id: int, user_id: int):
    return chat_session_dao.query_history_session(agent_id, user_id)

# 查询指定会话详情
@session_router.get("/{agent_id}/{user_id}/{session_id}")
async def session_detail(agent_id: int, user_id: int, session_id: str):
    agent = AGENTS.get(agent_id, None)
    if agent is None:
        return f"Agent not found (agentId={agent_id})"

    # 调用智能体的 session_detail 方法，获取会话详情
    return await agent.session_detail(user_id, session_id)
# 删除历史会话
@session_router.delete("/history")
async def delete_history_session(agent_id: int, user_id: int, session_id: str):
    agent = AGENTS.get(agent_id, None)
    if agent is None:
        return f"Agent not found (agentId={agent_id})"

    # 调用智能体的方法删除会话详情
    await agent.delete_session(session_id)

    # 删除数据库中的历史会话
    return chat_session_dao.delete_history_session(agent_id, user_id, session_id)

# 更新历史会话标题
@session_router.put("/history")
async def update_history_session(agent_id: int, user_id: int, session_id: str, title: str):
    chat_session_dao.update_history_session(agent_id, user_id, session_id, title)
    return {"status": "ok", "message": "No change"}
    return chat_session_dao.create_session(n, agent_id, user_id)