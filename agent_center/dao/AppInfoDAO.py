from sqlalchemy import select
from sqlalchemy.orm import scoped_session

from common import JWT_EXPIRE_HOURS, JWT_PRIVATE_KEY
from config import config_manager
from dao.BaseDAO import BaseDAO
from dao.pojo import AppInfo
from util import JWTUtil


class AppInfoDAO(BaseDAO):
    def __init__(self):
        self._expire_hours = int(config_manager.get(JWT_EXPIRE_HOURS))
        self._private_key = config_manager.get(JWT_PRIVATE_KEY)

    def create_token(self, app_key: str, app_secret: str):
        """
        通过 app_key 和 app_secret 获取访问接口凭证（JWT）。
        Args:
            app_key (str): 应用的唯一 key
            app_secret (str): 应用的密钥
        Returns:
            dict: 包含 token、有效期和 app_id 信息
        """

        def _query_app_info(session: scoped_session):
            # 1)根据app_key从数据库中查询记录
            stmt = select(AppInfo).where(AppInfo.app_key == app_key)  # type:ignore
            app_info = session.execute(stmt).scalars().first()

            # 2) 如果记录不存在,直接抛异常
            if app_info is None:
                raise Exception("生成token失败,app_key不存在")

            # 3) 校验app_secret是否正确,如果不正确,抛异常
            if app_info.app_secret != app_secret:
                raise Exception("生成token失败,app_secret错误")

            # 4) 如果没有问题,则生成token返回
            token = JWTUtil.create_token(
                data={
                    "app_id": app_info.id,
                    "app_key": app_key,
                    "name": app_info.name
                },
                private_key_b64=self._private_key,
                expire_hours=self._expire_hours
            )
            return {
                "token": token,
                "expire_hours": self._expire_hours,
                "app_id": app_info.id
            }

        # 使用 BaseDAO 提供的执行方法执行数据库操作
        return self._execute(_query_app_info)


# 创建单例对象
app_info_dao = AppInfoDAO()

if __name__ == '__main__':
    token = app_info_dao.create_token(
        "ddd8c127b3c1baa5f2ca7280d287a102",
        "5ca5087fd74a5afd5cb1cad3016e4980")
    print(f"token==>{token}")