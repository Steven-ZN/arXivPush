# arxiv_fetch.py
import arxiv, re
from dateutil.tz import gettz
from datetime import timedelta

def build_query(cfg):
    # 构建更宽松的搜索查询

    # 添加主要分类（这是最重要的）
    cats = cfg.get("categories", [])
    if cats:
        # 使用所有配置的分类
        cat_query = " OR ".join([f'cat:{cat}' for cat in cats])
        base_query = f'({cat_query})'
    else:
        base_query = ""

    # 只添加1-2个最常用的搜索词，避免查询过于复杂
    terms = []
    for blk in cfg.get("queries", []):
        if "any" in blk:
            terms.extend(blk["any"])
        if "all" in blk:
            terms.extend(blk["all"])

    # 选择最常用的1-2个术语
    common_terms = ["machine learning", "deep learning", "neural network"]
    selected_terms = []
    for term in common_terms:
        if term in [t.strip() for t in terms]:
            selected_terms.append(term)
            if len(selected_terms) >= 2:
                break

    # 简化查询：只使用分类，不过滤术语，以获得更多论文
    if base_query:
        return base_query
    else:
        # 最后备选：只搜索最新论文
        return ""


def iterative_time_aware_search(cfg, target=20, max_days=7):
    """
    时间感知的迭代搜索架构
    优先抓取最新论文，动态扩展时间窗口直到满足条件

    Args:
        cfg: 配置字典
        target: 目标论文数量
        max_days: 最大搜索天数

    Returns:
        list: 按发布时间降序排列的论文列表
    """
    from datetime import datetime, timedelta
    from dateutil.tz import gettz

    tz_local = gettz(cfg.get("timezone", "America/New_York"))
    current_date = datetime.now(tz_local).date()

    collected = []
    seen_ids = set()
    time_window = 1

    # 获取搜索配置
    cats = cfg.get("categories", ["cs.AI", "cs.LG", "cs.CL", "cs.CV"])
    excludes = [e.lower() for e in cfg.get("exclude", [])]

    print(f"🎯 启动时间感知迭代搜索")
    print(f"📅 当前日期: {current_date}")
    print(f"🎯 目标论文: {target} 篇")
    print(f"🔍 最大搜索范围: {max_days} 天")
    print("=" * 60)

    while len(collected) < target and time_window <= max_days:
        # 计算当前搜索窗口
        end_date = current_date - timedelta(days=time_window-1)
        start_date = current_date - timedelta(days=time_window)

        print(f"🔍 [{time_window}/{max_days}] 搜索窗口: {start_date} ~ {end_date}")

        try:
            # 构建时间窗口查询
            cat_query = " OR ".join([f'cat:{cat}' for cat in cats])

            # 使用arxiv API的时间过滤
            search = arxiv.Search(
                query=cat_query,
                max_results=100,  # 每次搜索更多以确保有足够的选择
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )

            # 获取结果并过滤
            batch_new_papers = []
            for r in arxiv.Client().results(search):
                # 转换为本地时区
                pub_local = r.published.astimezone(tz_local)
                pub_date = pub_local.date()

                # 检查是否在当前搜索窗口内
                if not (start_date <= pub_date <= end_date):
                    continue

                # 去重（避免不同版本的同一论文）
                base_id = r.get_short_id().split('v')[0]
                if base_id in seen_ids:
                    continue
                seen_ids.add(base_id)

                # 过滤排除词
                title = r.title.lower()
                abstract = (r.summary or '').lower()
                if any(e and (e in title or e in abstract) for e in excludes):
                    continue

                batch_new_papers.append(r)
                print(f"📄 找到论文: {r.get_short_id()} - {r.title[:50]}...")

            # 添加到收集列表
            collected.extend(batch_new_papers)

            print(f"✅ 窗口 {time_window}: 新增 {len(batch_new_papers)} 篇, 累计 {len(collected)} 篇")

            # 检查是否达到目标
            if len(collected) >= target:
                print(f"🎉 已达到目标 {target} 篇论文!")
                break

        except Exception as e:
            print(f"❌ 窗口 {time_window} 搜索失败: {e}")
            # 继续下一个窗口，不中断整个搜索过程

        # 动态扩展时间窗口
        time_window += 1

        # 防止过于频繁的API调用
        import time
        time.sleep(0.5)

    # 最终排序和截取
    collected.sort(key=lambda x: x.published, reverse=True)
    final_results = collected[:target]

    print("\n" + "=" * 60)
    print("📊 迭代搜索完成!")
    print(f"   - 搜索窗口数: {time_window - 1}")
    print(f"   - 总论文数: {len(collected)}")
    print(f"   - 最终选取: {len(final_results)} 篇")

    if len(final_results) < target:
        print(f"   ⚠️  未达到目标，只找到 {len(final_results)} 篇论文")
    else:
        print(f"   ✅ 成功达到目标 {target} 篇论文")

    # 显示最新论文的发布时间范围
    if final_results:
        latest = final_results[0].published.astimezone(tz_local)
        oldest = final_results[-1].published.astimezone(tz_local)
        print(f"   📅 时间范围: {oldest.strftime('%Y-%m-%d')} ~ {latest.strftime('%Y-%m-%d')}")

    return final_results


def fetch_window(cfg, since_dt_local, now_local):
    """
    兼容性包装器：使用新的时间感知迭代搜索
    """
    max_items = cfg.get("digest_max_items", 20)

    # 使用新的时间感知迭代搜索
    print(f"🚀 使用时间感知迭代搜索 (替代传统搜索)")

    try:
        results = iterative_time_aware_search(
            cfg=cfg,
            target=max_items,
            max_days=7
        )
        return results
    except Exception as e:
        print(f"❌ 时间感知搜索失败，回退到传统搜索: {e}")

        # 回退到简化的传统搜索
        return fallback_search(cfg, max_items)


def fallback_search(cfg, max_items):
    """
    简化的回退搜索方案
    """
    from datetime import datetime, timedelta
    from dateutil.tz import gettz

    tz_local = gettz(cfg.get("timezone", "America/New_York"))

    print(f"🔄 执行回退搜索方案...")

    search = arxiv.Search(
        query="cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV",
        max_results=max_items,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    try:
        filtered_papers = []
        unique_ids = set()

        for r in arxiv.Client().results(search):
            paper_id = r.get_short_id()
            base_id = paper_id.split('v')[0]

            if base_id in unique_ids:
                continue
            unique_ids.add(base_id)

            # 过滤排除词
            excludes = [e.lower() for e in cfg.get("exclude", [])]
            title = r.title.lower()
            abstract = (r.summary or '').lower()
            if any(e and (e in title or e in abstract) for e in excludes):
                continue

            filtered_papers.append(r)
            if len(filtered_papers) >= max_items:
                break

        print(f"✅ 回退搜索完成: {len(filtered_papers)} 篇论文")
        return filtered_papers

    except Exception as e:
        print(f"❌ 回退搜索也失败: {e}")
        return []

def load_pushed_papers():
    """加载已推送的论文ID"""
    import os
    import json

    pushed_file = "pushed_papers.json"
    if os.path.exists(pushed_file):
        try:
            with open(pushed_file, "r") as f:
                data = json.load(f)
                return set(data.get("papers", []))
        except:
            return set()
    return set()

def save_pushed_papers(paper_ids):
    """保存已推送的论文ID"""
    import os
    import json

    pushed_file = "pushed_papers.json"
    existing_ids = load_pushed_papers()
    all_ids = existing_ids.union(paper_ids)

    try:
        with open(pushed_file, "w") as f:
            json.dump({"papers": list(all_ids)}, f)
        print(f"💾 已保存 {len(paper_ids)} 个新论文ID到推送记录")
    except Exception as e:
        print(f"⚠️ 保存推送记录失败: {e}")

def mark_papers_as_pushed(papers):
    """标记论文为已推送"""
    paper_ids = [p.get_short_id() for p in papers]
    save_pushed_papers(paper_ids)


def pack_papers(cfg, papers):
    # 结构化成 JSON 友好格式， papers已经在fetch_window中过去重
    data = []
    max_abs = int(cfg.get("abstract_max_chars", 500))

    for p in papers:
        paper_id = p.get_short_id()
        abs_text = re.sub(r"\s+", " ", (p.summary or "")).strip()
        if len(abs_text) > max_abs:
            abs_text = abs_text[:max_abs] + "…"

        # 确保有正确的arXiv链接
        arxiv_id = paper_id.split('v')[0]  # 去掉版本号
        arxiv_link = f"https://arxiv.org/abs/{arxiv_id}"

        data.append({
            "id": paper_id,
            "title": p.title.strip().replace("\n", " "),
            "authors": [a.name for a in p.authors],
            "primary_category": p.primary_category,
            "published": p.published.isoformat(),
            "link": arxiv_link,  # 统一使用arxiv链接
            "abstract": abs_text,
        })

    print(f"📊 论文数量: {len(data)}")
    return data