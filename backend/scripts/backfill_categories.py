"""
数据回填脚本：为缺少分类标签的历史问题补充 AI 分类

背景：早期版本中分类是 SSE 流末尾异步完成的，用户中途关闭页面会导致
category 字段为 NULL / 空字符串 / "分析中..."。此脚本找出这些遗留问题，
调用 classify_question() 逐个补全分类标签。

用法：
    cd backend
    python scripts/backfill_categories.py

安全措施：
    - 每处理一条休眠 0.5s，避免打爆 LLM API 速率限制
    - 分类失败时自动跳过，不会中断整体流程
    - 默认只处理前 100 条（--all 处理全部）
"""
import asyncio
import sys
import os

# 确保 backend 目录在 sys.path 中，以便导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import init_db, close_db, get_db
from app.services.ai_service import classify_question


async def backfill(max_items: int | None = 100, dry_run: bool = False):
    """
    回填缺少分类的问题。

    参数:
        max_items: 最多处理条数，None 表示全部
        dry_run: 仅预览不写入
    """
    print("[DB] 连接数据库...")
    await init_db()

    # 查询缺少分类的问题（NULL / 空串 / 旧占位符）
    async with get_db() as db:
        rows = await db.execute_fetchall(
            """SELECT id, content FROM questions
               WHERE category IS NULL OR category = '' OR category = '分析中...'
               ORDER BY created_at ASC"""
        )

    total = len(rows)
    print(f"[INFO] 找到 {total} 条缺少分类的问题")

    if total == 0:
        print("[OK] 没有需要处理的数据，退出")
        await close_db()
        return

    limit = min(max_items, total) if max_items else total
    print(f"[INFO] 将处理前 {limit} 条" + (" (预览模式，不写入)" if dry_run else ""))

    success = 0
    skip = 0
    fail = 0

    for i, (qid, content) in enumerate(rows[:limit], 1):
        # 截断显示内容
        preview = content[:60] + "…" if len(content) > 60 else content
        print(f"\n[{i}/{limit}] {preview}")

        # 调用 AI 分类
        try:
            category = await classify_question(content)
            print(f"  -> {category}")
        except Exception as e:
            print(f"  [WARN] 分类失败: {e}")
            fail += 1
            continue

        # 验证分类结果有效性
        valid = ["职业发展", "情感关系", "个人成长", "理财规划", "健康生活", "社交技巧", "技术学习", "其他"]
        if category not in valid:
            print(f"  [WARN] 无效分类结果，跳过")
            skip += 1
            continue

        if dry_run:
            success += 1
        else:
            try:
                async with get_db() as db:
                    await db.execute(
                        "UPDATE questions SET category = ? WHERE id = ?",
                        (category, qid)
                    )
                    await db.commit()
                success += 1
            except Exception as e:
                print(f"  [ERR] 写入失败: {e}")
                fail += 1
                continue

        # 避免打爆 API 速率限制
        if i < limit:
            await asyncio.sleep(0.5)

    print(f"\n{'='*40}")
    print(f"[OK] 完成! 成功: {success}  跳过: {skip}  失败: {fail}")
    if dry_run:
        print("[TIP] 这是预览模式，加 --execute 参数才会实际写入")

    await close_db()


if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    all_items = "--all" in sys.argv
    max_items = None if all_items else 100

    if dry_run:
        print("[PREVIEW] 预览模式 -- 仅查看不写入（加 --execute 执行实际更新）")
        print(f"   {'--all' if all_items else '默认处理前100条'}")

    asyncio.run(backfill(max_items=max_items, dry_run=dry_run))
