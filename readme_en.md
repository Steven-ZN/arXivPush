# arXiv Push - Time-Aware Iterative Search System

## 📋 Project Overview

arXiv Push is an intelligent arXiv paper push notification system featuring time-aware iterative search capabilities. The system automatically fetches the latest academic papers and generates structured summary reports using AI models.

## 🚀 v2.0 Major Update - Time-Aware Iterative Search Architecture

### ✨ Core Features

- **🎯 Time-Aware Search**: Based on current time with dynamic time window expansion
- **⚡ Latest-First Priority**: Sorted by `submitted_date` in descending order to ensure newest papers first
- **🔄 Dynamic Expansion**: Intelligent time window expansion mechanism until target quantity is met
- **🧠 Smart Deduplication**: Remove duplicate papers of different versions through `base_id`
- **🛡️ Fault Tolerance**: Multi-layer fallback strategy to ensure system stability

### 🏗️ Architecture Design

```
🎯 Starting Time-Aware Iterative Search
📅 Current Date: 2025-10-14
🎯 Target Papers: 20
🔍 Max Search Range: 7 days
============================================================
🔍 [1/7] Search Window: 2025-10-13 ~ 2025-10-14 → 0 papers
🔍 [2/7] Search Window: 2025-10-12 ~ 2025-10-13 → 0 papers
🔍 [3/7] Search Window: 2025-10-11 ~ 2025-10-12 → 18 papers ✅
🎉 Target 20 papers achieved!
📅 Time Range: 2025-10-11 ~ 2025-10-11
```

## 📁 File Update Description

### `arxiv_fetch.py` - Core Search Engine
### `arxiv-cli.py` - CLI System with Ollama Integration

#### `arxiv_fetch.py` New Features

##### 1. `iterative_time_aware_search()` Function
```python
def iterative_time_aware_search(cfg, target=20, max_days=7):
    """
    Time-aware iterative search architecture
    Prioritizes fetching latest papers, dynamically expands time window until conditions are met
    """
```

**Core Algorithm Flow**:
1. **Initialize Time Window**: `current_date = today()`, `time_window = 1`
2. **Iterative Search**: Execute independent search for each window and accumulate results
3. **Dynamic Expansion**: `time_window += 1` until target is reached
4. **Stop Condition**: `len(collected) >= target` or `time_window > max_days`
5. **Final Sorting**: `collected.sort(key=lambda p: p.published, reverse=True)`

##### 2. Refactored `fetch_window()` Function
```python
def fetch_window(cfg, since_dt_local, now_local):
    """
    Compatibility wrapper: Uses new time-aware iterative search
    """
    # Use new time-aware iterative search
    results = iterative_time_aware_search(
        cfg=cfg,
        target=max_items,
        max_days=7
    )
    return results
```

##### 3. New `fallback_search()` Function
```python
def fallback_search(cfg, max_items):
    """
    Simplified fallback search solution
    """
```

#### Technical Specifications

| Feature | Implementation | Status |
|---------|----------------|--------|
| **Latest-First Priority** | `sort_by=submittedDate descending` | ✅ |
| **Dynamic Time Window** | Expand `+1 day` per round | ✅ |
| **Deduplication Mechanism** | Through `base_id` set | ✅ |
| **Stop Condition** | ≥20 papers within last 7 days | ✅ |
| **Robustness** | API exception auto-retry ≤3 times | ✅ |

#### `arxiv-cli.py` Ollama Integration Features

##### 1. Automatic Ollama Service Management
```python
# Automatically check and start Ollama service on startup
def cmd_start(self):
    # Check and start Ollama service
    print("🤖 Checking Ollama service...")
    ollama_manager = create_ollama_manager(CFG)

    if not ollama_manager.start_service(auto_start=True):
        print("❌ Ollama service startup failed")
        return

    print("✅ Ollama service ready")
```

##### 2. Complete Ollama CLI Commands
```bash
# Ollama service management commands
arxiv-ollama          # View status
arxiv-ollama start    # Start service
arxiv-ollama stop     # Stop service
arxiv-ollama restart  # Restart service
arxiv-ollama test     # Test service
arxiv-ollama status   # Detailed status
```

##### 3. Smart Service Integration
- **Auto-startup**: Automatically checks and starts Ollama service when running `arxiv start`
- **Status monitoring**: Real-time monitoring of Ollama service status and model availability
- **Error handling**: Intelligent handling of Ollama service exceptions with detailed error messages
- **Configurable**: Support for custom Ollama host addresses and model selection

## 🔧 System Requirements

- Python 3.8+
- arXiv API client
- Ollama service (qwen2.5:7b model)
- Date-time processing library (python-dateutil)

## 📊 Performance Metrics

### Search Efficiency
- **Window Count**: Usually 2-3 windows to achieve 20 papers target
- **Timeliness**: All papers from last 3-7 days
- **Deduplication Effect**: Select 20 optimal papers from 30+ candidates
- **Search Time**: Complete single search < 30 seconds

### Test Results
```
🎯 Verification Results:
   📊 Paper Count: 20/20 (Target: ≥20 papers)
   🔄 Deduplication Effect: ✅ Through base_id deduplication
   ⏰ Time Strategy: ✅ Dynamic window expansion
   📅 Time Span: 1 day (2025-10-11 ~ 2025-10-11)
   📈 Latest-First Priority: ✅ Sorted by submitted_date descending
   🎯 Timeliness: 3 days ago (Target: ≤7 days) ✅
```

## 🔄 Compatibility

- ✅ **Fully Backward Compatible**: Seamless integration through original `fetch_window` interface
- ✅ **Smart Fallback Mechanism**: Auto-fallback to traditional search on exceptions
- ✅ **Configurable Parameters**: Support custom target quantity and search days
- ✅ **Detailed Log Output**: Complete search process visualization

## 🚀 Usage

### 1. System Deployment Steps

#### Environment Setup
```bash
# 1. Clone project
git clone <repository-url>
cd arxivpush-package

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure Discord Bot
cp .env.template .env
# Edit .env file, fill in Discord Bot Token

# 4. Configure system parameters
cp config.yaml.template config.yaml
# Edit config.yaml file, set push times, categories, etc.

# 5. Install Ollama (if not installed)
curl -fsSL https://ollama.com/install.sh | sh

# 6. Create command shortcuts
./install_commands.sh
```

#### Start System
```bash
# Start complete service (auto-starts Ollama)
arxiv start

# Check service status
arxiv status

# View real-time monitoring
arxiv smi
```

### 2. Programming Interface Usage

#### Basic Usage
```python
import arxiv_fetch

# Configuration parameters (fully customizable)
cfg = {
    'categories': ['cs.AI', 'cs.LG', 'cs.CL', 'cs.CV'],  # Customize any arXiv categories
    'digest_max_items': 20,
    'exclude': ['survey', 'review'],                     # Customize exclude keywords
    'timezone': 'Asia/Shanghai'
}

# Execute search
papers = arxiv_fetch.fetch_window(cfg, None, now_local)
print(f"Retrieved {len(papers)} latest papers")
```

#### Advanced Configuration
```python
# Direct call to time-aware search
papers = arxiv_fetch.iterative_time_aware_search(
    cfg=cfg,
    target=25,        # Custom target quantity
    max_days=10       # Custom max search days
)
```

### 3. Ollama Service Management

#### Command Line Management
```bash
# View Ollama status
arxiv-ollama

# Start/stop Ollama service
arxiv-ollama start
arxiv-ollama stop

# Test Ollama service
arxiv-ollama test

# View detailed status
arxiv-ollama status
```

#### Configuration File Settings
```yaml
# config.yaml
ollama:
  host: "http://127.0.0.1:11434"
  model: "qwen2.5:7b"

# Customize categories, keywords, and schedules
categories:
  - "cs.AI"
  - "cs.LG"
  - "cs.CL"
  - "cs.CV"  # Add/remove any categories

queries:
  - any: ["machine learning", "deep learning"]  # Customize keywords
  - all: ["transformer", "attention"]

exclude:
  - "survey"
  - "review"  # Customize exclude words
```

### 4. System Management Commands

#### Service Control
```bash
arxiv start     # Start service (includes Ollama)
arxiv stop      # Stop service
arxiv restart   # Restart service
arxiv status    # View status
arxiv smi       # Real-time monitoring
```

#### Report Management
```bash
# Manually generate reports
arxiv report am    # Generate morning report
arxiv report pm    # Generate evening report

# Run immediately
arxiv rn          # Smart判断 morning/evening report
arxiv rn am       # Force generate morning report
```

#### Configuration Management
```bash
# View configuration
arxiv config get
arxiv config get categories

# Modify configuration
arxiv config set digest_max_items 25

# Keyword management (fully customizable)
arxiv keywords add-or "keyword1,keyword2"  # Add OR keywords
arxiv keywords add-and "keyword1,keyword2" # Add AND keywords
arxiv keywords exclude "word1,word2"       # Add exclude words
```

## 📈 Changelog

### v2.0 (2025-10-14)
- ✨ New time-aware iterative search architecture
- 🔄 Refactored core search algorithm
- 🛡️ Enhanced error handling and fallback mechanisms
- 📊 Optimized search performance and accuracy
- 📝 Improved log output and status display

### v1.0 (Historical Version)
- 🎯 Basic arXiv search functionality
- 🤖 Ollama integration
- 📱 Discord bot push notifications

## 🤝 Contributing

Welcome to submit Issues and Pull Requests to improve the project!

## 📄 License

MIT License