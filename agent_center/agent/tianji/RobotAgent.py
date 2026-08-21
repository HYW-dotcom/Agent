from typing import AsyncIterable

from agent.BaseAgent import BaseAgent
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import StateSnapshot

# 机器人智能体
class RobotAgent(BaseAgent):
    # 声明用于 Graph 的所有节点智能体（节点 = 子 Agent）
    INTENT_MAPS = {
        "intent_agent": IntentAgent(),
        "recommend_agent": RecommendAgent(),
        "buy_agent": BuyAgent(),
        "consult_agent": ConsultAgent(),
        "knowledge_agent": KnowledgeAgent(),
        "unknown_agent": UnknownAgent(),
    }

    def __init__(self):
        self.graph: Optional[CompiledStateGraph] = None
        self.checkpointer: Optional[AsyncPostgresSaver] = None  # 用于保存会话状态的 Postgres Checkpointer

    # 初始化图
    async def init(self):
        # ========= 检查数据库中是否存在会话记忆相关的表，如果不存在则创建======
        async_pg_pool = await get_async_pg_pool()
        conn = None
        try:
            conn = await async_pg_pool.getconn()
            await conn.set_autocommit(True)  # 设置自动提交，不使用显式事务块
            self.checkpointer = AsyncPostgresSaver(conn=conn)
            await self.checkpointer.setup()  # 如果会话记忆相关的表不存在，会自动创建
        finally:
            if conn is not None:
                await async_pg_pool.putconn(conn)

        # ============ 初始化图======
        # 创建checkpointer是用于实现会话记忆的
        self.checkpointer = AsyncPostgresSaver(conn=async_pg_pool)
        # 1) 创建图
        graph_builder = StateGraph(RobotState)

        # 2) 将所有的节点(函数)添加到图
        for agent_name, agent in self.INTENT_MAPS.items():
            graph_builder.add_node(agent_name, agent.execute)

        # 3) 使用边将节点串链起来
        # 3-1) 开始->意图智能体
        graph_builder.add_edge(START, "intent_agent")

        # 3-2) 意图智能体->根据条件->分支智能体
        def intent_router_gate(state: RobotState):
            # 获取到意图
            intent = state.get("intent")
            if intent is None or intent == "" or intent == '':
                intent = "UNKNOWN"
            logger.debug(f"【IntentAgent】智能体识别到的意图：{intent}")
            return intent

        graph_builder.add_conditional_edges("intent_agent", intent_router_gate, INTENT_TO_AGENT)
        # 3-3) 分支智能体->END
        for target in INTENT_TO_AGENT.values():
            graph_builder.add_edge(target, END)

        # 4) 编译图
        self.graph = graph_builder.compile(checkpointer=self.checkpointer)
        logger.debug(f"【RobotAgent】编译图完成")
    # 执行智能体
    async def execute(self, question: str, session_id: str, user_token: str) -> AsyncIterable[str]:
        # 更新会话标题
        chat_session_dao.update_session_title(session_id,  question)

        # 清除停止标记
        self.reset_stop(session_id)
        try:
            # 创建请求id
            request_id = uuid.uuid4().hex

            # 更新会话标题
            chat_session_dao.update_session_title(session_id, question)

            # 1) 构建config对象
            config = {"configurable": {
                "thread_id": session_id,  # 会话id,用于后面区分会话记忆
                "user_token": user_token,  # 将自定义参数传递给子智能体
                "request_id": request_id  # 将自定义参数传递给子智能体
            }}

            # 2) 构建请求消息对象
            inputs = {"messages": HumanMessage(question)}

            # 3) 执行图
            res = self.graph.astream(
                input=inputs,  # 输入内容
                config=config,  # 配置选项
                stream_mode="messages",  # 流模式
                subgraphs=True, # 需要得到子图的输出
            )
            # 定义一个对象用于存储工具输出
            tool_result = {}
            # 4) 返回处理结果
            try:
                async for node_info, (message, metadata) in res:
                    # 检查是否收到停止标记
                    if self.is_stop(session_id):
                        await res.aclose()
                        break
                    # 获取消息 tags（例如 IntentAgent）,如果是IntentAgent, 则跳过
                    tags = metadata.get("tags", [])
                    if "IntentAgent" in tags:
                        continue

                    #  提前返回消息中的内容
                    content = getattr(message, "content", None)
                    if content:
                        yield make_sse_event(1001, content)
            except asyncio.CancelledError:
                # 客户端中断，也需要安全关闭流
                await res.aclose()
                raise
        except Exception as e:
            logger.exception(f"RobotAgent error:{e}")
            yield make_sse_event(2001, str(e))

        # SSE 最终停止事件（前端用于关闭流）
        yield format_sse_data(STOP_EVENT)

    # 定义智能体的id
    def id(self) -> int:
        return 1001

    # 查询返回会话明细
    async def session_detail(self, user_id: int, session_id: str) -> list:
        # 根据session查询会话详情
        config = RunnableConfig(configurable={
            "thread_id": session_id
        })
        state_snapshot: StateSnapshot = await self.graph.aget_state(config)
        messages = state_snapshot.values.get("messages", [])

        result = []
        # 遍历消息, 将其中User和AI类型的消息存储到列表中
        for message in messages:
            message_type = ""
            message_content = message.content
            params = {}

            if isinstance(message, HumanMessage):
                message_type = "USER"
            elif isinstance(message, AIMessage):
                message_type = "ASSISTANT"
            else:
                continue

            if message_type and message_content:
                result.append({
                    "type": message_type,
                    "content": message_content,
                    "params": params
                })
        return result

    # 删除会话
    async def delete_session(self, session_id: str):
        # 删除会话
        await self.checkpointer.adelete_thread(session_id)


# 全局 RouterAgent 实例
robot_agent = RobotAgent()