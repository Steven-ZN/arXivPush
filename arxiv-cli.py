#!/usr/bin/env python3
"""
arXiv Push CLI - 命令行接口
支持 arxiv- 前缀的所有命令
"""

import os, sys, json, yaml, asyncio, argparse
from datetime import datetime
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import now_in_tz, last_window_start, fmt_period
from datetime import timedelta
from arxiv_fetch import fetch_window, pack_papers, mark_papers_as_pushed
from summarizer import run_ollama
from state import PeriodState, latest_active_period
from ollama_manager import create_ollama_manager

# 加载配置
with open("config.yaml", "r", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

TZNAME = CFG.get("timezone", "America/New_York")
CHANNEL_ID = int(CFG["discord_channel_id"])
WINDOW_H = int(CFG.get("time_window_hours", 12))

class ArxivCLI:
    def __init__(self):
        self.status_file = Path("status.json")
        self.load_status()

    def format_time_minus_4h(self, time_str):
        """格式化时间显示"""
        if not time_str:
            return "N/A"
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%dT%H:%M:%S%z')
        except:
            return time_str

    def load_status(self):
        """加载状态"""
        if self.status_file.exists():
            with open(self.status_file, "r", encoding="utf-8") as f:
                self.status = json.load(f)
        else:
            self.status = {
                "running": False,
                "start_time": None,
                "last_fetch": None,
                "last_report": None,
                "total_reports": 0,
                "errors": []
            }

    def save_status(self):
        """保存状态"""
        with open(self.status_file, "w", encoding="utf-8") as f:
            json.dump(self.status, f, ensure_ascii=False, indent=2, default=str)

    def is_bot_running(self):
        """检查bot进程是否实际在运行"""
        try:
            import subprocess
            result = subprocess.run(['pgrep', '-f', 'bot.py'],
                                  capture_output=True, text=True)
            return result.returncode == 0 and result.stdout.strip()
        except:
            return False

    def get_bot_process_info(self):
        """获取bot进程详细信息"""
        try:
            import subprocess
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'bot.py' in line and 'grep' not in line and 'python' in line:
                    parts = line.split()
                    if len(parts) >= 11:
                        return {
                            'pid': parts[1],
                            'cpu': parts[2],
                            'mem': parts[3],
                            'time': parts[9],
                            'cmd': ' '.join(parts[10:])
                        }
            return None
        except:
            return None

    def cmd_start(self):
        """启动服务 - 真正的进程管理"""
        # 检查进程是否实际在运行
        if self.is_bot_running():
            process_info = self.get_bot_process_info()
            print("⚠️  arXiv Push 服务已经在运行中")
            if process_info:
                print(f"📊 进程信息:")
                print(f"   PID: {process_info['pid']}")
                print(f"   CPU: {process_info['cpu']}%")
                print(f"   内存: {process_info['mem']}%")
                print(f"   运行时间: {process_info['time']}")
                print(f"   命令: {process_info['cmd']}")
            return

        print("🚀 正在启动 arXiv Push 服务...")

        # 检查必要文件
        if not os.path.exists(".env"):
            print("❌ 错误: .env 文件不存在")
            print("💡 请先配置 Discord Bot Token")
            return

        if not os.path.exists("config.yaml"):
            print("❌ 错误: config.yaml 文件不存在")
            print("💡 请先配置服务参数")
            return

        # 检查并启动Ollama服务
        print("🤖 检查 Ollama 服务...")
        ollama_manager = create_ollama_manager(CFG)

        if not ollama_manager.start_service(auto_start=True):
            print("❌ Ollama 服务启动失败")
            print("💡 arXiv Push 需要 Ollama 服务来生成摘要")
            print("💡 请手动检查 Ollama 安装和配置")
            return

        print("✅ Ollama 服务就绪")

        # 启动服务
        try:
            import subprocess
            # 使用nohup在后台启动服务
            process = subprocess.Popen([
                'nohup', 'python3', 'bot.py'
            ], stdout=open('bot_output.log', 'w'),
               stderr=subprocess.STDOUT)

            # 等待进程启动
            import time
            time.sleep(2)

            # 验证进程是否成功启动
            if process.poll() is None:  # 进程还在运行
                print("✅ arXiv Push 服务启动成功")

                # 更新状态
                self.status["running"] = True
                self.status["start_time"] = datetime.now().isoformat()
                self.save_status()

                # 显示配置信息
                print(f"📅 报送时间: {', '.join(CFG.get('report_times', []))} ({TZNAME})")
                print(f"🔍 时间窗口: {WINDOW_H} 小时")
                print(f"🤖 Ollama 模型: {CFG.get('ollama', {}).get('model', 'qwen2.5:7b')}")
                print(f"📁 日志文件: bot_output.log")
                print(f"💡 使用 'arxiv status' 查看服务状态")
                print(f"💡 使用 'arxiv smi' 查看实时监控")

            else:
                print("❌ 服务启动失败")
                print("💡 请检查日志文件: bot_output.log")

        except Exception as e:
            print(f"❌ 启动失败: {str(e)}")
            print("💡 请检查 Python 环境和依赖包")

    def cmd_stop(self):
        """停止服务 - 真正的进程管理"""
        print("🛑 正在停止 arXiv Push 服务...")

        # 尝试终止bot进程
        stopped = False
        try:
            import subprocess
            # 查找并终止进程
            result = subprocess.run(['pkill', '-f', 'python.*bot.py'],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ 已向服务进程发送停止信号")
                stopped = True
            else:
                print("⚠️  未找到运行中的服务进程")

            # 等待进程结束
            import time
            time.sleep(1)

            # 验证进程是否已停止
            if self.is_bot_running():
                print("⚠️  服务仍在运行，尝试强制终止...")
                subprocess.run(['pkill', '-9', '-f', 'python.*bot.py'])
                time.sleep(1)

            if not self.is_bot_running():
                print("✅ arXiv Push 服务已停止")
            else:
                print("❌ 无法停止服务，请手动检查进程")

        except Exception as e:
            print(f"❌ 停止服务时出错: {str(e)}")

        # 更新状态
        self.status["running"] = False
        self.save_status()

        if stopped:
            print("💡 使用 'arxiv start' 重新启动服务")

    def cmd_restart(self):
        """重启服务"""
        print("🔄 正在重启服务...")
        self.cmd_stop()
        self.cmd_start()
        print("✅ arXiv Push 服务已重启")

    def cmd_status(self):
        """查看服务状态 - 包含实际进程检测"""
        # 检查实际进程状态
        is_running = self.is_bot_running()
        process_info = self.get_bot_process_info() if is_running else None

        # 计算运行时间
        uptime = "N/A"
        if process_info and process_info['time']:
            uptime = process_info['time']
        elif self.status["start_time"]:
            start_time = datetime.fromisoformat(self.status["start_time"])
            uptime = str(datetime.now() - start_time).split('.')[0]

        # 状态显示
        if is_running and process_info:
            status_emoji = "🟢"
            status_text = "运行中"
            detail_info = f"PID: {process_info['pid']} | CPU: {process_info['cpu']}% | 内存: {process_info['mem']}%"
        elif is_running:
            status_emoji = "🟡"
            status_text = "检测到运行但信息获取失败"
            detail_info = "请检查进程状态"
        else:
            status_emoji = "🔴"
            status_text = "已停止"
            detail_info = "服务未运行"

        print(f"\n{status_emoji} arXiv Push 服务状态")
        print("=" * 60)
        print(f"🚀 运行状态: {status_text}")
        if detail_info:
            print(f"📊 详细信息: {detail_info}")
        print(f"⏱️  运行时间: {uptime}")
        print(f"📊 生成报告数: {self.status['total_reports']}")

        # 配置信息
        print(f"\n⚙️  配置信息:")
        print(f"   时区: {TZNAME}")
        print(f"   报送时间: {', '.join(CFG.get('report_times', []))}")
        print(f"   时间窗口: {WINDOW_H} 小时")
        print(f"   Ollama 模型: {CFG.get('ollama', {}).get('model', 'qwen2.5:7b')}")

        # 最近活动
        print(f"\n📈 最近活动:")
        if self.status["last_fetch"]:
            print(f"   📥 最后获取: {self.format_time_minus_4h(self.status['last_fetch'])}")
        if self.status["last_report"]:
            print(f"   📤 最后报告: {self.format_time_minus_4h(self.status['last_report'])}")

        # 错误信息
        if self.status["errors"]:
            recent_errors = self.status["errors"][-3:]
            print(f"\n⚠️  最近错误 (最近{len(recent_errors)}个):")
            for error in recent_errors:
                print(f"   • {error['time']}: {error['error']}")

        # 服务管理提示
        print(f"\n💡 服务管理:")
        if not is_running:
            print(f"   启动服务: arxiv start")
            print(f"   查看日志: tail -f bot_output.log")
        else:
            print(f"   停止服务: arxiv stop")
            print(f"   重启服务: arxiv restart")
            print(f"   实时监控: arxiv smi")

        print("=" * 60)

    def cmd_smi(self):
        """实时状态检测 - 类似 nvidia-smi"""
        import psutil

        # 系统资源信息
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # CPU 信息
        cpu_info = []
        try:
            # CPU型号
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            cpu_model = line.split(':')[1].strip()
                            break
            except:
                cpu_model = "Unknown"

            # CPU频率
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                cpu_current_freq = f"{cpu_freq.current:.0f}MHz"
                cpu_max_freq = f"{cpu_freq.max:.0f}MHz"
            else:
                cpu_current_freq = "Unknown"
                cpu_max_freq = "Unknown"

            # CPU核心数
            cpu_cores = psutil.cpu_count(logical=False)
            cpu_threads = psutil.cpu_count(logical=True)

            cpu_info.append(f"   CPU: {cpu_model}")
            cpu_info.append(f"   频率: {cpu_current_freq}/{cpu_max_freq}")
            cpu_info.append(f"   核心: {cpu_cores}c/{cpu_threads}t")
            cpu_info.append(f"   使用率: {cpu_percent}%")
        except Exception as e:
            cpu_info.append(f"   CPU检测失败: {str(e)}")

        # Ollama 状态检查
        ollama_status = "运行中"
        ollama_model = CFG.get("ollama", {}).get("model", "未知")
        try:
            import requests
            response = requests.get(f"{CFG.get('ollama', {}).get('host', 'http://127.0.0.1:11434')}/api/tags", timeout=5)
            if response.status_code != 200:
                ollama_status = "无响应"
        except:
            ollama_status = "连接失败"

        print(f"\narXiv Push 实时状态")
        print("=" * 60)
        print(f"版本: v1.0 | 进程ID: {os.getpid()}")

        # 服务状态
        service_status = "运行中" if self.status["running"] else "已停止"
        uptime = "N/A"
        if self.status["start_time"]:
            start_time = datetime.fromisoformat(self.status["start_time"])
            uptime = str(datetime.now() - start_time).split('.')[0]

        print(f"\n服务状态:")
        print(f"   状态: {service_status}")
        print(f"   运行时间: {uptime}")
        print(f"   生成报告: {self.status['total_reports']} 次")

        # GPU 状态检查
        gpu_info = []
        try:
            import GPUtil
            import subprocess
            gpus = GPUtil.getGPUs()
            if gpus:
                for i, gpu in enumerate(gpus):
                    # 获取GPU型号
                    try:
                        result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                                              capture_output=True, text=True, timeout=5)
                        gpu_names = result.stdout.strip().split('\n')
                        gpu_name = gpu_names[i] if i < len(gpu_names) else "Unknown"
                    except:
                        gpu_name = "Unknown"

                    gpu_info.append(f"   GPU {i} {gpu_name}: {gpu.load*100:.1f}% {gpu.memoryUsed}MB/{gpu.memoryTotal}MB {gpu.temperature}°C")
            else:
                gpu_info.append("   未检测到GPU")
        except ImportError:
            gpu_info.append("   GPUtil未安装")
        except Exception as e:
            gpu_info.append(f"   GPU检测失败: {str(e)}")

        print(f"\n系统资源:")
        for cpu_line in cpu_info:
            print(cpu_line)
        print(f"   内存: {memory.percent}% ({memory.used//1024//1024}MB/{memory.total//1024//1024}MB)")
        print(f"   磁盘: {disk.percent}% ({disk.used//1024//1024//1024}GB/{disk.total//1024//1024//1024}GB)")

        print(f"\nGPU 资源:")
        for gpu_line in gpu_info:
            print(gpu_line)

        print(f"\nOllama:")
        print(f"   状态: {ollama_status}")
        print(f"   模型: {ollama_model}")
        print(f"   接口: {CFG.get('ollama', {}).get('host', 'http://127.0.0.1:11434')}")

        print(f"\n配置:")
        print(f"   Discord: 已配置")
        print(f"   频道ID: {CHANNEL_ID}")
        print(f"   时区: {TZNAME}")

        # 最近活动
        print(f"\n最近活动:")
        if self.status["last_fetch"]:
            print(f"   最后获取: {self.format_time_minus_4h(self.status['last_fetch'])}")
        if self.status["last_report"]:
            print(f"   最后报告: {self.format_time_minus_4h(self.status['last_report'])}")
        if self.status["errors"]:
            print(f"   错误数: {len(self.status['errors'])}")

        print("=" * 60)

    def cmd_ollama(self, action=None):
        """Ollama服务管理"""
        ollama_manager = create_ollama_manager(CFG)

        if not action:
            # 显示状态
            status = ollama_manager.get_status()
            print("🤖 Ollama 服务状态")
            print("=" * 50)

            if status['service_running']:
                print(f"🟢 服务状态: 运行中")
                if status['process_info']:
                    print(f"📊 进程信息: PID={status['process_info']['pid']}, CPU={status['process_info']['cpu']}%, 内存={status['process_info']['mem']}%")
            else:
                print(f"🔴 服务状态: 已停止")

            print(f"📡 服务地址: {status['host']}")
            print(f"🤖 模型名称: {status['model_name']}")

            if status['model_available']:
                print(f"✅ 模型状态: 可用 (大小: {status['model_size']})")
            else:
                print(f"❌ 模型状态: 不可用")

            print("\n💡 可用命令:")
            print("   arxiv-ollama start    - 启动服务")
            print("   arxiv-ollama stop     - 停止服务")
            print("   arxiv-ollama restart  - 重启服务")
            print("   arxiv-ollama test     - 测试服务")
            print("   arxiv-ollama status   - 显示状态")

        elif action == "start":
            print("🚀 启动 Ollama 服务...")
            if ollama_manager.start_service(auto_start=True):
                print("✅ Ollama 服务启动成功")
            else:
                print("❌ Ollama 服务启动失败")

        elif action == "stop":
            print("🛑 停止 Ollama 服务...")
            if ollama_manager.stop_service():
                print("✅ Ollama 服务已停止")
            else:
                print("❌ Ollama 服务停止失败")

        elif action == "restart":
            print("🔄 重启 Ollama 服务...")
            ollama_manager.stop_service()
            import time
            time.sleep(2)
            if ollama_manager.start_service(auto_start=True):
                print("✅ Ollama 服务重启成功")
            else:
                print("❌ Ollama 服务重启失败")

        elif action == "test":
            print("🧪 测试 Ollama 服务...")
            success, message = ollama_manager.test_service()
            if success:
                print(f"✅ 测试通过: {message}")
            else:
                print(f"❌ 测试失败: {message}")

        elif action == "status":
            status = ollama_manager.get_status()
            print("🤖 Ollama 详细状态")
            print("=" * 40)
            print(f"服务运行: {'是' if status['service_running'] else '否'}")
            print(f"模型可用: {'是' if status['model_available'] else '否'}")
            print(f"模型名称: {status['model_name']}")
            print(f"服务地址: {status['host']}")
            if status['model_size']:
                print(f"模型大小: {status['model_size']}")
            if status['process_info']:
                print(f"进程PID: {status['process_info']['pid']}")
                print(f"CPU使用: {status['process_info']['cpu']}%")
                print(f"内存使用: {status['process_info']['mem']}%")

        else:
            print("❌ 未知命令")
            print("💡 可用命令: start, stop, restart, test, status")

    async def cmd_report(self, which):
        """手动生成报告"""
        report_mode = CFG.get("report_mode", "daily")

        if report_mode == "hourly":
            if which.lower() != "hourly":
                print("❌ 当前为小时模式，请指定 'hourly'")
                return False
            label = "小时报告"
        else:
            if which.lower() not in ["am", "pm"]:
                print("❌ 请指定 'am' 或 'pm'")
                return False
            label = "早报" if which.lower() == "am" else "晚报"

        print(f"🔄 正在生成{label}...")

        try:
            success = await self.generate_report(label)
            if success:
                print(f"✅ {label}生成完成")
                return True
            else:
                print("❌ 生成失败，请检查日志")
                return False
        except Exception as e:
            print(f"❌ 生成异常: {str(e)}")
            return False

    async def cmd_rn(self, which=None):
        """立即运行一次 - 智能判断报告类型"""
        report_mode = CFG.get("report_mode", "daily")

        if not which:
            if report_mode == "hourly":
                which = "hourly"
            else:
                # 智能判断当前时间应该生成早报还是晚报
                now_local = now_in_tz(TZNAME)
                which = "am" if now_local.hour < 12 else "pm"

        if report_mode == "hourly":
            if which.lower() != "hourly":
                print("❌ 当前为小时模式，请指定 'hourly'")
                return False
            label = "小时报告"
        else:
            if which.lower() not in ["am", "pm"]:
                print("❌ 请指定 'am' 或 'pm'")
                return False
            label = "早报" if which.lower() == "am" else "晚报"

        print(f"🚀 立即执行中 - 正在生成{label}...")
        print("⏳ 可能需要1-3分钟，请稍候...")

        try:
            success = await self.generate_report(label)
            if success:
                print(f"✅ 执行完成 - {label}已生成！")
                print(f"📁 报告保存在 storage/ 目录下")
                return True
            else:
                print(f"❌ 执行失败 - {label}生成失败")
                return False
        except Exception as e:
            print(f"💥 执行异常 - {str(e)}")
            return False

    async def generate_report(self, period_label: str, manual=False):
        """生成报告核心逻辑"""
        try:
            now_local = now_in_tz(TZNAME)
            # 移除12小时时间限制，获取最新论文
            print(f"📥 获取最新论文 (无时间限制)")
            papers = fetch_window(CFG, None, now_local)  # 传入None表示不限制开始时间
            data = pack_papers(CFG, papers)

            self.status["last_fetch"] = now_local.isoformat()
            self.save_status()
            print(f"📊 获取到 {len(data)} 篇论文")

            # 如果没有论文，不生成报告
            if len(data) == 0:
                print("📭 当前没有找到相关论文")
                return True

            period = fmt_period(now_local)
            st = PeriodState(period)
            st.save_raw(data)

            # 标记论文为已推送
            mark_papers_as_pushed(papers)

            # 调用 Ollama 生成摘要
            print("🤖 开始生成摘要...")
            # 传入空字符串作为开始时间，表示无时间限制
            md = run_ollama(CFG, period_label, "", now_local.isoformat(), json.dumps(data, ensure_ascii=False))
            st.save_report(md)

            # 生成 prompt 上下文
            prompt_ctx = (
                "# 原始条目 (JSON)\n" + json.dumps(data, ensure_ascii=False, indent=2) +
                "\n\n# 早/晚报 (Markdown)\n" + md
            )
            st.save_prompt(prompt_ctx)

            self.status["last_report"] = now_local.isoformat()
            self.status["total_reports"] += 1
            self.save_status()
            print(f"✅ 报告生成完成: {period_label}")
            return True

        except Exception as e:
            error_msg = f"生成报告失败: {str(e)}"
            print(f"❌ {error_msg}")
            self.status["errors"].append({"time": datetime.now().isoformat(), "error": error_msg})
            self.save_status()
            return False

    def cmd_config_get(self, key=None):
        """查看配置"""
        if key:
            if key in CFG:
                print(f"📋 {key}: {CFG[key]}")
            else:
                print(f"❌ 配置项 '{key}' 不存在")
        else:
            print("📋 当前配置:")
            print(json.dumps(CFG, ensure_ascii=False, indent=2))

    def cmd_config_set(self, key, value):
        """设置配置"""
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

            print(f"✅ 已更新 {key}: {value}")
            print(f"💡 注意: 需要重启服务使配置生效")

        except Exception as e:
            print(f"❌ 更新失败: {str(e)}")

    def cmd_logs(self, lines=10):
        """查看日志"""
        try:
            with open("arxivpush.log", "r", encoding="utf-8") as f:
                log_lines = f.readlines()

            recent_lines = log_lines[-lines:]
            print(f"📄 最近 {len(recent_lines)} 行日志:")
            print("=" * 50)
            print("".join(recent_lines))

        except FileNotFoundError:
            print("❌ 日志文件不存在")
        except Exception as e:
            print(f"❌ 读取日志失败: {str(e)}")

    def cmd_keywords(self, action=None, param=None):
        """关键词管理"""
        if not action:
            print("🔍 当前关键词配置:")
            print("=" * 50)
            queries = CFG.get("queries", [])
            if not queries:
                print("❌ 暂无关键词配置")
                return

            for i, query in enumerate(queries, 1):
                print(f"\n查询块 {i}:")
                if "any" in query:
                    print(f"  任意匹配 (OR): {', '.join(query['any'])}")
                if "all" in query:
                    print(f"  全部匹配 (AND): {', '.join(query['all'])}")

            exclude = CFG.get("exclude", [])
            if exclude:
                print(f"\n排除关键词: {', '.join(exclude)}")
            return

        if action == "clear":
            CFG["queries"] = []
            CFG["exclude"] = []
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(CFG, f, allow_unicode=True, sort_keys=False)
            print("✅ 已清空所有关键词配置")

        elif action == "add-or" and param:
            keywords = [k.strip() for k in param.split(",")]
            if "queries" not in CFG:
                CFG["queries"] = []
            CFG["queries"].append({"any": keywords})
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(CFG, f, allow_unicode=True, sort_keys=False)
            print(f"✅ 已添加任意匹配关键词: {', '.join(keywords)}")

        elif action == "add-and" and param:
            keywords = [k.strip() for k in param.split(",")]
            if "queries" not in CFG:
                CFG["queries"] = []
            CFG["queries"].append({"all": keywords})
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(CFG, f, allow_unicode=True, sort_keys=False)
            print(f"✅ 已添加全部匹配关键词: {', '.join(keywords)}")

        elif action == "exclude" and param:
            keywords = [k.strip() for k in param.split(",")]
            if "exclude" not in CFG:
                CFG["exclude"] = []
            CFG["exclude"].extend(keywords)
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(CFG, f, allow_unicode=True, sort_keys=False)
            print(f"✅ 已添加排除关键词: {', '.join(keywords)}")

        elif action == "set-default":
            CFG["queries"] = [
                {"any": ["machine learning", "deep learning", "neural network"]},
                {"any": ["computer vision", "image processing", "object detection"]},
                {"all": ["transformer", "attention"]},
            ]
            CFG["exclude"] = ["survey", "review", "perspective"]
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(CFG, f, allow_unicode=True, sort_keys=False)
            print("✅ 已设置默认关键词配置")

        elif action == "set-ai":
            CFG["queries"] = [
                {"any": ["GPT", "LLM", "large language model", "transformer"]},
                {"any": ["diffusion model", "generative AI", "GAN"]},
                {"all": ["reinforcement learning", "policy"]},
                {"any": ["computer vision", "NLP", "natural language processing"]},
            ]
            CFG["exclude"] = ["survey", "review"]
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(CFG, f, allow_unicode=True, sort_keys=False)
            print("✅ 已设置 AI 领域关键词配置")

        elif action == "set-cv":
            CFG["queries"] = [
                {"any": ["computer vision", "image segmentation", "object detection"]},
                {"any": ["deep learning", "CNN", "convolutional neural network"]},
                {"all": ["medical image", "segmentation"]},
                {"any": ["transformer", "vision transformer", "ViT"]},
            ]
            CFG["exclude"] = ["survey", "review"]
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.safe_dump(CFG, f, allow_unicode=True, sort_keys=False)
            print("✅ 已设置计算机视觉关键词配置")

        else:
            print("❌ 语法错误")
            print("用法:")
            print("  arxiv-keywords                    # 显示当前关键词")
            print("  arxiv-keywords clear              # 清空关键词")
            print("  arxiv-keywords add-or word1,word2 # 添加任意匹配")
            print("  arxiv-keywords add-and word1,word2# 添加全部匹配")
            print("  arxiv-keywords exclude word1,word2# 添加排除词")
            print("  arxiv-keywords set-default        # 设置默认关键词")
            print("  arxiv-keywords set-ai             # 设置 AI 关键词")
            print("  arxiv-keywords set-cv             # 设置 CV 关键词")

    def cmd_help(self):
        """显示帮助信息"""
        print("🤖 arXiv Push CLI 帮助")
        print("=" * 50)

        print("\n🔧 系统管理:")
        print("  arxiv-start           - 启动服务")
        print("  arxiv-stop            - 停止服务")
        print("  arxiv-restart         - 重启服务")
        print("  arxiv-status          - 查看状态")
        print("  arxiv-smi             - 实时监控")
        print("  arxiv-ollama          - Ollama服务管理")

        print("\n📊 报告管理:")
        report_mode = CFG.get("report_mode", "daily")
        if report_mode == "hourly":
            print("  arxiv-report hourly   - 手动生成小时报告")
            print("  arxiv-rn [hourly]     - 立即运行一次")
        else:
            print("  arxiv-report am|pm    - 手动生成报告")
            print("  arxiv-rn [am|pm]      - 立即运行一次")

        print("\n⚙️  配置管理:")
        print("  arxiv-config get [key]    - 查看配置")
        print("  arxiv-config set <key> <value> - 修改配置")
        print("  arxiv-keywords [action]    - 关键词管理")

        print("\n🛠️  其他功能:")
        print("  arxiv-logs [lines=10] - 查看日志")
        print("  arxiv-help            - 显示帮助")


def main():
    # 支持多种调用方式:
    # 1. arxiv-start (符号链接)
    # 2. python arxiv-cli.py start (直接调用)
    # 3. arxiv start (需要特殊处理)

    script_name = os.path.basename(sys.argv[0])

    if script_name.startswith("arxiv-") and script_name != "arxiv-cli.py":
        # 从符号链接名解析命令: arxiv-start -> start
        cmd = script_name[6:]  # 去掉 "arxiv-" 前缀
        args = sys.argv[1:]
    elif len(sys.argv) >= 2 and sys.argv[1] in ["start", "stop", "restart", "status", "smi", "rn", "help", "config", "keywords", "logs"]:
        # 支持: python arxiv-cli.py start 或 arxiv start (如果创建arxiv脚本)
        cmd = sys.argv[1]
        args = sys.argv[2:]
    else:
        # 传统方式: python arxiv-cli.py start
        if len(sys.argv) < 2:
            print("❌ 请提供命令参数，使用 'arxiv-help' 查看帮助")
            sys.exit(1)
        cmd = sys.argv[1]
        args = sys.argv[2:]

    cli = ArxivCLI()

    # 异步命令
    if cmd in ["report", "rn"]:
        asyncio.run(cli.execute_async_cmd(cmd, *args))
        return

    # 同步命令
    cli.execute_sync_cmd(cmd, *args)


# 为 ArxivCLI 添加命令执行方法
def execute_sync_cmd(self, cmd, *args):
    """执行同步命令"""
    if cmd == "start":
        self.cmd_start()
    elif cmd == "stop":
        self.cmd_stop()
    elif cmd == "restart":
        self.cmd_restart()
    elif cmd == "status":
        self.cmd_status()
    elif cmd == "smi":
        self.cmd_smi()
    elif cmd == "config":
        if len(args) == 0:
            print("❌ 请指定子命令: get | set")
            return
        subcmd = args[0]
        if subcmd == "get":
            self.cmd_config_get(args[1] if len(args) > 1 else None)
        elif subcmd == "set":
            if len(args) < 3:
                print("❌ 语法错误: arxiv-config set <key> <value>")
                return
            self.cmd_config_set(args[1], args[2])
        else:
            print(f"❌ 未知子命令: {subcmd}")
    elif cmd == "keywords":
        self.cmd_keywords(args[0] if args else None, args[1] if len(args) > 1 else None)
    elif cmd == "logs":
        lines = int(args[0]) if args and args[0].isdigit() else 10
        self.cmd_logs(lines)
    elif cmd == "ollama":
        self.cmd_ollama(args[0] if args else None)
    elif cmd == "help":
        self.cmd_help()
    else:
        print(f"❌ 未知命令: {cmd}")
        print("💡 使用 'arxiv-help' 查看帮助")

async def execute_async_cmd(self, cmd, *args):
    """执行异步命令"""
    if cmd == "report":
        if len(args) == 0:
            print("❌ 请指定 'am' 或 'pm'")
            return
        await self.cmd_report(args[0])
    elif cmd == "rn":
        await self.cmd_rn(args[0] if args else None)
    else:
        print(f"❌ 未知异步命令: {cmd}")

# 动态添加方法到类
ArxivCLI.execute_sync_cmd = execute_sync_cmd
ArxivCLI.execute_async_cmd = execute_async_cmd

if __name__ == "__main__":
    main()