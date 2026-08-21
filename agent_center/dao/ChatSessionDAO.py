import random
import uuid

from sqlalchemy.orm import scoped_session

from config import get_id, config_manager, logger
from dao.BaseDAO import BaseDAO
from dao.pojo import ChatSession
from vo import SessionVO, Example, ChatSessionVO
from sqlalchemy import select, delete
from sqlalchemy.orm import scoped_session
from typing import Optional
from collections import defaultdict
from datetime import datetime, date

class ChatSessionDAO(BaseDAO):

    def __init__(self):
        pass

    def create_session(self, num: int, agent_id: int, user_id: int):
        """
        创建新的聊天会话，并随机选取示例。
            Args:
                num (int): 随机选取的示例数量
                agent_id (int): 智能体 ID
                user_id (int): 用户 ID

            Returns:
                SessionVO: 会话数据对象，包括示例列表
        """

        logger.debug("开始创建新的 ChatSession（示例数量: %d）", num)
        # scoped_session = 线程隔离会话工厂 类似threadLocal
        def _create(session: scoped_session):
            # 1) 创建一个聊天会话记录, 保存到数据库
            chat_session = ChatSession(
                id=get_id(),  # 全局唯一id
                session_id=uuid.uuid4().hex,  # 会话id
                user_id=user_id,
                agent_id=agent_id
            )
            session.add(chat_session)
            logger.debug("ChatSession 已创建：id=%s, session_id=%s", chat_session.id, chat_session.session_id)

            # 2) 创建返回的vo对象
            session_vo = SessionVO(
                sessionId=chat_session.session_id,
                title=config_manager.get(f"ai.{agent_id}.session.title"),
                describe=config_manager.get(f"ai.{agent_id}.session.describe"),
                examples=self.hot_examples(num, agent_id)
            )
            logger.debug("ChatSession 创建成功，session_id=%s", chat_session.session_id)
            return session_vo

        return self._execute(_create)
    # 更新会话的标题
    def update_session_title(self, session_id: str, title: str):
        def _update_session_title(scoped: scoped_session):
            # 先查询会话是否已经存在标题
            stmt = select(ChatSession).where(ChatSession.session_id == session_id)  # type: ignore
            chat_session: Optional[ChatSession] = scoped.execute(stmt).scalars().first()

            # 如果不存在标题，则设置
            if chat_session is not None and chat_session.title is None:
                chat_session.title = title
                chat_session.update_time = datetime.now()
                logger.debug("更新 ChatSession 标题成功：session_id=%s, title=%s", session_id, title)

        self._execute(_update_session_title)
    # 热点问题
    def hot_examples(self, num: int = 3, agent_id: int = 1001):
        examples = config_manager.get(f"ai.{agent_id}.session.examples", [])
        examples = random.sample(examples, min(num, len(examples)))
        return [Example(title=e.get('title'), describe=e.get('describe')) for e in examples]

    # 查询历史会话
    def query_history_session(self, agent_id: int, user_id: int):
        # 时间分组常量
        TODAY = "当天"
        LAST_30_DAYS = "最近30天"
        LAST_YEAR = "最近1年"
        MORE_THAN_YEAR = "1年以上"

        def _query_app_info(session: scoped_session):
            stmt = (select(ChatSession)
                    .where(ChatSession.agent_id == agent_id)  # type: ignore
                    .where(ChatSession.user_id == user_id)
                    .where(ChatSession.title.isnot(None))
                    .order_by(ChatSession.update_time.desc())
                    .limit(30))

            chat_sessions = session.execute(stmt).scalars().all()
            if not chat_sessions:
                return {}

            chat_session_vo_list = [
                ChatSessionVO(
                    session_id=cs.session_id,
                    title=cs.title,
                    update_time=cs.update_time
                )
                for cs in chat_sessions
            ]

            # 按时间分组
            now = date.today()
            groups = defaultdict(list)
            for vo in chat_session_vo_list:
                days = abs((now - vo.update_time.date()).days)
                if days == 0:
                    key = TODAY
                elif days <= 30:
                    key = LAST_30_DAYS
                elif days <= 365:
                    key = LAST_YEAR
                else:
                    key = MORE_THAN_YEAR
                groups[key].append(vo)

            # 按顺序返回
            order = [MORE_THAN_YEAR, LAST_YEAR, LAST_30_DAYS, TODAY]
            return {key: groups[key] for key in order if key in groups}

        return self._execute(_query_app_info)
    # 删除历史会话
    def delete_history_session(self, agent_id: int, user_id: int, session_id: str):
        def _delete_history_session(session: scoped_session):
            stmt = (delete(ChatSession)
                    .where(ChatSession.agent_id == agent_id)  # type: ignore
                    .where(ChatSession.user_id == user_id)
                    .where(ChatSession.session_id == session_id))
            session.execute(stmt)
        self._execute(_delete_history_session)

    # 更新历史会话标题
    def update_history_session(self, agent_id: int, user_id: int, session_id: str, title: str):
        def _update_history_session(session: scoped_session):
            stmt = (update(ChatSession)
                    .where(ChatSession.agent_id == agent_id)  # type: ignore
                    .where(ChatSession.user_id == user_id)
                    .where(ChatSession.session_id == session_id)
                    .values(title=title[:100]))  # 限制标题长度
            session.execute(stmt)
        self._execute(_update_history_session)
# 全局 ChatSessionDAO 实例
chat_session_dao = ChatSessionDAO()