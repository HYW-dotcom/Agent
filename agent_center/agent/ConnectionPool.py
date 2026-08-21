from psycopg_pool import AsyncConnectionPool
from config import config_manager
from common import *

# ---------------- 异步 PostgreSQL 连接池（懒加载单例） ----------------
_async_pg_pool: AsyncConnectionPool | None = None  # 全局异步连接池实例


# 创建PostgreSQL连接池
async def get_async_pg_pool() -> AsyncConnectionPool:
    global _async_pg_pool

    if _async_pg_pool is None:
        # 从配置获取连接池参数
        _async_pg_pool = AsyncConnectionPool(
            config_manager.get(AI_AGENT_CHECKPOINTER_POSTGRES_URL),  # 数据库连接 URL
            min_size=config_manager.get(AI_AGENT_CHECKPOINTER_POSTGRES_MIN),  # 最小连接数
            max_size=config_manager.get(AI_AGENT_CHECKPOINTER_POSTGRES_MAX),  # 最大连接数
            open=False  # 构造时不自动打开连接池
        )
        await _async_pg_pool.open()  # 手动打开连接池，建立实际连接
    return _async_pg_pool


# 关闭PostgreSQL连接池
async def close_async_pg_pool() -> None:
    global _async_pg_pool

    if _async_pg_pool is not None:
        await _async_pg_pool.close()  # 关闭所有连接
        _async_pg_pool = None  # 清理全局实例，允许重新创建