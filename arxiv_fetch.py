# arxiv_fetch.py
import arxiv, re
from dateutil import tz
from datetime import timedelta

def build_query(cfg):
    # 极简查询，确保API能返回结果
    terms = []

    # 收集前几个最常用的搜索词
    for blk in cfg.get("queries", []):
        if "any" in blk:
            terms.extend(blk["any"])
        if "all" in blk:
            terms.extend(blk["all"])

    # 取前3个术语，去重
    unique_terms = list(set([t.strip() for t in terms]))[:3]

    if not unique_terms:
        return ""

    # 使用最简单的查询格式：all:术语
    term_query = " OR ".join([f'all:"{term}"' for term in unique_terms])

    # 添加主要分类
    cats = cfg.get("categories", [])
    if cats:
        # 只使用主要分类cs.LG
        term_query = f'{term_query} AND cat:cs.LG'

    return term_query


def fetch_window(cfg, since_dt_local, now_local):
    tz_local = tz.gettz(cfg.get("timezone", "America/New_York"))
    q = build_query(cfg)

    # 使用更小的页面大小和结果数量，避免分页问题
    client = arxiv.Client(page_size=50, delay_seconds=2, num_retries=3)
    search = arxiv.Search(
        query=q.strip(), max_results=100,  # 减少到100个结果
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    results = []
    total_checked = 0

    try:
        for r in client.results(search):
            total_checked += 1
            pub_local = r.published.astimezone(tz_local)

            # 检查是否在时间窗口内
            if since_dt_local <= pub_local <= now_local:
                # 过滤排除词
                excludes = [e.lower() for e in cfg.get("exclude", [])]
                title = r.title.lower()
                abstract = (r.summary or '').lower()
                if any(e and (e in title or e in abstract) for e in excludes):
                    continue
                results.append(r)

            # 避免检查太老的论文
            if pub_local < since_dt_local - timedelta(days=7):
                break

    except Exception as e:
        print(f"Warning: Error during fetch: {e}")

    return results


def pack_papers(cfg, papers):
    # 结构化成 JSON 友好格式
    data = []
    max_abs = int(cfg.get("abstract_max_chars", 500))
    for p in papers:
        abs_text = re.sub(r"\s+", " ", (p.summary or "")).strip()
        if len(abs_text) > max_abs:
            abs_text = abs_text[:max_abs] + "…"
        data.append({
            "id": p.get_short_id(),
            "title": p.title.strip().replace("\n", " "),
            "authors": [a.name for a in p.authors],
            "primary_category": p.primary_category,
            "published": p.published.isoformat(),
            "link": p.entry_id if cfg.get("link", "abs") == "abs" else p.pdf_url,
            "abstract": abs_text,
        })
    return data