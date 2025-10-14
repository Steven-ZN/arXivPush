# summarizer.py
import os, requests, time

# 通过 HTTP 调用 Ollama，本地已安装 `ollama` 并拉取 qwen 模型。
# 设置 OLLAMA_KEEP_ALIVE=0，使其在请求完成后立即"休眠/退出"。

PROMPT_TEMPLATE = """
请严格按照以下模板生成「arXiv日报」，必须基于提供的真实论文数据，不能编造任何内容：


---

## 一、今日论文趋势
欢迎来到 **arXiv日报**，先来看看今天的研究热点。

今天 arXiv 上共收录 AI 方向论文 **{total_papers}** 篇，
其中：
- 机器学习 (cs.LG)：{ml_papers} 篇
- 计算机视觉 (cs.CV)：{cv_papers} 篇
- 自然语言处理 (cs.CL)：{nlp_papers} 篇
- 其他（如AI安全、多模态等）：{other_papers} 篇

从关键词来看，今日高频词包括多模态、深度学习、神经网络等；
在模型方向上，轻量化模型和跨模态学习成为主要趋势。

---

## 二、论文速览

**1. {paper1_title}**
作者：{paper1_authors}
主要内容：{paper1_summary}
亮点与评论：{paper1_comment}

**2. {paper2_title}**
作者：{paper2_authors}
主要内容：{paper2_summary}
亮点与评论：{paper2_comment}

**3. {paper3_title}**
作者：{paper3_authors}
主要内容：{paper3_summary}
亮点与评论：{paper3_comment}

（根据实际论文数量继续列出，最多10篇）

---

## 三、值得关注的动向

- **开源项目**：
  {opensource_news}

- **趋势解读**：
  {trend_analysis}

- **会议动向**：
  {conference_news}

---

今天的日报就到这里，{time_period}我们再见～
日报有用记得关注哦，你的鼓励真的很重要～

---

【期别】{period_label}
【时间窗】{since} ~ {now}
【论文条目(JSON 数组)】
{items_json}

重要提示：
1. 必须严格基于真实论文数据，不能编造任何内容
2. 使用纯文本格式，取消所有markdown标记
3. 论文数量根据实际数据填写
4. 如果某类论文数量为0，可以省略该分类
5. 动向部分如果没有具体信息，可以写"暂无特别动向"或基于论文内容进行合理推测
""".strip()


def run_ollama(cfg, period_label, since_str, now_str, items_json):
    host = cfg.get("ollama", {}).get("host", "http://127.0.0.1:11434")
    model = cfg.get("ollama", {}).get("model", "deepseek-r1:latest")
    keep_alive = cfg.get("ollama", {}).get("keep_alive", 0)

    # 解析论文数据，统计分类
    import json
    papers = json.loads(items_json)

    # 统计各类别论文数量
    ml_count = sum(1 for p in papers if 'cs.LG' in p.get('primary_category', ''))
    cv_count = sum(1 for p in papers if 'cs.CV' in p.get('primary_category', ''))
    cl_count = sum(1 for p in papers if 'cs.CL' in p.get('primary_category', ''))
    other_count = len(papers) - ml_count - cv_count - cl_count

    # 生成论文条目文本
    papers_text = ""
    for i, paper in enumerate(papers[:10], 1):  # 最多10篇
        title = paper.get('title', '').replace('\n', ' ')
        authors = ', '.join(paper.get('authors', [])[:3])  # 只显示前3个作者
        if len(paper.get('authors', [])) > 3:
            authors += ' et al.'
        summary = paper.get('abstract', '')[:200] + '...' if len(paper.get('abstract', '')) > 200 else paper.get('abstract', '')

        papers_text += f"""
**{i}. {title}**
作者：{authors}
主要内容：{summary}
亮点与评论：{paper.get('primary_category', '')}分类论文，提出了相关研究方法。

"""

    # 确定时间段
    time_period = "明早10点" if "早报" in period_label else "今晚10点"

    # 填充模板变量
    prompt = PROMPT_TEMPLATE.format(
        total_papers=len(papers),
        ml_papers=ml_count,
        cv_papers=cv_count,
        nlp_papers=cl_count,
        other_papers=other_count,
        paper1_title=papers[0].get('title', '') if len(papers) > 0 else '',
        paper1_authors=', '.join(papers[0].get('authors', [])[:3]) if len(papers) > 0 else '',
        paper1_summary=papers[0].get('abstract', '')[:200] + '...' if len(papers) > 0 and len(papers[0].get('abstract', '')) > 200 else papers[0].get('abstract', '') if len(papers) > 0 else '',
        paper1_comment=papers[0].get('primary_category', '') + '分类研究' if len(papers) > 0 else '',
        paper2_title=papers[1].get('title', '') if len(papers) > 1 else '',
        paper2_authors=', '.join(papers[1].get('authors', [])[:3]) if len(papers) > 1 else '',
        paper2_summary=papers[1].get('abstract', '')[:200] + '...' if len(papers) > 1 and len(papers[1].get('abstract', '')) > 200 else papers[1].get('abstract', '') if len(papers) > 1 else '',
        paper2_comment=papers[1].get('primary_category', '') + '分类研究' if len(papers) > 1 else '',
        paper3_title=papers[2].get('title', '') if len(papers) > 2 else '',
        paper3_authors=', '.join(papers[2].get('authors', [])[:3]) if len(papers) > 2 else '',
        paper3_summary=papers[2].get('abstract', '')[:200] + '...' if len(papers) > 2 and len(papers[2].get('abstract', '')) > 200 else papers[2].get('abstract', '') if len(papers) > 2 else '',
        paper3_comment=papers[2].get('primary_category', '') + '分类研究' if len(papers) > 2 else '',
        opensource_news="暂无特别开源项目动态" if len(papers) < 3 else f"基于{len(papers)}篇论文分析，发现多个值得关注的开源工具",
        trend_analysis=f"本期收录{len(papers)}篇论文，主要集中在机器学习{ml_count}篇、计算机视觉{cv_count}篇等方向" if len(papers) > 0 else "本期论文数量较少",
        conference_news="暂无特别会议动向",
        time_period=time_period,
        period_label=period_label,
        since=since_str,
        now=now_str,
        items_json=items_json
    )

    # 直接调用 /api/generate；设置 keep_alive 控制
    url = f"{host}/api/generate"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "prompt": prompt,
        "options": {
            "num_ctx": 4096,
        },
        "stream": False,
        "keep_alive": keep_alive
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=600)
    resp.raise_for_status()
    out = resp.json().get("response", "").strip()

    # 移除markdown格式，转换为纯文本
    out = out.replace('**', '').replace('## ', '').replace('# ', '').replace('- ', '• ').replace('---', '='*20)

    return out
