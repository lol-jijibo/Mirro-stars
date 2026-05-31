"""
Mirro FastAPI 应用入口
负责组装所有路由、配置CORS、启动数据库连接。
通过 uvicorn 启动: uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.models.database import get_db, close_db
from app.api.questions import router as questions_router
from app.api.search import router as search_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时：初始化MySQL数据库连接并自动建表
    关闭时：断开数据库连接
    """
    # 启动时预初始化数据库
    await get_db()
    yield
    # 关闭时清理MySQL连接
    await close_db()


# 创建FastAPI应用实例
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="面向年轻人的AI问题解决平台 — 提问→全网搜索→AI分析→流程图→分步方案",
    lifespan=lifespan,
)

# 配置CORS — 允许前端开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,    # 只允许前端地址访问
    allow_credentials=True,
    allow_methods=["*"],                     # 允许所有HTTP方法
    allow_headers=["*"],                     # 允许所有请求头
)

# 注册业务路由
app.include_router(questions_router)  # /api/questions/*
app.include_router(search_router)     # /api/search/*


@app.get("/")
async def root():
    """根路径 — API健康检查"""
    return {
        "name": "Mirro AI — 问题解决引擎",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
