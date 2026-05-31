"""
搜索服务模块 — 全网案例聚合
负责通过Tavily Search API搜索互联网上与用户问题相关的案例、教程和资源。
为AI答案提供真实引用来源，增强可信度。
"""
from tavily import TavilyClient
from app.core.config import settings


def _get_client() -> TavilyClient:
    """获取Tavily搜索客户端"""
    return TavilyClient(api_key=settings.TAVILY_API_KEY)


async def search_related_resources(query: str, max_results: int = 5) -> list[dict]:
    """
    根据用户问题搜索全网相关资源
    业务场景：用户提问后，自动搜索知乎、小红书、B站等平台上的相关内容，
    作为解答的参考资料和案例来源。

    返回格式：[{"title": "标题", "url": "链接", "snippet": "摘要"}, ...]
    """
    try:
        client = _get_client()
        # 优化搜索词：加上"经验分享"和"解决方法"提高结果质量
        search_query = f"{query} 经验分享 解决方法"

        response = client.search(
            query=search_query,
            search_depth="basic",        # basic基础搜索，advanced深度搜索（消耗更多配额）
            max_results=max_results,
            include_domains=[],          # 不限制域名，全网搜索
        )

        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")[:200],  # 截取前200字作为摘要
            })
        return results
    except Exception as e:
        # 搜索失败不影响主流程，返回空列表
        # 业务决策：搜索是辅助功能，即使搜索挂了，AI答案仍然可用
        print(f"[搜索服务] 搜索失败，返回空结果: {e}")
        return []
