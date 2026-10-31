# tgbot2notion (Telegram 社交灵感收藏助手)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.12+](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![CI: Syntax Check](https://github.com/shitouuuuu/tgbot2notion/actions/workflows/ci.yml/badge.svg)](https://github.com/shitouuuuu/tgbot2notion/actions)

[English](README_EN.md) | 简体中文

---

专为手机浏览社交网络（Instagram、Threads、Facebook、Twitter/X、YouTube 等）设计的轻量灵感收藏助手。在移动端 App 中点击「分享到 Telegram」直接发送给专属 Bot，即可自动提取标题、摘要、封面与你的个人批注并存入 Notion 数据库。

> 💡 **轻量设计原则**：本项目定位于**书签与灵感收录**，仅提取网页公开的结构化元数据（OpenGraph）和外部预览图 URL，**绝不下载、转存或分发大体积音视频/图片实体文件**，极低系统开销（仅占约 30MB 内存），零硬盘负担。

---

## ✨ 核心特性

- **多平台深度自适应解析**：
  - 🐦 **Twitter / X 深度抓取**：集成 FxTwitter API v2 深度端点，支持未截断长文案、作者 Handle、点赞/转推/收藏社交热度指标（如 `❤️ 12.5k · 🔁 3.2k`），并提取全部高清图集在 Notion 正文完整展示。
  - 📸 **Instagram**：帖子与 Reels 官方 Embed 接口解析，免登录抓取完整 Caption 文案、自带标签与高清封面。
  - 🧵 **Threads**：自适应支持 `threads.com` 与 `threads.net` 动态解析与短链重定向追踪。
  - ▶️ **YouTube** / 📘 **Facebook** / 📺 **Bilibili** / 📕 **小红书** 等主流平台。
- **双向智能 `#标签`（Hashtag Parsing）**：支持在 Telegram 分享消息中附带任意 `#标签`（如 `#设计 #灵感`），并自动与原帖自带的标签深度融合去重，统一归纳至 Notion 的 `Tags`（多选）属性。
- **智能查重防冗余**：同一链接重复发送时，自动检测并提示已有页面直达按钮，避免 Notion 数据库数据重复堆积。
- **链接清洗与备注分离**：自动清除 URL 中的追踪参数（`utm_*`, `igsh`, `fbclid` 等）；支持连同个人感想一起发送（如：`“构图思路很棒 https://...”`），自动提取为 Notion 独立批注。
- **Notion 字段智能匹配**：自动适配中英文数据库属性字段（`名称/Title`, `URL`, `Platform`, `Tags`, `Summary`, `User Note`, `Saved At`），并自动挂载外部封面（Cover）与专属 Emoji 平台图标。
- **精美 Telegram 交互**：采用原生 Blockquote 卡片排版，提供快捷内联按钮直达 Notion 页面或原帖；内置 `/stats` 统计仪表盘，实时汇总各平台收录数量。
- **安全与代理支持**：配置 `ALLOWED_USER_IDS` 白名单，拦截未经授权的陌生用户调用；可选配置 HTTP/HTTPS 代理。

---

## 📋 开箱即用 Notion 数据库规范与视图推荐

### 1. 标准数据库属性结构（Properties Schema）
你可以新建一个空白 Notion Database，并确认包含以下字段（中英文命名均能自动智能匹配）：

| 字段名称 (推荐) | 兼容别名 | 属性类型 (Type) | 说明 |
| :--- | :--- | :--- | :--- |
| **Title** | `名称` / `标题` | **Title** (必填) | 自动提取的推文/帖子标题或首句 |
| **Platform** | `平台` / `来源` / `Source` | **Select** | 来源平台（如 Instagram, Twitter, Threads 等） |
| **Tags** | `标签` / `分类` / `Tag` | **Multi-select** | 智能合并的分类标签（支持 `#标签` 自动入库） |
| **URL** | `Url` / `Link` / `原链接` | **URL** | 清洗去追踪参数后的干净原始链接 |
| **Saved At** | `Date` / `保存时间` / `时间` | **Date** | 收藏入库时间（UTC/本地时间） |
| **User Note** | `Note` / `备注` / `批注` | **Text (Rich Text)** | 随链接一同发送的个人感想批注 |
| **Summary** | `Description` / `摘要` / `内容` | **Text (Rich Text)** | 帖子完整文案或内容概要 |

---

### 2. 画报级数据库视图配置指南

建议在你的 Notion 数据库中创建以下 3 种视图，体验极致的灵感收集流：

1. **画廊瀑布流（Gallery View · 强烈推荐）**：
   - 布局（Layout）：选择 **Gallery**
   - 卡片预览（Card preview）：选择 **Page cover**
   - 卡片尺寸（Card size）：选择 **Medium** 或 **Large**
   - 显示属性（Properties）：勾选 `Platform`、`Tags`、`Saved At`
   - *效果*：所有来自 IG、Threads、YouTube 的灵感将以高清社交海报的形式瀑布流排列。
2. **主题分类看板（Board View）**：
   - 分组依据（Group by）：按 `Platform`（来源平台）或 `Tags`（分类标签）分组。
3. **快速索引清单（List View）**：
   - 排序（Sort）：按 `Saved At` 降序排列（最新收藏置顶）。

---

## 🛠️ 部署前准备

### 1. Telegram Bot Token 与 ID
1. 在 Telegram 中找到 [@BotFather](https://t.me/BotFather)，发送 `/newbot`，按提示创建一个新 Bot 并获取 `TELEGRAM_BOT_TOKEN`。
2. 在 Telegram 中向 [@userinfobot](https://t.me/userinfobot) 发送任意消息，查询你的纯数字 ID（即 `ALLOWED_USER_IDS`，用于白名单拦截）。

### 2. Notion Integration 与 Database
1. 访问 [Notion My Integrations](https://www.notion.so/my-integrations)，点击 **+ New integration**，创建一个名为 `Telegram Collector` 的 Internal Integration，复制获取 **Internal Integration Secret**（即 `NOTION_TOKEN`）。
2. 在 Notion 中打开你要存放收藏的 Database，点击右上角 `...` -> **Connect to**（连接到）-> 选择刚才创建的 Integration。
3. 复制 Database 的网页链接，链接中 32 位的长字符串即为 `NOTION_DATABASE_ID`：
   - 链接格式示例：`https://www.notion.so/workspace/`**`a1b2c3d4e5f64a7b8c9d0e1f2a3b4c5d`**`?v=...`

---

## 🚀 部署方式

### 方式一：Docker Compose（推荐 · 一键启动）

```bash
git clone https://github.com/shitouuuuu/tgbot2notion.git
cd tgbot2notion

# 配置密钥
cp .env.example .env
nano .env

# 后台一键构建并启动
docker compose up -d

# 查看运行日志
docker compose logs -f
```

---

### 方式二：Python 虚拟环境 + Linux Systemd 常驻

```bash
git clone https://github.com/shitouuuuu/tgbot2notion.git
cd tgbot2notion

# 1. 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
nano .env

# 3. 配置 systemd 系统服务常驻后台
sudo cp tgbot2notion.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tgbot2notion

# 查看状态与实时日志
sudo systemctl status tgbot2notion
sudo journalctl -u tgbot2notion -f
```

---

## 📄 免责声明 / Disclaimer

1. 本项目仅供个人学习、研究与生产力书签整理使用，代码基于 MIT 协议开源。
2. 本工具仅抓取公开网页的 OpenGraph 基础元数据，不下载、不托管、亦不对外分发任何有版权的音视频及多媒体实体内容。
3. 用户在自建部署与使用时，须遵守目标平台的服务条款（Terms of Service）以及所在地区的法律法规，对于任何因不当使用该工具导致的后果，项目作者概不承担法律责任。

---

## 📜 许可证 / License

本项目采用 [MIT License](LICENSE) 授权许可。
