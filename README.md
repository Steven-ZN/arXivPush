# arXivPush: 基于 Discord 的每日论文推送系统

<div align="center">

[![Language: 中文](https://img.shields.io/badge/Language-中文-blue.svg)](README.md)
[![Language: English](https://img.shields.io/badge/Language-English-green.svg)](README_EN.md)

</div>

<div align="center">
  <h3>自动化的科研信息系统，用于每日从 arXiv 获取最新论文并生成中英学术日报。
系统集成本地 LLM（Ollama）实现论文摘要趋势分析互动问答，通过 Discord 实时推送</h3>
</div>

---

**arXivPush** is an automated research information system that retrieves the latest papers from arXiv every day and generates bilingual (Chinese-English) academic daily reports.
 The system integrates a local LLM (Ollama) for paper summarization, trend analysis, and interactive Q&A, and pushes updates to Discord in real time.
 
## 部分输出示例

**ArxivPush** 系统自动生成的日报示例（由于消息过长，仅展示部分内容）。

![ArxivPush Demo Output](./demo.png)

## 快速部署指南

### 环境要求

  * Python 3.8+
  * Linux (原部署环境Ubuntu 24.04)
  * 内存 ≥ 4GB（推荐 8GB）
  * 硬盘空间 ≥ 10GB

### 外部依赖

* Ollama：本地大语言模型运行环境
* Discord Bot Token：从 Discord Developer Portal 获取
* Discord Channel ID：目标推送频道的唯一 ID



### 安装

#### 克隆与安装依赖

```
git clone <repository-url>
cd arxivpush
pip install -r requirements.txt
```

#### 安装 Ollama 并拉取模型

```
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2.5:7b
ollama serve
```

> 16GB 显存推荐使用 `qwen2.5:7b`，8GB 可使用 `qwen2.5:3b`。

#### 配置 Discord 应用

1. 打开 [Discord Developer Portal](https://discord.com/developers/applications)
2. 创建应用 → 启用 Bot → 获取 Token
3. 启用 “Message Content Intent”
4. 邀请 Bot 至服务器
5. 获取频道 ID（右键频道 → Copy ID）

#### 创建 `.env`

```
DISCORD_BOT_TOKEN=your_discord_bot_token_here
```

#### 配置 `config.yaml`

```
queries:
- any:
  - machine learning
  - deep learning
- all:
  - transformer
  - attention
categories:
- cs.CV
- cs.LG
timezone: America/New_York
report_times:
- '10:00'
- '22:00'
discord_channel_id: your_channel_id_here
ollama:
  model: qwen2.5:7b
  host: http://127.0.0.1:11434
  keep_alive: 0
```

#### 启动服务

```bash
python bot.py
# 或后台运行
nohup python3 bot.py > bot_output.log 2>&1 &
```



## 运行与使用

###  Discord 命令（部分需要手动启用）

| 命令                     | 说明                |
| ------------------------ | ------------------- |
| arxiv-smi                | 查看系统状态        |
| arxiv-rn am / pm         | 立即生成早报 / 晚报 |
| arxiv-p-start            | 启动服务            |
| arxiv-p-stop             | 停止服务            |
| arxiv-p-config get / set | 查看或修改配置      |
| arxiv-p-logs [行数]      | 查看日志            |
| arxiv-help               | 查看帮助            |

### CLI 命令

```
python arxiv-cli.py start     # 启动服务
python arxiv-cli.py rn pm     # 手动生成晚报
python arxiv-cli.py smi       # 查看实时监控
```

### 对话功能

直接在 Discord 频道中输入以 `/` 开头的消息即可与最新日报对话：

```
/这些论文的研究趋势是什么？
/解释第一篇论文的主要创新点
```



## 系统架构

[![](https://mermaid.ink/img/pako:eNqFWG1T4zgS_isqb-19uDOQNw9Mamu3MoS95W5gcgNTdXuGSim2kuiwLZ8kAxmG_36tV8tJCFQR21I_j9qtVr_4JcpYTqJxtOK4XqPb6V2F9N_PP6MrTCt0zsqaVaSSws2cf75MMX-mj0dZQY_rzS8LfvIriJW4ytFnWhF0WUnClzgj9-jo6Feg4CRVP-hmIyQp7x3TJybTBZOOY0pFxniuhlugX5VVS7pKM3053uCysOuq54ZjSVkVooL30EvPOMuIELRaoRmtSQF6ttQwr5C_E5mtzbvNl-reaTbDNeFmWhFcVCuA3-_gbySWJBXq1yH1EFiywitSghV3Qd8kLUTaqF8HuqUl0eNUUiLuOy-zpcqkWDFO5bp0InpGE39qaJH_qyF8k-pfM0C4XmKh7uf_U-PtdniAxv84B9UVOxHob-ifZPMEmyN-oBuCuTPTsXnQlJPZJTovqHnJQONPWGkU2P8zW9HMCRgCo7AS_MxYne6BsFovordl_kSrnD21ijug0fsSvE_7A-ofXf9AU5I3dTpt6oJmajOmRJJMTRtDYEHmNEe5ktISypEcs8Ya36AF0IIbg29X0j6CapqEPGdFkxP0YI3k8UZME0yyrCmbQnmI2UM_wMyWNBWF_ZjXalKgnGZ77eg3XJ0IyVkh3rDC-ZpkD-gW8xWRsGvmRg--XBOSo1I5oFnsN72-1BJjNOi9OsoAZEj_JEB18VzDUbduYB5Q4AcVsM81-1_R0K5w_ybjNQOPYlx-JaIppEjVPVps0KxZFFSsQdEpmMzjw7W7TuMdqiXTAjOcPaQ1_FjLah3_cfPlGi0ZL7GUsIldQ08uD0ULxWdOewMhj9Pv4BXC37ojDBxu3riijxm7Oxou59_CM7ZvOblM9yD0ciNrZ6Qca6GEuocDENraBt__gb4UBS5xPzVXpM8uLgrUP4QbONxgBzc4hBs63HAHNzyEGzncaAc3OoRLHC7ZwSWHttq6jZu3NjJJpSC46qe35Fmae2f5TD3MJYzfd3GDFjfo4rYEh63g8KDgqBUcHRRMWsFkR7CTGE0wmwhBykWx8blJv6yJWmaKpNuy9x3hQUe4MzV8e2r09lSyNeUm3YievuWkyv9OqlTfoEmFi42gAsGQzQAmBxOoGnJrG-0GbTiyDCZSMCGtN6RqQ-e1eWD-VCuJwGG2MnN3cjdwtPR6uYtnyXEmU3s1mV2gJWclug39yQko0BWB-JnqX_QEaQB94RQCCy5UmMQeYgQU4Csp2SOB7CdSc4t8JmyjcitkNKtEwwmUcg8iNfcI83_TR6SHWr1aMZMidTz90si6kal5gASodDNjXXPdQN6DosjWhD5hBhxtTWVl0xmkXJabmsqOeW1CQfPm-EnZBOoxPXbyJ_wdXV0dTafzydXJ7OpEbynHTzYxHP9XBJl_l47UkFneY9NC8-_rOamOy_xtNnCEsn6PrdZC80wdvWd5LAOf2CE8X-P36DIQOdneBCwbEdSne2vaRuiitjEm0lxfm0qqKtVMd9RqhD2ckCjhHNhqxz2aF2tUZt-ye6hWBtNNoU5R1z2gNTBaGQFIvZOZvzcNAYdk64daxdyIyRNTTIsNuoLWB-pDda9gqfq5hfO0slz93rjXQ39B_TO4vkX1B2u45zIPe8kuHlVhrQS67-q6HtU0rUzU2n5bKwJJLHXScN8Wqe4FrPCKCKmiYg0BZ57rR62BDYvEurLHt0p3CTy_GwiVAX-rKlKk9goRRwjwoa1uBXpFZFtDgX4v2FPQRDr34vK8zG1HKdSja5ygELwh_JFmQavlYawOUbY7UMMHMMo3O2vBs3EaXY9u-bLDGWu1OHPGNQ7OTQPhbcueHngdgPyxQde6c-mkYdM771aBfmkT-_VqamdXdifnu7q0ua-N7tc7DD5PuIG2_-2odsE54-gP0K4I1NrqNFRxpQVVb6CuWp6kATg4iYGENa_kmxf9C5aAsIJ-QcPfXlsTSNeP6uZjp94PBFQvAc2lXiGFGyQZCgLXVozRgQXObUUhaoZvZ0-dnUl3BNssa4ZM_J19S-EffRNhUgolriDJQi9uLgfkTJ2iXdKVrzas6rG9GB-TbLhuY5R36m7d13406R5LPaMp1YcAaP1T22vZR-1qrs2F0Jj5bwT3ezhuaakygP6ecUN0q2UYTAMPeJVEvrPOxxSPnlzajz6qmQrRJcTaAsBrCHD7gC5EGbQLmR2KzIYt0IA9kC3XUGWDNguUlBWT2ky-K8gKLMSULE2b5Qq6JS2K8U-kv0yWJBbQlz-Q8U-9fnL6cWEfj55oLtfjQf28w4Rpl2Y5JMky8TQj3B-dZe_T2OzvdDlbJuTMk_QXCRn03ifJzFcFp8kSdOl5EvIh6ff2kXRo2jMaB-1-HLbusf6wEpvPI3H7aaRj1D2kk8vYdmX2OrDXob2O7DWJfWnvrdvlCyuo2NaKsQm4sanOYlVTxeYAxa5-cVaO4mjFaR6NJW9IHJUE6lb1GL2oZe4iuYZ66i4aw21Olhj6yrvornoFGFjhP4yVDslZs1pH4yUuBDw1dQ5qTSmGUqAVgTchXAfHaHx6qimi8Uv0HI2HyfHZadLr9c76yccPp6dncbSJxv3hx-PBWfKx9-G0N0p6SX_wGkff9aI9Jf_6f7R4Ljs?type=png)](https://mermaid.live/edit#pako:eNqFWG1T4zgS_isqb-19uDOQNw9Mamu3MoS95W5gcgNTdXuGSim2kuiwLZ8kAxmG_36tV8tJCFQR21I_j9qtVr_4JcpYTqJxtOK4XqPb6V2F9N_PP6MrTCt0zsqaVaSSws2cf75MMX-mj0dZQY_rzS8LfvIriJW4ytFnWhF0WUnClzgj9-jo6Feg4CRVP-hmIyQp7x3TJybTBZOOY0pFxniuhlugX5VVS7pKM3053uCysOuq54ZjSVkVooL30EvPOMuIELRaoRmtSQF6ttQwr5C_E5mtzbvNl-reaTbDNeFmWhFcVCuA3-_gbySWJBXq1yH1EFiywitSghV3Qd8kLUTaqF8HuqUl0eNUUiLuOy-zpcqkWDFO5bp0InpGE39qaJH_qyF8k-pfM0C4XmKh7uf_U-PtdniAxv84B9UVOxHob-ifZPMEmyN-oBuCuTPTsXnQlJPZJTovqHnJQONPWGkU2P8zW9HMCRgCo7AS_MxYne6BsFovordl_kSrnD21ijug0fsSvE_7A-ofXf9AU5I3dTpt6oJmajOmRJJMTRtDYEHmNEe5ktISypEcs8Ya36AF0IIbg29X0j6CapqEPGdFkxP0YI3k8UZME0yyrCmbQnmI2UM_wMyWNBWF_ZjXalKgnGZ77eg3XJ0IyVkh3rDC-ZpkD-gW8xWRsGvmRg--XBOSo1I5oFnsN72-1BJjNOi9OsoAZEj_JEB18VzDUbduYB5Q4AcVsM81-1_R0K5w_ybjNQOPYlx-JaIppEjVPVps0KxZFFSsQdEpmMzjw7W7TuMdqiXTAjOcPaQ1_FjLah3_cfPlGi0ZL7GUsIldQ08uD0ULxWdOewMhj9Pv4BXC37ojDBxu3riijxm7Oxou59_CM7ZvOblM9yD0ciNrZ6Qca6GEuocDENraBt__gb4UBS5xPzVXpM8uLgrUP4QbONxgBzc4hBs63HAHNzyEGzncaAc3OoRLHC7ZwSWHttq6jZu3NjJJpSC46qe35Fmae2f5TD3MJYzfd3GDFjfo4rYEh63g8KDgqBUcHRRMWsFkR7CTGE0wmwhBykWx8blJv6yJWmaKpNuy9x3hQUe4MzV8e2r09lSyNeUm3YievuWkyv9OqlTfoEmFi42gAsGQzQAmBxOoGnJrG-0GbTiyDCZSMCGtN6RqQ-e1eWD-VCuJwGG2MnN3cjdwtPR6uYtnyXEmU3s1mV2gJWclug39yQko0BWB-JnqX_QEaQB94RQCCy5UmMQeYgQU4Csp2SOB7CdSc4t8JmyjcitkNKtEwwmUcg8iNfcI83_TR6SHWr1aMZMidTz90si6kal5gASodDNjXXPdQN6DosjWhD5hBhxtTWVl0xmkXJabmsqOeW1CQfPm-EnZBOoxPXbyJ_wdXV0dTafzydXJ7OpEbynHTzYxHP9XBJl_l47UkFneY9NC8-_rOamOy_xtNnCEsn6PrdZC80wdvWd5LAOf2CE8X-P36DIQOdneBCwbEdSne2vaRuiitjEm0lxfm0qqKtVMd9RqhD2ckCjhHNhqxz2aF2tUZt-ye6hWBtNNoU5R1z2gNTBaGQFIvZOZvzcNAYdk64daxdyIyRNTTIsNuoLWB-pDda9gqfq5hfO0slz93rjXQ39B_TO4vkX1B2u45zIPe8kuHlVhrQS67-q6HtU0rUzU2n5bKwJJLHXScN8Wqe4FrPCKCKmiYg0BZ57rR62BDYvEurLHt0p3CTy_GwiVAX-rKlKk9goRRwjwoa1uBXpFZFtDgX4v2FPQRDr34vK8zG1HKdSja5ygELwh_JFmQavlYawOUbY7UMMHMMo3O2vBs3EaXY9u-bLDGWu1OHPGNQ7OTQPhbcueHngdgPyxQde6c-mkYdM771aBfmkT-_VqamdXdifnu7q0ua-N7tc7DD5PuIG2_-2odsE54-gP0K4I1NrqNFRxpQVVb6CuWp6kATg4iYGENa_kmxf9C5aAsIJ-QcPfXlsTSNeP6uZjp94PBFQvAc2lXiGFGyQZCgLXVozRgQXObUUhaoZvZ0-dnUl3BNssa4ZM_J19S-EffRNhUgolriDJQi9uLgfkTJ2iXdKVrzas6rG9GB-TbLhuY5R36m7d13406R5LPaMp1YcAaP1T22vZR-1qrs2F0Jj5bwT3ezhuaakygP6ecUN0q2UYTAMPeJVEvrPOxxSPnlzajz6qmQrRJcTaAsBrCHD7gC5EGbQLmR2KzIYt0IA9kC3XUGWDNguUlBWT2ky-K8gKLMSULE2b5Qq6JS2K8U-kv0yWJBbQlz-Q8U-9fnL6cWEfj55oLtfjQf28w4Rpl2Y5JMky8TQj3B-dZe_T2OzvdDlbJuTMk_QXCRn03ifJzFcFp8kSdOl5EvIh6ff2kXRo2jMaB-1-HLbusf6wEpvPI3H7aaRj1D2kk8vYdmX2OrDXob2O7DWJfWnvrdvlCyuo2NaKsQm4sanOYlVTxeYAxa5-cVaO4mjFaR6NJW9IHJUE6lb1GL2oZe4iuYZ66i4aw21Olhj6yrvornoFGFjhP4yVDslZs1pH4yUuBDw1dQ5qTSmGUqAVgTchXAfHaHx6qimi8Uv0HI2HyfHZadLr9c76yccPp6dncbSJxv3hx-PBWfKx9-G0N0p6SX_wGkff9aI9Jf_6f7R4Ljs)

### 模块说明

* **bot.py**：主入口，负责消息监听、命令解析、任务调度
* **arxiv_fetch.py**：从 arXiv 拉取论文并过滤
* **summarizer.py**：调用 Ollama 模型生成摘要与趋势分析
* **text_processor.py**：格式化文本、生成 APA6 引用
* **state.py**：持久化管理，存储所有周期数据



## 算法与实现细节

### 调度算法

```python
def start_scheduler():
    if report_mode == "hourly":
        scheduler.add_job(post_digest, CronTrigger(minute=0))
    else:
        for t in report_times:
            hour, minute = map(int, t.split(":"))
            scheduler.add_job(post_digest, CronTrigger(hour=hour, minute=minute))
```

### 查询构建算法

```python
def build_query(queries, categories, exclude_keywords):
    parts = []
    for query in queries:
        if 'any' in query:
            parts.append(f"({' OR '.join(query['any'])})")
        if 'all' in query:
            parts.append(f"({' AND '.join(query['all'])})")
    if categories:
        cat = " OR ".join([f"cat:{c}" for c in categories])
        parts.append(f"({cat})")
    return " AND ".join(parts)
```

### 批处理摘要生成

```python
def run_ollama(cfg, period_label, since_str, now_str, items_json):
    for i in range(0, len(items_json), 4):
        batch = items_json[i:i+4]
        prompt = build_batch_prompt(batch, i+1)
        result = call_ollama(prompt, timeout=300)
        all_content += reconstruct_with_numbering(result, batch, i+1)
    trend = call_ollama(build_trend_prompt(all_content))
    return post_process_with_links(all_content, trend, items_json)
```

### 文本解析与APA6生成

```python
def generate_apa6_citation(paper, index):
    arxiv_id = paper['id'].split('v')[0]
    authors = ', '.join(paper['authors'][:3]) + (' et al' if len(paper['authors']) > 3 else '')
    title = paper['title']
    year = paper['published'][:4]
    link = f"https://arxiv.org/abs/{arxiv_id}"
    return f"[{index}] {authors} ({year}). {title}. arXiv ID: {arxiv_id}. {link}"
```


## 系统流程

### 1. 定时推送

```mermaid
graph TD
    A[调度器触发] --> B[arXiv 数据获取]
    B --> C[论文过滤与清洗]
    C --> D[LLM 批处理摘要]
    D --> E[趋势分析生成]
    E --> F[APA6 格式化]
    F --> G[Discord 推送]
    G --> H[状态持久化]
```

### 智能对话

```mermaid
graph TD
    A[用户输入消息 / 问题] --> B[检测活跃周期]
    B --> C[加载对应日报上下文]
    C --> D[构建 LLM 提示词]
    D --> E[调用 Ollama 生成回复]
    E --> F[发送到 Discord 并记录日志]
```



## 性能与优化

* **批处理机制**：防止 LLM 上下文溢出
* **内存控制**：`keep_alive=0` 自动释放显存
* **并行数据抓取**：异步请求 arXiv API
* **分段推送**：自动切分长消息，保证 Discord 可读性
* **缓存策略**：避免重复拉取与生成，提高执行效率


## 配置与扩展

* 支持多模型：`DeepSeek`、`Qwen`、`Mistral`
* 支持自定义关键词逻辑（AND / OR 混合）
* 支持多时区与多周期
* 报告模板可定制（精简版、会议追踪版、研究主题版）



## 版本更新

### v1.2.0（2025-10-12）

* 实现智能批处理摘要生成
* 新增 APA6 引用格式模块
* 完整的趋势分析与后处理架构
* 优化 Ollama 内存管理与日志系统

### v1.1.0（2025-10-11）

* 增强 CLI 与生产环境部署
* 改进日志与状态监控模块

### v1.0.0（2025-10-10）

* 初始版本：实现每日推送、摘要生成与智能对话

---

## 十、许可证

本项目遵循 **MIT License**，允许自由使用、修改与分发，但须保留原作者信息与版权声明。
