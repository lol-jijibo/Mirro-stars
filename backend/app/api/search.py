"""
搜索API路由 — 独立搜索接口
提供手动搜索功能，用户可以在答案页点击"搜索更多案例"进行额外搜索。
与ai_service中自动触发的搜索不同，这是用户主动发起的搜索。
"""
from fastapi import APIRouter
from app.models.schemas import SearchRequest, SearchResult
from app.services.search_service import search_related_resources

router = APIRouter(prefix="/api/search", tags=["全网搜索"])


@router.post("")
async def search_web(body: SearchRequest) -> dict:
    """
    手动搜索全网相关案例
    业务场景：用户看完AI答案后，想查看更多真实案例或教程时手动触发。
    返回带有标题、链接和摘要的搜索结果列表。
    """
    results = await search_related_resources(body.query, body.max_results)

    return {
        "query": body.query,
        "results": [
            SearchResult(title=r["title"], url=r["url"], snippet=r["snippet"])
            for r in results
        ]
    }
