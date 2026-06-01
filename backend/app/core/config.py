"""
Mirro 后端核心配置模块
负责加载环境变量、统一管理所有配置项，确保各服务模块使用一致的配置。
"""
import os
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
load_dotenv()


class Settings:
    """
    全局配置单例
    所有业务模块通过 from app.core.config import settings 获取配置
    """

    # ========== LLM 配置 — AI答案生成引擎 ==========
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")      # 模型提供商: openai / claude / deepseek
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")               # API密钥
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")             # 模型名称
    LLM_BASE_URL: str | None = os.getenv("LLM_BASE_URL")          # 自定义API地址（DeepSeek等兼容接口需要）

    # ========== 搜索配置 — 全网案例检索 ==========
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")                    # Tavily搜索API密钥（免费1000次/月）

    # ========== 数据库配置 — MySQL ==========
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "mirro")

    # ========== 服务配置 ==========
    APP_TITLE: str = "Mirro AI — 问题解决引擎"                    # API文档标题
    APP_VERSION: str = "0.1.0"                                     # 当前版本号
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]            # 允许跨域的前端地址（Vite默认端口）


# 全局配置实例 — 各模块统一引用此对象
settings = Settings()
