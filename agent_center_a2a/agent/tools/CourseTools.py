import random

from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from agent.rag import vector_store
from agent.tools.result import CourseInfo
from common import GATEWAY_SERVICE_NAME
from config import nacos_config, logger
from util import HttpClientUtil, JsonUtil


# 查询课程信息
@tool
def query_course_info(course_id: int, tool_runtime: ToolRuntime):
    """
    根据课程 ID 查询课程数据
    Args:
        course_id : 课程 ID
        runtime: 获取运行参数
    """

    # 1) 获取工具运行时参数
    user_token = tool_runtime.context.user_token
    request_id = tool_runtime.context.request_id

    # 2) 从Nacos获取业务系统网关实例
    instances = nacos_config.get_discovery_client().list_naming_instance(GATEWAY_SERVICE_NAME).get("hosts", [])
    if not instances:
        logger.error("No gateway-service instances found")
        return None

    instance = random.choice(instances)# 随机选择一个网关实例发起请求，分散负载
    url = f"http://{instance['ip']}:{instance['port']}/cs/courses/baseInfo/{course_id}"

    # 3) 调用业务系统,查询课程信息
    # url = f"http://127.0.0.1:10010/cs/courses/baseInfo/{course_id}"
    response = HttpClientUtil.get(url=url, token=user_token) or {}
    data = response.get("data")

    # 3) 返回课程信息
    if not data:
        return None
    else:
        course_info = CourseInfo.of(data)
        return JsonUtil.to_str(course_info)


@tool
def query_recommend_data(question: str):
    """
    根据用户问题中的年龄、学历、兴趣推荐课程
    Args:
        question: 用户问题
    """

    # 调用向量库查询
    docs = vector_store.search(question, k=3)
    result = "\n".join([doc['text'] for doc in docs])
    logger.debug(f"向量库查询结果：{result}")
    return result