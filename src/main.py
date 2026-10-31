import logging
import sys
from telegram import BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from src import config
from src.bot.handlers import start_command, help_command, stats_command, button_callback, handle_message

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('tgbot2notion')

async def post_init(application):
    """自动注册 Telegram 客户端左下角的快捷命令菜单"""
    commands = [
        BotCommand("start", "🏠 帮助与使用指南"),
        BotCommand("stats", "📊 查看灵感库统计"),
        BotCommand("help", "💡 支持的平台与格式"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        logger.info("已成功为 Telegram 注册菜单命令列表")
    except Exception as e:
        logger.warning(f"设置快捷命令菜单失败: {e}")

def main():
    if not config.validate_config():
        sys.exit(1)

    logger.info("正在启动 tgbot2notion 服务...")
    if config.ALLOWED_USER_IDS:
        logger.info(f"已启用用户白名单，允许的 User ID: {config.ALLOWED_USER_IDS}")
    else:
        logger.warning("未配置 ALLOWED_USER_IDS，当前对所有 Telegram 用户开放！")

    builder = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init)
    
    # 代理配置（可选）
    if config.PROXY:
        logger.info(f"已启用网络代理配置: {config.PROXY}")
        builder = builder.proxy(config.PROXY).get_updates_proxy(config.PROXY)

    app = builder.build()

    # 注册命令与事件处理器
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot 已进入轮询监听模式...")
    app.run_polling()

if __name__ == '__main__':
    main()
