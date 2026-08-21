# 智能体id 与 对应的智能体实例
from agent.BaseAgent import BaseAgent
from agent.tianji import robot_agent

AGENTS: dict[int, BaseAgent] = {
    # 智能体id :  智能体对象
    robot_agent.id(): robot_agent,  # 1001, 机器人智能体对象
}