"""
Mirro 数据库模块
负责MySQL数据库连接池管理、表结构初始化。
使用 aiomysql 连接池实现并发安全的异步数据库操作。
"""
import aiomysql
from contextlib import asynccontextmanager
from app.core.config import settings


class MySQLDatabase:
    """
    MySQL数据库封装类
    对外提供 execute / commit / execute_fetchall 接口，
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

    async def table_exists(self, table_name: str) -> bool:
        """检查指定数据表是否已经存在"""
        rows = await self.execute_fetchall(
            "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ?",
            (table_name,)
        )
        return bool(rows and rows[0][0] > 0)

    async def column_exists(self, table_name: str, column_name: str) -> bool:
        """检查指定字段是否已经存在"""
        rows = await self.execute_fetchall(
            """SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ? AND COLUMN_NAME = ?""",
            (table_name, column_name)
        )
        return bool(rows and rows[0][0] > 0)


# 全局数据库连接池（应用启动时初始化）
_pool: aiomysql.Pool | None = None


async def _get_pool() -> aiomysql.Pool:
    """
    获取数据库连接池（懒加载单例模式）
    首次调用时自动建立连接池并初始化表结构，后续调用复用同一池。
    """
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            db=settings.DB_NAME,
            autocommit=False,
            charset="utf8mb4",
            init_command="SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci",
            minsize=2,   # 最小保持连接数
            maxsize=10,  # 最大连接数
            pool_recycle=3600,  # 每小时回收连接，防止MySQL wait_timeout断连
        )
        # 初始化表结构
        async with _pool.acquire() as conn:
            db = MySQLDatabase(conn)
            await _init_tables(db)
    return _pool


@asynccontextmanager
async def get_db():
    """
    获取数据库连接的异步上下文管理器
    业务场景：所有API路由通过此函数获得数据库连接，执行CRUD操作。
    使用完毕后自动归还连接到池中。

    用法:
        async with get_db() as db:
            await db.execute(...)
            await db.commit()
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        yield MySQLDatabase(conn)


async def init_db():
    """
    预初始化数据库连接池和表结构（应用启动时调用）
    确保首次API请求不需要等待连接池建立。
    """
    await _get_pool()


async def close_db():
    """
    关闭数据库连接池（应用关闭时调用）
    等待所有活跃连接归还后关闭。
    """
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


async def _init_tables(db: MySQLDatabase):
    """
    初始化数据库表结构
    在首次连接池建立时自动执行，确保所有业务表存在。
    业务场景：项目首次启动时自动建表，无需手动执行SQL脚本。
    """
    # 问题表 — 记录用户提出的每一个问题
    if not await db.table_exists("questions"):
        await db.execute("""
            CREATE TABLE questions (
                id VARCHAR(36) PRIMARY KEY COMMENT '问题唯一ID，使用UUID',
                content TEXT NOT NULL COMMENT '用户提问的原始内容',
                category VARCHAR(50) COMMENT 'AI自动分类：职业/情感/成长/理财/健康/社交/其他',
                conversation_id VARCHAR(36) COMMENT '多轮对话的会话ID，同一轮对话的所有问题共享此ID',
                created_at VARCHAR(255) NOT NULL COMMENT '提问时间，ISO8601格式'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        await db.commit()

    # 答案表 — 存储AI生成的完整解答方案
    if not await db.table_exists("answers"):
        await db.execute("""
            CREATE TABLE answers (
                id VARCHAR(36) PRIMARY KEY COMMENT '答案唯一ID',
                question_id VARCHAR(36) NOT NULL COMMENT '关联的问题ID',
                content TEXT COMMENT 'AI生成的Markdown格式解答正文',
                answer_type VARCHAR(20) DEFAULT 'insight' COMMENT '答案类型: action=含步骤计划, insight=纯深度分析',
                flowchart_mermaid TEXT COMMENT 'Mermaid流程图语法，前端直接渲染',
                steps TEXT COMMENT '分步执行计划，JSON数组 [{step, title, desc, duration}]',
                sources TEXT COMMENT '引用来源，JSON数组 [{title, url, snippet}]',
                action_summary TEXT COMMENT '答案顶部回应要点，JSON对象 {conclusion, first_action, timeframe, risk, fit_for}',
                related_questions TEXT COMMENT 'AI生成的相关追问建议，JSON数组',
                created_at VARCHAR(255) NOT NULL COMMENT '生成时间',
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        await db.commit()

    # 兼容旧表：如果 answers 表已存在但缺少 answer_type 列，则自动添加
    if not await db.column_exists("answers", "answer_type"):
        await db.execute("""
            ALTER TABLE answers ADD COLUMN answer_type VARCHAR(20) DEFAULT 'insight'
            COMMENT '答案类型: action=含步骤计划, insight=纯深度分析'
            AFTER content
        """)
        await db.commit()

    # 兼容旧表：如果 questions 表已存在但缺少 conversation_id 列，则自动添加
    if not await db.column_exists("questions", "conversation_id"):
        await db.execute("""
            ALTER TABLE questions ADD COLUMN conversation_id VARCHAR(36)
            COMMENT '多轮对话的会话ID，同一轮对话的所有问题共享此ID'
            AFTER category
        """)
        await db.commit()

    # 兼容旧表：如果 answers 表已存在但缺少 related_questions 列，则自动添加
    if not await db.column_exists("answers", "related_questions"):
        await db.execute("""
            ALTER TABLE answers ADD COLUMN related_questions TEXT
            COMMENT 'AI在生成答案时一并产出的相关追问建议，JSON数组'
            AFTER sources
        """)
        await db.commit()

    # 兼容旧表：如果 answers 表已存在但缺少 action_summary 列，则自动添加
    if not await db.column_exists("answers", "action_summary"):
        await db.execute("""
            ALTER TABLE answers ADD COLUMN action_summary TEXT
            COMMENT '答案顶部回应要点，JSON对象'
            AFTER sources
        """)
        await db.commit()

    # 反馈表 — 记录用户对AI答案的评价
    if not await db.table_exists("feedback"):
        await db.execute("""
            CREATE TABLE feedback (
                id VARCHAR(36) PRIMARY KEY COMMENT '反馈唯一ID',
                question_id VARCHAR(36) NOT NULL COMMENT '关联的问题ID',
                answer_id VARCHAR(36) NOT NULL COMMENT '关联的答案ID',
                rating INT NOT NULL DEFAULT 0 COMMENT '评分：1=好评, -1=差评, 0=中性',
                comment TEXT COMMENT '可选的文字反馈',
                created_at VARCHAR(255) NOT NULL COMMENT '反馈时间',
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                FOREIGN KEY (answer_id) REFERENCES answers(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        await db.commit()
