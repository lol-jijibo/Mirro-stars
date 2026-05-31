"""
Mirro 数据库模块
负责MySQL数据库连接管理、表结构初始化。
使用 aiomysql 实现异步数据库操作，不阻塞主线程。
"""
import aiomysql
from app.core.config import settings


class MySQLDatabase:
    """
    MySQL数据库封装类
    对外提供与 aiosqlite 兼容的接口（execute / commit / execute_fetchall），
    内部自动将 SQLite 风格的 ? 占位符转换为 MySQL 的 %s 占位符，
    使业务层代码无需改动 SQL 语法。
    """

    def __init__(self, conn: aiomysql.Connection):
        self._conn = conn

    async def execute(self, sql: str, params: tuple = ()) -> None:
        """执行写操作（INSERT / UPDATE / DELETE）"""
        sql = sql.replace("?", "%s")
        async with self._conn.cursor() as cur:
            await cur.execute(sql, params)

    async def commit(self) -> None:
        """提交事务"""
        await self._conn.commit()

    async def execute_fetchall(self, sql: str, params: tuple = ()) -> list[tuple]:
        """执行查询并返回所有结果行"""
        sql = sql.replace("?", "%s")
        async with self._conn.cursor() as cur:
            await cur.execute(sql, params)
            return await cur.fetchall()

    async def close(self) -> None:
        """关闭底层连接"""
        self._conn.close()


# 全局数据库连接实例（应用启动时初始化，单连接模式）
_conn: aiomysql.Connection | None = None
_db: MySQLDatabase | None = None


async def get_db() -> MySQLDatabase:
    """
    获取数据库连接（懒加载单例模式）
    首次调用时自动建立MySQL连接并创建表结构，后续调用复用同一连接。
    业务场景：所有API路由通过此函数获得数据库连接，执行CRUD操作。
    """
    global _conn, _db
    if _conn is None:
        _conn = await aiomysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            db=settings.DB_NAME,
            autocommit=False,
            charset="utf8mb4",
        )
        _db = MySQLDatabase(_conn)
        await _init_tables(_db)
    return _db


async def _init_tables(db: MySQLDatabase):
    """
    初始化数据库表结构
    在首次数据库连接时自动执行，确保所有业务表存在。
    业务场景：项目首次启动时自动建表，无需手动执行SQL脚本。
    """
    # 问题表 — 记录用户提出的每一个问题
    await db.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id VARCHAR(36) PRIMARY KEY COMMENT '问题唯一ID，使用UUID',
            content TEXT NOT NULL COMMENT '用户提问的原始内容',
            category VARCHAR(50) COMMENT 'AI自动分类：职业/情感/成长/理财/健康/社交/其他',
            created_at VARCHAR(255) NOT NULL COMMENT '提问时间，ISO8601格式'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    # 答案表 — 存储AI生成的完整解答方案
    await db.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id VARCHAR(36) PRIMARY KEY COMMENT '答案唯一ID',
            question_id VARCHAR(36) NOT NULL COMMENT '关联的问题ID',
            content TEXT COMMENT 'AI生成的Markdown格式解答正文',
            answer_type VARCHAR(20) DEFAULT 'insight' COMMENT '答案类型: action=含步骤计划, insight=纯深度分析',
            flowchart_mermaid TEXT COMMENT 'Mermaid流程图语法，前端直接渲染',
            steps TEXT COMMENT '分步执行计划，JSON数组 [{step, title, desc, duration}]',
            sources TEXT COMMENT '引用来源，JSON数组 [{title, url, snippet}]',
            created_at VARCHAR(255) NOT NULL COMMENT '生成时间',
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)

    await db.commit()

    # 兼容旧表：如果 answers 表已存在但缺少 answer_type 列，则自动添加
    try:
        await db.execute("""
            ALTER TABLE answers ADD COLUMN answer_type VARCHAR(20) DEFAULT 'insight'
            COMMENT '答案类型: action=含步骤计划, insight=纯深度分析'
            AFTER content
        """)
        await db.commit()
    except Exception:
        pass  # 列已存在则跳过


async def close_db():
    """关闭数据库连接（应用关闭时调用）"""
    global _conn, _db
    if _conn:
        _conn.close()
        _conn = None
        _db = None
