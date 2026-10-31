# tgbot2notion (Telegram to Notion Social Inspiration Collector)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.12+](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![CI: Syntax Check](https://github.com/shitouuuuu/tgbot2notion/actions/workflows/ci.yml/badge.svg)](https://github.com/shitouuuuu/tgbot2notion/actions)

English | [简体中文](README.md)

---

A lightweight social bookmark and inspiration collector designed for mobile browsing across social networks (Instagram, Threads, Twitter/X, YouTube, Facebook, and more). 

Simply tap **"Share to Telegram"** in any mobile app and send the link to your personal bot. It automatically parses titles, summaries, cover images, full multi-image galleries, hashtags, and your personal notes directly into a beautifully formatted Notion database.

> 💡 **Lightweight Design Principle**: This project focuses on **bookmarking and inspiration curation**. It only extracts public structured metadata (OpenGraph) and external preview URLs. It **never downloads, stores, or re-hosts heavy binary media files (videos/audio/images)**, resulting in minimal resource usage (~30MB RAM) and zero disk overhead.

---

## ✨ Key Features

- **Deep Multi-Platform Parsing**:
  - 🐦 **Twitter / X Deep Scraping**: Powered by the FxTwitter API v2 engine. Extracts un-truncated long tweets, author handles, engagement metrics (e.g., `❤️ 12.5k · 🔁 3.2k · 🔖 1.1k`), and embeds all original photos into a multi-image gallery inside the Notion page.
  - 📸 **Instagram**: Seamless post & Reels parsing via official embed endpoints. Grabs full captions, embedded hashtags, and HD covers without login credentials.
  - 🧵 **Threads**: Adaptive support for both `threads.com` and `threads.net` links with redirect resolution.
  - ▶️ **YouTube** / 📘 **Facebook** / 📺 **Bilibili** / 📕 **Xiaohongshu (RED)** and standard web pages.
- **Bidirectional Smart Hashtag Parsing**: Add any `#tag` (e.g., `#design #inspiration`) when sharing via Telegram. The bot automatically strips hashtags from your note and merges them with post hashtags into Notion's `Tags` (multi-select) field.
- **Deduplication & Anti-Redundancy**: If a URL has already been bookmarked, the bot notifies you with a direct link to the existing Notion page instead of creating duplicate records.
- **URL Sanitization & Note Separation**: Automatically strips tracking query parameters (`utm_*`, `igsh`, `fbclid`, `si`, `xmt`, etc.). Supports sharing thoughts alongside links (e.g., `"Great layout concept https://..."`), neatly separated into Notion notes.
- **Smart Notion Property Mapping**: Intelligently adapts to English and Chinese database properties (`Title`, `URL`, `Platform`, `Tags`, `Summary`, `User Note`, `Saved At`), mounting platform emoji icons and external cover art.
- **Interactive Telegram UI**: Native Blockquote formatting, quick inline buttons to open the Notion page or original post, and a `/stats` command dashboard summarizing your collection by platform.
- **Security & Proxy Support**: Restricts bot access using `ALLOWED_USER_IDS` whitelist. Optional HTTP/HTTPS proxy support for restricted networks.

---

## 📋 Notion Database Schema & Recommended Views

### 1. Standard Database Properties Schema
Create a Notion database with the following properties (case-insensitive and compatible with English/Chinese aliases):

| Property Name | Compatible Aliases | Property Type | Description |
| :--- | :--- | :--- | :--- |
| **Title** | `Name` / `名称` / `标题` | **Title** (Required) | Extracted post title or first sentence |
| **Platform** | `来源` / `Source` / `平台` | **Select** | Source platform (Instagram, Twitter, Threads, etc.) |
| **Tags** | `标签` / `分类` / `Tag` | **Multi-select** | Merged category tags (supports `#hashtag` parsing) |
| **URL** | `Link` / `Url` / `原链接` | **URL** | Sanitized, clean original link |
| **Saved At** | `Date` / `Time` / `时间` | **Date** | Timestamp when bookmarked |
| **User Note** | `Note` / `备注` / `批注` | **Text (Rich Text)** | Personal thoughts sent along with the link |
| **Summary** | `Description` / `摘要` / `内容` | **Text (Rich Text)** | Full post caption or content summary |

---

### 2. Recommended Database Views

We recommend setting up three views in your Notion database for the best curation experience:

1. **Gallery Waterfall View (Highly Recommended)**:
   - **Layout**: Gallery
   - **Card preview**: Page cover
   - **Card size**: Medium or Large
   - **Properties displayed**: `Platform`, `Tags`, `Saved At`
   - *Result*: Your bookmarks from IG, X, and YouTube will appear as a sleek visual moodboard.
2. **Platform & Tag Board View**:
   - **Group by**: `Platform` or `Tags`.
3. **Chronological List View**:
   - **Sort**: `Saved At` descending (newest bookmarks on top).

---

## 🛠️ Prerequisites

### 1. Telegram Bot Token & User ID
1. Search for [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, and follow prompts to obtain your `TELEGRAM_BOT_TOKEN`.
2. Message [@userinfobot](https://t.me/userinfobot) to get your numeric Telegram ID (used for `ALLOWED_USER_IDS` whitelist access).

### 2. Notion Integration Secret & Database ID
1. Visit [Notion My Integrations](https://www.notion.so/my-integrations), click **+ New integration**, name it (e.g., `Telegram Collector`), and copy the **Internal Integration Secret** (`NOTION_TOKEN`).
2. Open your target Notion Database, click `...` in the upper-right corner -> **Connect to** -> select your integration.
3. Copy the database link. The 32-character string in the URL is your `NOTION_DATABASE_ID`:
   - Example: `https://www.notion.so/workspace/`**`a1b2c3d4e5f64a7b8c9d0e1f2a3b4c5d`**`?v=...`

---

## 🚀 Deployment

### Option 1: Docker Compose (Recommended)

```bash
git clone https://github.com/shitouuuuu/tgbot2notion.git
cd tgbot2notion

# Configure environment variables
cp .env.example .env
nano .env

# Build and start in background
docker compose up -d

# Check logs
docker compose logs -f
```

---

### Option 2: Python Virtual Environment + Systemd

```bash
git clone https://github.com/shitouuuuu/tgbot2notion.git
cd tgbot2notion

# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
nano .env

# 3. Configure systemd service
sudo cp tgbot2notion.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tgbot2notion

# Inspect status and live logs
sudo systemctl status tgbot2notion
sudo journalctl -u tgbot2notion -f
```

---

## 📄 Disclaimer

1. This project is intended solely for personal study, research, and bookmark curation. It is open-sourced under the MIT License.
2. This tool only retrieves public OpenGraph metadata and URLs. It does not download, store, host, or redistribute copyrighted multimedia content.
3. Users must comply with the Terms of Service of target platforms and applicable local laws. The author assumes no legal liability for improper usage of this tool.

---

## 📜 License

Distributed under the [MIT License](LICENSE).
