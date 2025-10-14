# bot.py
import os, json, yaml, asyncio, psutil, subprocess, sys, time
from datetime import datetime
from dotenv import load_dotenv
from discord.ext import commands
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dateutil import tz
import logging

from utils import now_in_tz, last_window_start, fmt_period
from arxiv_fetch import fetch_window, pack_papers
from summarizer import run_ollama
from state import PeriodState, latest_active_period

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arxivpush.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="arxiv-", intents=intents)  # 改为 arxiv- 前缀

with open("config.yaml", "r", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

TZNAME = CFG.get("timezone", "America/New_York")
CHANNEL_ID = int(CFG["discord_channel_id"])  # 必填
WINDOW_H = int(CFG.get("time_window_hours", 12))

# 全局状态
BOT_STATUS = {
    "running": True,
    "scheduler": None,
    "start_time": datetime.now(),
    "last_fetch": None,
    "last_report": None,
    "total_reports": 0,
    "errors": []
}

scheduler = AsyncIOScheduler(timezone=TZNAME)

async def post_digest(period_label: str, manual=False):
    """生成并发送 arXiv 摘要报告"""
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            logger.warning("Discord channel not found.")
            return False

        now_local = now_in_tz(TZNAME)
        since_local = last_window_start(TZNAME, WINDOW_H)

        logger.info(f"开始获取论文: {since_local} ~ {now_local}")
        papers = fetch_window(CFG, since_local, now_local)
        data = pack_papers(CFG, papers)

        BOT_STATUS["last_fetch"] = now_local
        logger.info(f"获取到 {len(data)} 篇论文")

        # 如果没有论文，不生成报告
        if len(data) == 0:
            logger.info("没有获取到论文，跳过报告生成")
            await channel.send(f" {period_label} | 本次时间窗口内没有新论文")
            return True

        period = fmt_period(now_local)
        st = PeriodState(period)
        st.save_raw(data)

        # 调用 Ollama 生成摘要
        logger.info("开始生成摘要...")
        md = run_ollama(CFG, period_label, since_local.isoformat(), now_local.isoformat(), json.dumps(data, ensure_ascii=False))
        st.save_report(md)

        # 生成 prompt 上下文
        prompt_ctx = (
            "# 原始条目 (JSON)\n" + json.dumps(data, ensure_ascii=False, indent=2) +
            "\n\n# 早/晚报 (Markdown)\n" + md
        )
        st.save_prompt(prompt_ctx)

        # 发送到 Discord
        prefix = "" if manual else ""
        title = f"{prefix} {period_label} | arXiv Digest ({since_local.strftime('%Y-%m-%d %H:%M')} ~ {now_local.strftime('%H:%M')} {TZNAME})"
        await channel.send(title)

        # 分段发送 md
        for chunk in split_message(md):
            await channel.send(chunk)

        BOT_STATUS["last_report"] = now_local
        BOT_STATUS["total_reports"] += 1
        logger.info(f"报告生成完成: {period_label}")
        return True

    except Exception as e:
        error_msg = f"生成报告失败: {str(e)}"
        logger.error(error_msg)
        BOT_STATUS["errors"].append({"time": datetime.now(), "error": error_msg})
        return False


def split_message(text, limit=1800):
    lines = text.split("\n")
    out, buf = [], []
    total = 0
    for ln in lines:
        if total + len(ln) + 1 > limit:
            out.append("\n".join(buf))
            buf, total = [ln], len(ln) + 1
        else:
            buf.append(ln)
            total += len(ln) + 1
    if buf:
        out.append("\n".join(buf))
    return out

# ===== 系统管理命令 =====

@bot.command(name="p-start", help="启动 arXiv push 服务")
async def start_service(ctx):
    """启动服务"""
    if BOT_STATUS["running"]:
        await ctx.send(" 服务已经在运行中")
        return

    try:
        start_scheduler()
        BOT_STATUS["running"] = True
        BOT_STATUS["start_time"] = datetime.now()
        logger.info("服务已启动")
        await ctx.send(" arXiv Push 服务已启动")
    except Exception as e:
        await ctx.send(f" 启动失败: {str(e)}")

@bot.command(name="p-stop", help="停止 arXiv push 服务")
async def stop_service(ctx):
    """停止服务"""
    if not BOT_STATUS["running"]:
        await ctx.send(" 服务未在运行")
        return

    try:
        stop_scheduler()
        BOT_STATUS["running"] = False
        logger.info("服务已停止")
        await ctx.send(" arXiv Push 服务已停止")
    except Exception as e:
        await ctx.send(f" 停止失败: {str(e)}")

@bot.command(name="p-restart", help="重启 arXiv push 服务")
async def restart_service(ctx):
    """重启服务"""
    await ctx.send(" 正在重启服务...")
    try:
        stop_scheduler()
        await asyncio.sleep(2)
        start_scheduler()
        BOT_STATUS["running"] = True
        BOT_STATUS["start_time"] = datetime.now()
        logger.info("服务已重启")
        await ctx.send(" arXiv Push 服务已重启")
    except Exception as e:
        await ctx.send(f" 重启失败: {str(e)}")

@bot.command(name="p-status", help="查看服务状态")
async def status(ctx):
    """查看详细状态"""
    uptime = datetime.now() - BOT_STATUS["start_time"]
    uptime_str = str(uptime).split('.')[0]  # 去掉微秒

    status_emoji = "" if BOT_STATUS["running"] else ""

    embed = discord.Embed(
        title=f"{status_emoji} arXiv Push 服务状态",
        color=discord.Color.green() if BOT_STATUS["running"] else discord.Color.red()
    )

    embed.add_field(name=" 运行状态", value="运行中" if BOT_STATUS["running"] else "已停止", inline=False)
    embed.add_field(name=" 运行时间", value=uptime_str, inline=True)
    embed.add_field(name=" 生成报告数", value=str(BOT_STATUS["total_reports"]), inline=True)
    embed.add_field(name=" 时区", value=TZNAME, inline=True)
    embed.add_field(name=" 报送时间", value=", ".join(CFG.get("report_times", [])), inline=True)
    embed.add_field(name=" 时间窗口", value=f"{WINDOW_H} 小时", inline=True)

    if BOT_STATUS["last_fetch"]:
        embed.add_field(name=" 最后获取", value=BOT_STATUS["last_fetch"].strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    if BOT_STATUS["last_report"]:
        embed.add_field(name=" 最后报告", value=BOT_STATUS["last_report"].strftime("%Y-%m-%d %H:%M:%S"), inline=True)

    if BOT_STATUS["errors"]:
        recent_errors = BOT_STATUS["errors"][-3:]  # 最近3个错误
        error_text = "\n".join([f"• {e['time'].strftime('%H:%M:%S')}: {e['error']}" for e in recent_errors])
        embed.add_field(name=" 最近错误", value=error_text, inline=False)

    await ctx.send(embed=embed)

@bot.command(name="p-report", help="手动生成报告: am | pm")
async def manual_report(ctx, which: str):
    """手动生成报告"""
    if which.lower() not in ["am", "pm"]:
        await ctx.send(" 请指定 'am' 或 'pm'")
        return

    label = "早报" if which.lower() == "am" else "晚报"
    await ctx.send(f" 正在生成{label}...")

    success = await post_digest(label, manual=True)
    if success:
        await ctx.send(f" {label}生成完成")
    else:
        await ctx.send(" 生成失败，请检查日志")

@bot.command(name="p-config", help="配置管理: get | set <key> <value>")
async def config_manage(ctx, action: str, key: str = None, value: str = None):
    """配置管理"""
    if action == "get":
        if key:
            if key in CFG:
                await ctx.send(f" {key}: `{CFG[key]}`")
            else:
                await ctx.send(f" 配置项 '{key}' 不存在")
        else:
            # 显示所有配置
            config_text = json.dumps(CFG, ensure_ascii=False, indent=2)
            if len(config_text) > 1900:
                # 配置太长，分文件显示
                with open("current_config.yaml", "w", encoding="utf-8") as f:
                    yaml.safe_dump(CFG, f, allow_unicode=True, sort_keys=False)
                await ctx.send(" 配置文件太长，已保存到 `current_config.yaml`")
            else:
                await ctx.send(f" 当前配置:\n```yaml\n{config_text}\n```")

    elif action == "set" and key and value:
        try:
            # 尝试转换值的类型
            if value.lower() in ["true", "false"]:
                value = value.lower() == "true"
            elif value.isdigit():
                value = int(value)
            elif "." in value and value.replace(".", "").isdigit():
                value = float(value)

            CFG[key] = value

            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(CFG, f, allow_unicode=True, sort_keys=False)

            await ctx.send(f" 已更新 {key}: `{value}`")
            logger.info(f"配置已更新: {key} = {value}")

        except Exception as e:
            await ctx.send(f" 更新失败: {str(e)}")

    else:
        await ctx.send(" 语法错误，使用: `arxiv-p-config get|set <key> <value>`")

@bot.command(name="p-logs", help="查看日志: [lines=10]")
async def show_logs(ctx, lines: int = 10):
    """查看日志"""
    try:
        with open("arxivpush.log", "r", encoding="utf-8") as f:
            log_lines = f.readlines()

        recent_lines = log_lines[-lines:]
        log_text = "".join(recent_lines)

        if len(log_text) > 1900:
            log_text = log_text[-1900:] + "\n... (日志被截断)"

        await ctx.send(f" 最近 {len(recent_lines)} 行日志:\n```log\n{log_text}\n```")

    except FileNotFoundError:
        await ctx.send(" 日志文件不存在")
    except Exception as e:
        await ctx.send(f" 读取日志失败: {str(e)}")

def start_scheduler():
    """启动调度器"""
    if scheduler.running:
        return

    # 清除现有任务
    scheduler.remove_all_jobs()

    # 添加定时任务
    for t in CFG.get("report_times", ["10:00", "22:00"]):
        hour, minute = map(int, t.split(":"))
        label = "早报" if hour < 12 else "晚报"
        scheduler.add_job(
            post_digest,
            CronTrigger(hour=hour, minute=minute),
            args=[label],
            name=f"{label}",
            id=f"daily_{label}"
        )

    scheduler.start()
    BOT_STATUS["scheduler"] = scheduler
    logger.info("调度器已启动")

def stop_scheduler():
    """停止调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("调度器已停止")

# ===== 专用命令 =====

@bot.command(name="smi", help="显示 arXiv Push 实时状态 (类似 nvidia-smi)")
async def smi(ctx):
    """实时状态检测 - 类似 nvidia-smi"""

    # 系统资源信息
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Ollama 状态检查
    ollama_status = " 运行中"
    ollama_model = CFG.get("ollama", {}).get("model", "未知")
    try:
        import requests
        response = requests.get(f"{CFG.get('ollama', {}).get('host', 'http://127.0.0.1:11434')}/api/tags", timeout=5)
        if response.status_code != 200:
            ollama_status = " 无响应"
    except:
        ollama_status = " 连接失败"

    # 调度器状态
    scheduler_status = " 运行中" if scheduler.running else " 已停止"
    jobs = scheduler.get_jobs()

    # 创建状态面板
    embed = discord.Embed(
        title="  arXiv Push 实时状态",
        description=f"**版本**: v1.0 | **进程ID**: {os.getpid()}",
        color=discord.Color.blue()
    )

    # 服务状态
    service_status = " 运行中" if BOT_STATUS["running"] else " 已停止"
    uptime = datetime.now() - BOT_STATUS["start_time"]

    embed.add_field(
        name=" 服务状态",
        value=f"**状态**: {service_status}\n**运行时间**: {str(uptime).split('.')[0]}\n**生成报告**: {BOT_STATUS['total_reports']} 次",
        inline=True
    )

    # 调度器状态
    job_info = "\n".join([f"• {job.name}" for job in jobs]) if jobs else "无任务"
    embed.add_field(
        name=" 调度器",
        value=f"**状态**: {scheduler_status}\n**任务数**: {len(jobs)}\n**任务列表**:\n{job_info}",
        inline=True
    )

    # 系统资源
    embed.add_field(
        name=" 系统资源",
        value=f"**CPU**: {cpu_percent}%\n**内存**: {memory.percent}% ({memory.used//1024//1024}MB/{memory.total//1024//1024}MB)\n**磁盘**: {disk.percent}% ({disk.used//1024//1024//1024}GB/{disk.total//1024//1024//1024}GB)",
        inline=True
    )

    # Ollama 状态
    embed.add_field(
        name=" Ollama",
        value=f"**状态**: {ollama_status}\n**模型**: {ollama_model}\n**接口**: {CFG.get('ollama', {}).get('host', 'http://127.0.0.1:11434')}",
        inline=True
    )

    # 网络状态
    embed.add_field(
        name=" 网络",
        value=f"**Discord**:  已连接\n**频道ID**: {CHANNEL_ID}\n**前缀**: arxiv-",
        inline=True
    )

    # 最近活动
    recent_activity = []
    if BOT_STATUS["last_fetch"]:
        recent_activity.append(f" 最后获取: {BOT_STATUS['last_fetch'].strftime('%H:%M:%S')}")
    if BOT_STATUS["last_report"]:
        recent_activity.append(f" 最后报告: {BOT_STATUS['last_report'].strftime('%H:%M:%S')}")
    if BOT_STATUS["errors"]:
        recent_activity.append(f" 错误数: {len(BOT_STATUS['errors'])}")

    embed.add_field(
        name=" 最近活动",
        value="\n".join(recent_activity) if recent_activity else "暂无活动",
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command(name="rn", help="立即运行一次报告生成")
async def run_now(ctx, which: str = None):
    """立即运行一次 - 智能判断早报/晚报"""
    if not which:
        # 智能判断当前时间应该生成早报还是晚报
        now_local = now_in_tz(TZNAME)
        which = "am" if now_local.hour < 12 else "pm"

    if which.lower() not in ["am", "pm"]:
        await ctx.send(" 请指定 'am' 或 'pm'")
        return

    label = "早报" if which.lower() == "am" else "晚报"

    # 发送正在处理的提示
    msg = await ctx.send(f" **立即执行中** - 正在生成{label}...\n 可能需要1-3分钟，请稍候...")

    try:
        success = await post_digest(label, manual=True)

        if success:
            await msg.edit(content=f" **执行完成** - {label}已生成并推送！\n 使用 `arxiv-smi` 查看详细状态")
        else:
            await msg.edit(content=f" **执行失败** - {label}生成失败\n 使用 `arxiv-p-logs` 查看错误日志")

    except Exception as e:
        await msg.edit(content=f" **执行异常** - {str(e)}\n 使用 `arxiv-p-logs` 查看详细错误信息")

@bot.command(name="p-help", help="显示帮助信息")
async def help_cmd(ctx):
    """显示帮助信息"""
    embed = discord.Embed(
        title="arXiv Push 帮助",
        description="基于 Discord 的 arXiv 论文自动推送和对话系统",
        color=discord.Color.gold()
    )

    # 实用命令
    embed.add_field(
        name="核心命令",
        value="`arxiv-smi` - 实时系统状态监控\n`arxiv-rn [am|pm]` - 立即生成报告\n`arxiv-p-status` - 查看服务状态",
        inline=False
    )

    # 系统管理
    embed.add_field(
        name="系统管理",
        value="`arxiv-p-start` - 启动服务\n`arxiv-p-stop` - 停止服务\n`arxiv-p-restart` - 重启服务",
        inline=False
    )

    # 配置管理
    embed.add_field(
        name="配置管理",
        value="`arxiv-p-config get [key]` - 查看配置项\n`arxiv-p-config set <key> <value>` - 修改配置\n`arxiv-p-logs [lines=10]` - 查看系统日志",
        inline=False
    )

    # 对话功能
    embed.add_field(
        name="对话功能",
        value="发送以 `/` 开头的消息即可与最新报告对话\n例如: `/这些论文有什么共同点？`\n`/详细解释第一篇论文的方法`",
        inline=False
    )

    embed.set_footer(text="所有命令都使用 'arxiv-' 前缀")
    await ctx.send(embed=embed)

# ===== 事件处理 =====

@bot.event
async def on_ready():
    """Bot 启动事件"""
    logger.info(f"Bot 已登录: {bot.user}")

    # 启动调度器
    start_scheduler()

    # 发送启动消息
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f" **arXiv Push 服务已启动**\n **Bot**: {bot.user.mention}\n **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n **帮助**: 使用 `arxiv-help` 查看所有命令")
    except Exception as e:
        logger.error(f"发送启动消息失败: {e}")

@bot.event
async def on_message(message: discord.Message):
    """消息处理事件"""
    if message.author == bot.user:
        return

    try:
        # 先处理命令
        await bot.process_commands(message)

        # 普通聊天：如果在 12 小时有效期内，与最近的报告对话
        if message.channel.id != CHANNEL_ID:
            return

        user_msg = message.content.strip()

        # 检查是否以/开头，如果是则开始对话
        if not user_msg.startswith('/'):
            return  # 不是对话命令，不处理

        # 去掉开头的/
        user_msg = user_msg[1:].strip()
        if not user_msg:
            return  # 空消息，不处理

        now_local = now_in_tz(TZNAME)
        name = latest_active_period(now_local, hours=WINDOW_H)
        if not name:
            await message.channel.send(" 当前没有可对话的报告，请先生成报告")
            return  # 超出会话有效期

        st = PeriodState(name)
        ctx_text = st.prompt_context.read_text(encoding="utf-8") if st.prompt_context.exists() else ""

        if not ctx_text.strip():
            await message.channel.send(" 没有找到报告上下文，请先生成报告")
            return  # 没有上下文

        st.append_chat("user", user_msg)

        # 构建对话提示
        prompt = (
            "你是学术助手。以下是某期 arXiv 早/晚报的上下文，请基于此逐问逐答。"
            "若用户要求对比/延伸，请引用报文中的条目并给出具体理由。\n\n" + ctx_text +
            "\n\n# 用户提问\n" + user_msg
        )

        # 调用 Ollama 进行对话
        import requests
        host = CFG.get("ollama", {}).get("host", "http://127.0.0.1:11434")
        model = CFG.get("ollama", {}).get("model", "qwen2.5:7b")
        payload = {"model": model, "prompt": prompt, "stream": False, "keep_alive": CFG.get("ollama", {}).get("keep_alive", 0)}

        response = requests.post(f"{host}/api/generate", json=payload, timeout=300)
        response.raise_for_status()
        answer = response.json().get("response", "").strip()

        st.append_chat("assistant", answer)

        # 分段发送回复
        for chunk in split(answer):
            await message.channel.send(chunk)

    except Exception as e:
        logger.error(f"处理消息失败: {e}")
        import traceback
        traceback.print_exc()

        # 不发送错误消息以避免刷屏
        # await message.channel.send(" 消息处理失败，请稍后重试")

def split(s, limit=1800):
    """分割长消息"""
    out, cur = [], []
    n = 0
    for ln in s.split("\n"):
        if n + len(ln) + 1 > limit:
            out.append("\n".join(cur))
            cur, n = [ln], len(ln) + 1
        else:
            cur.append(ln); n += len(ln) + 1
    if cur: out.append("\n".join(cur))
    return out

if __name__ == "__main__":
    logger.info("正在启动 arXiv Push Bot...")
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))
