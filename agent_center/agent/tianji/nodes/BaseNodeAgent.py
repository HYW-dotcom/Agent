from abc import ABC, abstractmethod
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from agent.tianji import RobotState
from config import config_manager


@dataclass
class ToolContext:
    user_token: str
    request_id: str


# 机器人智能体中各个节点智能体的父类
class BaseNodeAgent(ABC):

    def __init__(self):
        # 读取模型基础配置
        self.model_name = config_manager.get("ai.openai.model")
        self.api_key = config_manager.get("ai.openai.api-key")
        self.base_url = config_manager.get("ai.openai.base-url")
        self.temperature = float(config_manager.get("ai.openai.temperature", 0.7))
        self.timeout = int(config_manager.get(f"ai.openai.timeout", 60))

        # 初始化 LLM
        self.llm = init_chat_model(
            model=self.model_name,
            model_provider="openai",
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            timeout=self.timeout,
            tags=[self.__class__.__name__]  # 为该模型调用添加 tag，用于后续追踪/过滤
        )

        # 创建LangChain Agent（自动加载 tools）
        self.agent = create_agent(
            model=self.llm,
            tools=self.tools()
        )

    # 智能体使用到的tools
    def tools(self):
        return []

    # 智能体使用的提示词
    @abstractmethod
    def system_prompt(self) -> str:
        pass

    # 智能体使用的提示词中的变量
    def system_prompt_params(self):
        return {}

    # 智能体执行返回的结果
    def do_result(self, messages):
        return {"messages": messages}

    # 智能体节点要执行的核心逻辑
    async def execute(self, state: RobotState, config: RunnableConfig):
        # 1 准备提示词
        # 1-1) 获取原始消息内容（不修改 state 原始消息）
        messages = state["messages"]

        # 1-2) 为避免污染原消息列表，进行深拷贝
        new_messages = messages.copy()

        # 1-3) 构建 SystemMessage（允许使用动态参数）
        params = self.system_prompt_params()
        system_msg = SystemMessage(self.system_prompt().format(**params))

        # 1-4) 将系统提示词添加到用户提示词之前
        if len(new_messages) >= 1:
            new_messages.insert(-1, system_msg)
        else:
            new_messages.append(system_msg)

        # 2) 调用大模型智能体执行推理
        res = await self.agent.ainvoke(
            input={"messages": new_messages}
        )

        # 3)交给子类最终处理
        return self.do_result(res['messages'])