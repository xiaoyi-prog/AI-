#!/usr/bin/env python3
"""
Market Data Summary Script
每个工作日汇总沪深300、恒生指数、标普500最近一个完整交易日的公开行情。

Usage: python market_summary.py <result_mode>
  result_mode: display_only (default)

Calendar script_args: ["display_only"]
"""

import sys
import os
import json
import asyncio
import re
from datetime import datetime, timedelta, timezone
from codeact_sdk import CodeActSDK

sdk = CodeActSDK()

# ── Tool schema versions (from get_codeact_tool_schemas) ──
SEARCH_VER = "v1_5ac1b0eba8c26f2a"
FETCH_VER = "v1_2c8d0580b3f93a58"

# Beijing timezone
BJT = timezone(timedelta(hours=8))


def recent_publish_time(days: int = 3) -> dict:
    """Generate publish_time filter for last N days in RFC3339."""
    now = datetime.now(BJT)
    start = now - timedelta(days=days)
    return {
        "start": start.strftime("%Y-%m-%dT00:00:00+08:00"),
        "end": now.strftime("%Y-%m-%dT23:59:59+08:00"),
    }


async def search_market_data(index_name: str, query_hint: str) -> dict:
    """Search for latest market data for a given index."""
    print(f"[搜索] {index_name}: {query_hint}")
    result = await sdk.call_tool(
        "codeact_search_web",
        {
            "query": query_hint,
            "response_length": "medium",
            "publish_time": recent_publish_time(3),
        },
        schema_version=SEARCH_VER,
    )
    if not result.get("is_success"):
        print(f"[警告] 搜索 {index_name} 失败: {result.get('error', 'unknown')}")
        return {"index": index_name, "status": "search_failed", "results": []}

    results = result.get("results", [])
    if not results:
        return {"index": index_name, "status": "no_results", "results": []}

    return {"index": index_name, "status": "ok", "results": results[:3]}


async def fetch_page(url: str) -> dict:
    """Fetch a single web page."""
    return await sdk.call_tool(
        "codeact_fetch_web",
        {"url": url},
        schema_version=FETCH_VER,
    )


async def fetch_top_results(search_result: dict) -> str:
    """Fetch top search result pages and concatenate content."""
    if search_result["status"] != "ok":
        return ""

    results = search_result.get("results", [])
    if not results:
        return ""

    # Fetch up to 2 pages concurrently
    tasks = [fetch_page(r["url"]) for r in results[:2]]
    fetched = await asyncio.gather(*tasks, return_exceptions=True)

    combined = []
    for i, f in enumerate(fetched):
        if isinstance(f, Exception):
            print(f"[警告] fetch {results[i]['url']} 异常: {f}")
            continue
        if f.get("is_success") and f.get("content"):
            title = f.get("title", results[i].get("title", ""))
            content = f["content"][:8000]
            combined.append(f"=== {title} ===\n{content}")

    return "\n\n".join(combined)


async def extract_market_info(index_name: str, page_content: str, snippets: str) -> dict:
    """Use LLM to extract structured market data."""
    fallback = {
        "index": index_name, "status": "数据缺失",
        "trading_date": None, "close_price": None, "change_pct": None, "source": "",
    }

    # Combine snippets and content for the prompt
    context_parts = []
    if snippets:
        context_parts.append(f"搜索摘要：\n{snippets}")
    if page_content:
        context_parts.append(f"页面内容：\n{page_content[:6000]}")

    if not context_parts:
        return fallback

    context = "\n\n".join(context_parts)

    prompt = f"""请从以下内容中提取{index_name}最近一个完整交易日的行情数据。

要求：
1. 提取收盘点位（数值）和涨跌幅（百分比数值，如 -1.5 表示跌1.5%）
2. 确定数据对应的交易日期（YYYY-MM-DD格式）
3. 如果市场休市，status 填 "休市"
4. 如果无法提取，status 填 "数据缺失"
5. source 填数据来源网站名称

{context}

严格返回以下JSON格式，不要包含其他文字：
{{"trading_date": "YYYY-MM-DD", "close_price": 数值或null, "change_pct": 数值或null, "status": "正常或休市或数据缺失", "source": "来源名称"}}"""

    try:
        response = await sdk.call_llm(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        # call_llm returns a string
        content = response if isinstance(response, str) else str(response)
        json_match = re.search(r'\{[^{}]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            data["index"] = index_name
            return data
        return fallback
    except Exception as e:
        print(f"[错误] LLM提取 {index_name} 失败: {e}")
        return fallback


async def search_market_events() -> list:
    """Search for notable market events of the day."""
    print("[搜索] 当日市场值得关注事件")
    queries = [
        "今日股市 财经要闻 重要事件",
        "A股 港股 市场动态 今天",
        "stock market news today S&P 500",
    ]
    pt = recent_publish_time(1)

    tasks = [
        sdk.call_tool(
            "codeact_search_web",
            {"query": q, "response_length": "short", "publish_time": pt},
            schema_version=SEARCH_VER,
        )
        for q in queries
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_events = []
    for r in results:
        if isinstance(r, Exception):
            print(f"[警告] 事件搜索异常: {r}")
            continue
        if not r.get("is_success"):
            continue
        for item in r.get("results", [])[:5]:
            all_events.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("url", ""),
            })

    return all_events


async def summarize_events(events: list) -> list:
    """Use LLM to pick top 3 events."""
    if not events:
        return []

    events_text = "\n".join(
        f"{i+1}. {e['title']} — {e['snippet'][:200]}" for i, e in enumerate(events[:15])
    )

    prompt = f"""从以下财经事件中筛选最值得关注的3条（不超过3条）。
标准：对市场影响大、政策变化、重要数据优先；排除广告软文；客观陈述。

事件列表：
{events_text}

严格返回JSON数组：
[{{"event": "简短描述", "source": "来源名称"}}]
只返回JSON，不要其他文字。"""

    try:
        response = await sdk.call_llm(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        content = response if isinstance(response, str) else str(response)
        array_match = re.search(r'\[.*\]', content, re.DOTALL)
        if array_match:
            return json.loads(array_match.group())
        return []
    except Exception as e:
        print(f"[错误] 事件总结失败: {e}")
        return []


def format_summary(trading_date: str, market_data: list, events: list, sources: list) -> str:
    """Format the final market summary."""
    lines = [f"📊 市场数据摘要 | {trading_date}", ""]

    for m in market_data:
        name = m["index"]
        status = m.get("status", "")
        if status == "休市":
            lines.append(f"【{name}】休市")
        elif status == "数据缺失" or m.get("close_price") is None:
            lines.append(f"【{name}】数据暂缺")
        else:
            try:
                close_f = float(m["close_price"])
                change_f = float(m["change_pct"]) if m.get("change_pct") is not None else 0.0
                sign = "+" if change_f >= 0 else ""
                lines.append(f"【{name}】收盘 {close_f:,.2f} | {sign}{change_f:.2f}%")
            except (ValueError, TypeError):
                lines.append(f"【{name}】收盘 {m.get('close_price', 'N/A')} | {m.get('change_pct', 'N/A')}%")

    lines.append("")
    lines.append("📰 当日值得关注：")
    if events:
        for i, e in enumerate(events[:3], 1):
            lines.append(f"{i}. {e.get('event', '暂无')} — {e.get('source', '网络')}")
    else:
        lines.append("暂无值得关注事件")

    lines.append("")
    # Deduplicate sources while preserving order
    seen = set()
    unique_sources = []
    for s in sources:
        if s and s not in seen:
            seen.add(s)
            unique_sources.append(s)
    lines.append(f"数据来源：{'、'.join(unique_sources) if unique_sources else '公开互联网信息'}")

    return "\n".join(lines)


async def main():
    result_mode = sys.argv[1] if len(sys.argv) > 1 else "display_only"
    print(f"[启动] result_mode={result_mode}")

    try:
        # ── Step 1: Search for market data for each index (concurrent) ──
        index_configs = [
            ("沪深 300", "沪深300指数 收盘 点位 涨跌幅 行情"),
            ("恒生指数", "恒生指数 收盘 点位 涨跌幅 行情"),
            ("标普 500", "S&P 500 index close price change percent"),
        ]

        search_tasks = [search_market_data(name, q) for name, q in index_configs]
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Normalize exceptions
        processed = []
        for i, r in enumerate(search_results):
            if isinstance(r, Exception):
                print(f"[错误] 搜索 {index_configs[i][0]} 异常: {r}")
                processed.append({"index": index_configs[i][0], "status": "search_failed", "results": []})
            else:
                processed.append(r)

        # ── Step 2: Build snippets map + fetch pages (concurrent) ──
        snippets_map = {}
        fetch_tasks = []
        for sr in processed:
            snippets_map[sr["index"]] = ""
            if sr.get("results"):
                snippets_map[sr["index"]] = "\n".join(
                    f"- {r.get('title','')}: {r.get('snippet','')}" for r in sr["results"]
                )
            fetch_tasks.append(fetch_top_results(sr))

        page_contents = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # ── Step 3: Extract structured data with LLM (concurrent) ──
        extract_tasks = []
        for i, pc in enumerate(page_contents):
            name = index_configs[i][0]
            content = pc if not isinstance(pc, Exception) else ""
            extract_tasks.append(extract_market_info(name, content, snippets_map.get(name, "")))

        market_data = await asyncio.gather(*extract_tasks, return_exceptions=True)

        # Normalize exceptions
        final_data = []
        for i, md in enumerate(market_data):
            if isinstance(md, Exception):
                print(f"[错误] 提取 {index_configs[i][0]} 异常: {md}")
                final_data.append({
                    "index": index_configs[i][0], "status": "数据缺失",
                    "trading_date": None, "close_price": None, "change_pct": None, "source": "",
                })
            else:
                final_data.append(md)

        # ── Step 4: Search + summarize events (sequential) ──
        raw_events = await search_market_events()
        events = await summarize_events(raw_events)

        # ── Step 5: Determine trading date ──
        trading_dates = [m.get("trading_date") for m in final_data if m.get("trading_date")]
        if trading_dates:
            trading_date = max(set(trading_dates), key=trading_dates.count)
        else:
            trading_date = datetime.now(BJT).strftime("%Y-%m-%d")

        # ── Step 6: Collect sources ──
        sources = [m.get("source", "") for m in final_data if m.get("source")]

        # ── Step 7: Format and submit ──
        summary = format_summary(trading_date, final_data, events, sources)

        print(f"\n{'='*40}")
        print(summary)
        print(f"{'='*40}")

        await sdk.submit_result(
            result_mode=result_mode,
            status="success",
            message=summary,
            data={
                "trading_date": trading_date,
                "market_data": final_data,
                "events": events,
            },
        )
        print("[完成] 结果已提交")

    except Exception as e:
        print(f"[致命错误] {e}")
        import traceback
        traceback.print_exc()
        try:
            await sdk.submit_result(
                result_mode="notify",
                status="error",
                message=f"市场数据汇总脚本执行失败：{str(e)[:200]}",
            )
        except Exception as e2:
            print(f"[致命错误] submit_result 也失败: {e2}")


if __name__ == "__main__":
    asyncio.run(main())
