# Skills Trending Daily

> 自动追踪 skills.sh 技能排行榜，AI 智能分析，每日趋势报告邮件

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [使用方法](#使用方法)
- [GitHub Actions](#github-actions)
- [数据模型](#数据模型)
- [开发指南](#开发指南)
- [常见问题](#常见问题)

---

## 项目简介

**Skills Trending Daily** 是一个自动化技能趋势追踪系统。它每天从 [skills.sh/trending](https://skills.sh/trending) 获取最新的技能排行榜，使用 Apimart（`gemini-3-pro-preview`）对热门技能进行智能分析和分类，计算排名变化趋势，并通过 Resend 发送专业的 HTML 邮件报告。

### 为什么需要这个项目？

1. **开发者视角** - 快速了解哪些技能值得学习
2. **趋势洞察** - 捕捉新兴技术框架和工具的崛起
3. **智能总结** - AI 帮你理解每个技能解决什么问题
4. **自动化** - 无需手动查看网站，每天自动推送

---

## 功能特性

### 核心功能

| 功能 | 说明 |
|-----|------|
| **排行榜抓取** | 使用 Playwright 动态渲染获取 Top 100 技能排行 |
| **详情抓取** | 深度抓取热门技能的详细信息 |
| **AI 分析** | Apimart API（Gemini）自动总结、分类、提取价值 |
| **趋势计算** | 排名变化、安装量变化、新晋/掉榜检测 |
| **邮件报告** | 专业 HTML 邮件，每个技能可点击跳转 |
| **数据存储** | SQLite 存储历史数据，支持趋势分析 |

### 邮件报告内容

```
Skills Trending Daily - 2026-01-24
├── Top 20 Leaderboard（含 AI 总结）
│   ├── 技能名称（可点击跳转）、排名、安装量
│   ├── AI 一句话摘要
│   ├── 详细说明
│   └── 解决的问题标签
├── Rising Skills（上升幅度 Top 5）
├── Declining Skills（下降幅度 Top 5）
├── New & Dropped（新晋/掉榜）
└── Trending Up（安装量暴涨告警）
```

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Skills Trending 系统架构                   │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
  │   GitHub     │      │   Playwright │      │     LLM      │
  │   Actions    │ ──▶ │  Skills      │ ──▶ │  Summarizer │
  │  (Cron Daily)│      │  Fetcher     │      │ (Apimart)    │
  └──────────────┘      └──────┬───────┘      └──────┬───────┘
                               │                     │
                               ▼                     │
                        ┌──────────────┐              │
                        │   Detail     │              │
                        │  Fetcher     │              │
                        │  (Top N)     │              │
                        └──────┬───────┘              │
                               │                       │
                               └───────┬───────────────┘
                                       │
                                       ▼
                               ┌──────────────┐
                               │  Database    │
                               │  (SQLite)    │
                               └──────┬───────┘
                                      │
                                      ▼
                               ┌──────────────┐
                               │   Trend      │
                               │  Analyzer    │
                               └──────┬───────┘
                                      │
                                      ▼
                               ┌──────────────┐
                               │   HTML       │
                               │  Reporter    │
                               └──────┬───────┘
                                      │
                                      ▼
                               ┌──────────────┐
                               │   Resend     │
                               │   Sender     │
                               └──────┬───────┘
                                      │
                                      ▼
                               ──────► 您的邮箱
```

---

## 快速开始

### 环境要求

- Python 3.11+
- Apimart API Key
- Resend API Key

### 安装

```bash
# 克隆仓库
git clone https://github.com/geekjourneyx/trending-skills.git
cd trending-skills

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Keys
nano .env
```

### 运行

```bash
# 设置环境变量
export LLM_API_KEY="your_apimart_api_key"
export RESEND_API_KEY="your_resend_key"
export EMAIL_TO="your_email@example.com"

# 运行
python src/main_trending.py
```

---

## 配置说明

### 环境变量

| 变量 | 必需 | 说明 | 默认值 |
|-----|------|------|--------|
| `LLM_API_KEY` | Yes | Apimart API Key | - |
| `LLM_BASE_URL` | No | Chat Completions 端点 | `https://api.apimart.ai/v1/chat/completions` |
| `LLM_MODEL` | No | 模型名 | `gemini-3-pro-preview` |
| `LLM_MAX_RETRIES` | No | LLM 失败重试次数 | `3` |
| `LLM_TIMEOUT` | No | LLM 请求超时（秒） | `180` |
| `RESEND_API_KEY` | Yes | Resend API Key | - |
| `EMAIL_TO` | Yes | 收件人邮箱 | - |
| `RESEND_FROM_EMAIL` | No | 发件人邮箱 | `onboarding@resend.dev` |
| `DB_PATH` | No | 数据库路径 | `data/trends.db` |
| `DB_RETENTION_DAYS` | No | 数据保留天数 | `30` |
| `SURGE_THRESHOLD` | No | 暴涨阈值（比例） | `0.3` |

### Resend 配置

1. 注册 [Resend](https://resend.com)
2. 创建 API Key
3. 配置发件人域名（或使用默认的 `onboarding@resend.dev`）

---

## 使用方法

### 命令行运行

```bash
# 完整流程
python src/main_trending.py
```

### 数据库查询

```bash
# 查看最新数据日期
sqlite3 data/trends.db "SELECT date FROM skills_daily ORDER BY date DESC LIMIT 1;"

# 查看今日排行榜 Top 10
sqlite3 data/trends.db "SELECT rank, name, installs FROM skills_daily WHERE date = '2026-01-24' ORDER BY rank LIMIT 10;"

# 查看技能详情
sqlite3 data/trends.db "SELECT name, summary, category FROM skills_details WHERE name = 'remotion-best-practices';"
```

---

## GitHub Actions

### 自动化部署

1. Fork 本仓库
2. 在 GitHub Settings > Secrets and variables > Actions 中添加：
   - `LLM_API_KEY`
   - `RESEND_API_KEY`
   - `EMAIL_TO`（可选）
3. 启用 Actions

### 定时执行

默认每天 **UTC 02:00**（北京时间 10:00）自动运行。

修改时间：编辑 `.github/workflows/skills-trending.yml` 中的 `cron` 表达式。

### 手动触发

在 GitHub Actions 页面点击 "Run workflow" 按钮手动执行。

---

## 数据模型

### skills_daily - 每日快照

| 字段 | 类型 | 说明 |
|-----|------|------|
| `id` | INTEGER | 主键 |
| `date` | TEXT | 日期 (YYYY-MM-DD) |
| `rank` | INTEGER | 当日排名 |
| `name` | TEXT | 技能名称 |
| `owner` | TEXT | 拥有者 |
| `installs` | INTEGER | 安装量 |
| `installs_delta` | INTEGER | 安装量变化 |
| `installs_rate` | REAL | 安装量变化率 |
| `rank_delta` | INTEGER | 排名变化（正=上升） |
| `url` | TEXT | 技能链接 |

### skills_details - 技能详情

| 字段 | 类型 | 说明 |
|-----|------|------|
| `id` | INTEGER | 主键 |
| `name` | TEXT | 技能名称（唯一） |
| `summary` | TEXT | AI 一句话摘要 |
| `description` | TEXT | 详细描述 |
| `use_case` | TEXT | 使用场景 |
| `solves` | TEXT | JSON：解决的问题列表 |
| `category` | TEXT | 分类（英文） |
| `category_zh` | TEXT | 分类（中文） |
| `rules_count` | INTEGER | 规则数量 |
| `owner` | TEXT | 拥有者 |
| `url` | TEXT | 技能链接 |

### skills_history - 历史趋势

| 字段 | 类型 | 说明 |
|-----|------|------|
| `id` | INTEGER | 主键 |
| `skill_name` | TEXT | 技能名称 |
| `date` | TEXT | 日期 |
| `rank` | INTEGER | 当日排名 |
| `installs` | INTEGER | 安装量 |

---

## 开发指南

### 项目结构

```
skills-trending/
├── .github/workflows/
│   └── skills-trending.yml    # GitHub Actions 配置
├── src/
│   ├── config.py              # 配置管理
│   ├── database.py            # SQLite 操作
│   ├── skills_fetcher.py      # 榜单抓取（Playwright）
│   ├── detail_fetcher.py      # 详情抓取
│   ├── claude_summarizer.py   # AI 分析
│   ├── trend_analyzer.py      # 趋势计算
│   ├── html_reporter.py       # 邮件生成
│   ├── resend_sender.py       # 邮件发送
│   └── main_trending.py       # 主入口
├── plugins/
│   └── trending-skills/       # Claude Code Skill
├── data/
│   └── trends.db              # 数据库（运行时生成）
├── requirements.txt
├── .env.example
├── CHANGELOG.md
└── README.md
```

### 核心模块说明

| 模块 | 功能 |
|-----|------|
| `skills_fetcher.py` | 使用 Playwright 抓取 skills.sh 榜单，支持动态渲染 |
| `detail_fetcher.py` | 抓取单个技能的详细页面内容 |
| `claude_summarizer.py` | 调用 Apimart Chat Completions 分析技能内容 |
| `trend_analyzer.py` | 计算排名变化、新晋/掉榜、暴涨检测 |
| `html_reporter.py` | 生成专业 HTML 邮件（无 emoji，可点击链接） |
| `database.py` | SQLite 数据库操作，支持数据持久化 |

### 扩展开发

**新增数据源**
```python
# 修改 skills_fetcher.py
class SkillsFetcher:
    def __init__(self, timeout: int = 30000):
        self.trending_url = "your_custom_url"
```

**新增分析维度**
```python
# 修改 trend_analyzer.py
def calculate_trends(self, today_skills, today, ai_summary_map):
    # 添加新的分析逻辑
    pass
```

**自定义邮件样式**
```python
# 修改 html_reporter.py
def _get_header(self, date: str) -> str:
    # 修改样式和布局
    pass
```

---

## 常见问题

### 邮件没有收到？

1. 检查 Resend API Key 是否正确
2. 确认收件人邮箱地址
3. 查看垃圾邮件箱
4. 检查 GitHub Actions 日志

### Playwright 浏览器安装失败？

```bash
# 重新安装
playwright install chromium --with-deps
```

### 数据库文件在哪里？

默认位置：`data/trends.db`

### 如何查看历史数据？

```bash
sqlite3 data/trends.db
.tables
SELECT * FROM skills_daily ORDER BY date DESC LIMIT 10;
```

### 如何更改运行时间？

编辑 `.github/workflows/skills-trending.yml`：
```yaml
schedule:
  - cron: '0 2 * * *'  # UTC 时间，每天 02:00
```

---

## 打赏 Buy Me A Coffee

如果该项目帮助了您，请作者喝杯咖啡吧

### WeChat

<img src="https://raw.githubusercontent.com/geekjourneyx/awesome-developer-go-sail/main/docs/assets/wechat-reward-code.jpg" alt="微信打赏码" width="200" />

---

## 作者

- **作者**: `geekjourneyx`
- **X (Twitter)**: https://x.com/seekjourney
- **公众号**: 极客杰尼

关注公众号，获取更多 AI 编程、AI 工具与 AI 出海建站的实战分享：

<p>
<img src="https://raw.githubusercontent.com/geekjourneyx/awesome-developer-go-sail/main/docs/assets/qrcode.jpg" alt="公众号：极客杰尼" width="180" />
</p>

---

## License

[MIT](LICENSE)

---

## 致谢

- [skills.sh](https://skills.sh) - 技能数据来源
- Apimart - LLM API 网关（Gemini）
- [Resend](https://resend.com) - 邮件服务
- [Playwright](https://playwright.dev) - 浏览器自动化
