from langgraph.graph import MessagesState

# 机器人智能体的状态
class RobotState(MessagesState):
    intent: str # 意图