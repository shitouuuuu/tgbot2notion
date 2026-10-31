import html
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src import config
from src.parsers.extractor import extract_url_and_note, fetch_metadata
from src.services.notion import NotionService, PLATFORM_ICONS

logger = logging.getLogger(__name__)
notion_service = NotionService()

def check_permission(user_id: int) -> bool:
    """检查用户白名单"""
    if not config.ALLOWED_USER_IDS:
        return True
    return user_id in config.ALLOWED_USER_IDS

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """优雅的 /start 欢迎面板"""
    user = update.effective_user
    user_id = user.id if user else 0
    
    if not check_permission(user_id):
        await update.message.reply_text(
            f"⛔️ <b>访问受限</b>\n\n你的 Telegram User ID 为：<code>{user_id}</code>\n请在服务器的 <code>.env</code> 文件中将此 ID 添加到 <code>ALLOWED_USER_IDS</code>。",
            parse_mode=ParseMode.HTML
        )
        return

    notion_url = f"https://notion.so/{config.NOTION_DATABASE_ID}"
    keyboard = [
        [
            InlineKeyboardButton("📓 打开 Notion 灵感库", url=notion_url),
            InlineKeyboardButton("📊 查看库内统计", callback_data="show_stats")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"✨ <b>你好，{html.escape(user.first_name)}！欢迎使用 Notion 灵感收藏助手</b>\n\n"
        "专为你手机端的社交灵感而打造，零大文件下载，轻量纯书签整理。\n\n"
        "💡 <b>核心功能一览</b>：\n"
        "• <b>一键自动收录</b>：浏览 Instagram、Threads、Facebook、Twitter、YouTube 等 App 时，点击「分享到 Telegram」直接发送给我即可自动归档。\n"
        "• <b>个人感想批注</b>：在分享文本前或后加上你的感想（如：<code>“构图思路很棒 https://...”</code>），会自动提取为独立批注。\n"
        "• <b>自动分类标签</b>：消息中可附带 <code>#标签</code>（如 <code>#设计 #灵感</code>），会自动存入 Notion 的 Tags 多选字段。\n"
        "• <b>智能防重</b>：同一链接重复发送时，会自动检测并提示已有页面，避免数据堆叠冗余。\n\n"
        "👇 随时点击下方按钮可直达你的 Notion 数据库或查看统计："
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """支持平台与使用指南"""
    user_id = update.effective_user.id if update.effective_user else 0
    if not check_permission(user_id):
        return

    help_text = (
        "📖 <b>支持的平台与格式一览</b>\n\n"
        "• 📸 <b>Instagram</b>：帖子 / Reels 链接（免登录抓取文案与封面）\n"
        "• 🧵 <b>Threads</b>：动态 / 帖子链接（支持 threads.com & threads.net）\n"
        "• 🐦 <b>Twitter / X</b>：推文分享链接（完整抓取作者与推文正文）\n"
        "• 📘 <b>Facebook</b>：帖子 / 视频分享链接\n"
        "• ▶️ <b>YouTube</b>：视频 / Shorts 链接\n"
        "• 📺 <b>Bilibili</b>：视频 / 动态链接\n"
        "• 📕 <b>小红书</b>：笔记链接\n"
        "• 🌐 <b>通用网页</b>：博客文章、新闻与官网\n\n"
        "💡 <b>高级用法技巧</b>：\n"
        "1. <b>打标签</b>：在消息内附带 <code>#设计 #前端</code>，自动写入 Notion 标签库。\n"
        "2. <b>写心得</b>：直接输入中文感想与链接，自动提取为醒目的个人批注卡片。\n"
        "3. <b>自动清洗</b>：自动剥离跟踪参数（如 utm_*, igsh 等），保证 Notion 链接干净整洁。"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """灵感库统计概览"""
    user_id = update.effective_user.id if update.effective_user else 0
    if not check_permission(user_id):
        return

    msg = await update.message.reply_text("📊 正在统计 Notion 灵感库数据...", parse_mode=ParseMode.HTML)
    await render_stats(msg)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理快捷按钮回调"""
    query = update.callback_query
    await query.answer()
    if query.data == "show_stats":
        await render_stats(query.message)

async def render_stats(message):
    """渲染统计卡片"""
    total, platforms = await notion_service.get_stats()
    notion_url = f"https://notion.so/{config.NOTION_DATABASE_ID}"
    keyboard = [[InlineKeyboardButton("📓 前往 Notion 灵感库", url=notion_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    plat_lines = []
    if platforms:
        for p_name, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True):
            icon = PLATFORM_ICONS.get(p_name, '🌐')
            plat_lines.append(f"  {icon} <b>{p_name}</b>：<code>{count}</code> 篇")
    else:
        plat_lines.append("  <i>（暂无各分类统计数据）</i>")

    stats_text = (
        "📊 <b>Notion 灵感库统计概览</b>\n\n"
        f"📦 <b>已累计收藏</b>：<code>{total}</code> 篇灵感\n\n"
        "<b>来源平台分布</b>：\n" + "\n".join(plat_lines)
    )
    await message.edit_text(stats_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理消息，包含防重复检测与优雅交互"""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    user_id = user.id if user else 0
    
    if not check_permission(user_id):
        await update.message.reply_text(f"⛔️ 访问受限。你的 Telegram ID: <code>{user_id}</code>", parse_mode=ParseMode.HTML)
        return

    text = update.message.text.strip()
    raw_url, user_note, tags = extract_url_and_note(text)
    
    if not raw_url:
        await update.message.reply_text(
            "ℹ️ <b>未检测到有效网址链接</b>\n\n请直接发送包含文章/帖子链接的消息，或在分享时选择我。",
            parse_mode=ParseMode.HTML
        )
        return

    status_msg = await update.message.reply_text("⚡ <i>正在查询与解析内容...</i>", parse_mode=ParseMode.HTML)
    
    try:
        # 1. 链接防重复检测（查重）
        existing = await notion_service.find_existing_bookmark(raw_url)
        if existing:
            created_str = ""
            if existing.get('created_time'):
                try:
                    dt = datetime.fromisoformat(existing['created_time'].replace('Z', '+00:00'))
                    created_str = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    created_str = existing['created_time']

            clean_title = html.escape(existing['title'])
            reply_text = (
                "⚠️ <b>该链接之前已收藏过</b>\n\n"
                f"📌 <b>原标题</b>\n"
                f"<blockquote>{clean_title}</blockquote>\n\n"
                f"🕒 <b>原收藏时间</b>：<code>{created_str or '近期'}</code>\n\n"
                "<i>💡 为避免 Notion 数据库数据冗余，已自动为你跳过重复写入。</i>"
            )
            keyboard = [
                [
                    InlineKeyboardButton("📓 打开已有的 Notion 页面", url=existing['url']),
                    InlineKeyboardButton("🌐 访问原始帖子", url=raw_url)
                ]
            ]
            await status_msg.edit_text(
                reply_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=True
            )
            return

        # 2. 抓取元数据（深度解析推文多图、互动热度与平台正文自带标签）
        meta = await fetch_metadata(raw_url)
        
        # 智能合并用户输入的标签与帖子自带的标签（去重）
        combined_tags = list(dict.fromkeys(tags + meta.get('tags', [])))

        # 3. 保存到 Notion（包含 Tags、多图、互动热度）
        page_url = await notion_service.save_bookmark(
            title=meta['title'],
            url=meta['url'],
            platform=meta['platform'],
            summary=meta['description'],
            user_note=user_note,
            image_url=meta['image_url'],
            tags=combined_tags,
            extra_images=meta.get('extra_images', []),
            stats=meta.get('stats', '')
        )
        
        # 4. 构造精美卡片式响应
        icon = PLATFORM_ICONS.get(meta['platform'], '🌐')
        clean_title = html.escape(meta['title'])
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        reply_text = (
            "✨ <b>灵感已成功收藏 · Saved to Notion</b>\n\n"
            f"📌 <b>标题</b>\n"
            f"<blockquote>{clean_title}</blockquote>\n\n"
            f"🏷️ <b>来源平台</b>：{icon} <b>#{meta['platform']}</b>\n"
        )
        
        if meta.get('stats'):
            reply_text += f"🔥 <b>互动热度</b>：<code>{meta['stats']}</code>\n"

        if combined_tags:
            tag_badges = " ".join([f"<code>#{html.escape(t)}</code>" for t in combined_tags[:6]])
            reply_text += f"🔖 <b>分类标签</b>：{tag_badges}\n"
            
        if meta.get('extra_images') and len(meta['extra_images']) > 1:
            reply_text += f"📸 <b>附带图集</b>：<code>已同步收录 {len(meta['extra_images'])} 张图片</code>\n"
            
        if user_note:
            clean_note = html.escape(user_note)
            reply_text += f"💬 <b>灵感批注</b>\n<blockquote>{clean_note}</blockquote>\n\n"
        else:
            reply_text += "\n"
            
        reply_text += f"🕒 <b>收藏时间</b>：<code>{time_str}</code>"

        # 底部内联按钮
        keyboard = [
            [
                InlineKeyboardButton("📓 打开 Notion 页面", url=page_url),
                InlineKeyboardButton("🌐 访问原始帖子", url=meta['url'])
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await status_msg.edit_text(
            reply_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.exception("保存到 Notion 失败")
        err_msg = html.escape(str(e))
        await status_msg.edit_text(
            f"❌ <b>收藏失败</b>\n<blockquote>{err_msg}</blockquote>\n\n原始链接：<code>{raw_url}</code>",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
