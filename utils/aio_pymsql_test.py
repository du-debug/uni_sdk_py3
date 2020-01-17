"""
异步数据库链接aio_mysql, 文档地址：https://aiomysql.readthedocs.io/en/latest/cursors.html
根据需求可选择不同的游标，直接引用类的引用即可
"""
import datetime
import settings
import asyncio
import aiomysql

from utils.log_mixin import LogMixin

class DictCursor(aiomysql.DictCursor):
    """留待扩展,自定义字典类型"""
    pass

class CursorSs(aiomysql.SSCursor):
    """
    无缓冲游标，主要用于返回大量数据的查询或通过慢速网络连接到远程服务器
    """
    pass

class DictCursorSS(aiomysql.SSDictCursor):
    """
    一个无缓冲的游标，它以字典的形式返回结果。
    """
    pass

class AioMysqlPoll(LogMixin):
    """aiomysql数据库链接池"""

    def __init__(self, db_config, **kwargs):
        self._pool = None
        self._loop = asyncio.get_event_loop()
        self.db_config = db_config
        print(db_config, kwargs)

    async def sql_execute(self, sq_str, **kwargs):
        if not self._pool:
            self.db_config['loop'] = self._loop
            self._pool = await aiomysql.create_pool(**self.db_config, maxsize=15)
        async with self._pool.acquire() as coon:
            async with coon.cursor(DictCursor) as cursor:
                await cursor.execute(sq_str)
                res = await cursor.fetchall()
                return res
        # self._pool.close()
        # await self._pool.wait_closed()

    def query(self, sql_str):
        result = self._loop.run_until_complete(self.sql_execute(sql_str))
        print(result[0])


    def query_hash(self, sql_str):
        result = asyncio.run_coroutine_threadsafe(self.sql_execute(sql_str), self._loop)
        return result.result()

    def close(self):
        self._pool.close()


if __name__ == "__main__":
    test = AioMysqlPoll(settings.database_configs['aio_local_test'])
    for i in range(2):
        test.query_hash("select * from apps")
