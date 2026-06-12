from dotenv import load_dotenv
from tools import get_tasks, get_overdue_tasks
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from graphs import run_pipeline
import os 
import asyncio

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start command"""

    user_name = update.effective_chat.first_name or "there"

    message= f"""Welcome {user_name} to AI Task Manager:-

    I can help you manage you task.
    
    🤖 Just tell me what you need:
    - "Create a high priority task for John to deploy frontend by Friday"
    - "Show my pending tasks"
    - "What should I focus on today?"
    - "Mark task 3 as completed"
    - "Find tasks assigned to John"

    📋 Quick Commands:
    /tasks - View all pending tasks
    /overdue - View overdue tasks
    /help - Show this message

    Let's get started! 🚀"""

    await update.message.reply_text(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /help command"""

    message = """Help AI Task Manager:-
    
    📋 Commands:
    /start - Welcome message
    /tasks - View all pending tasks
    /overdue - View overdue tasks
    /help - Show this message

    💬 Natural Language Examples:
    - "Create a task for John to fix login bug by Friday"
    - "Show all high priority tasks"
    - "Mark task 1 as completed"
    - "Delete task 3"
    - "Update task 2 priority to high"
    - "What should I focus on today?"
    - "Show tasks assigned to Rahul"
    - "Plan my week" """

    await update.message.reply_text(message)

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /tasks command"""
    await update.message.reply_text("📋 Fetching your tasks...")

    try:
        tasks = get_tasks.invoke({"status": "Pending"}) 
        if tasks:
            await update.message.reply_text(f"Pending tasks:\n\n{tasks}")
        else:
            await update.message.reply_text("No pedding task found.")
    except Exception as e:
        await update.message.reply_text(f"Error fetching task : {str(e)}")

async def overdue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /overdue command"""
    await update.message.reply_text("📋 Fetching your overdue tasks...")

    try:
        overdue_tasks = get_overdue_tasks()
        if overdue_tasks:
            await update.message.reply_text(f"Overdue Tasks:\n\n{overdue_tasks}")
        else:
            await update.message.reply_text("No overdue tasks found.")
    except Exception as e:
        await update.message.reply_text(f"Error fetching overdue task: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles users message"""

    user_message = update.message.text

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    await update.message.reply_text("🤔 Processing your request...")

    try:
        results = run_pipeline(user_message)
        responce = results.get("final responce" , "Sorry, I could not process that.")
        await update.message.reply_text(responce)
    except Exception as e:
        await update.message.reply_text(f"Error fetching your request: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    print(f"Error: {context.error}")

def run_bot():
    """Start the telegram bot."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file")
    
    print("🤖 Starting Telegram bot...")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("overdue", overdue_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    USE_WEBHOOK = os.getenv("USE_WEBHOOK", "false").lower() == "true"

    if USE_WEBHOOK:
        WEBHOOK_URL = os.getenv("WEBHOOK_URL")
        app.run_webhook(
            listen="0.0.0.0",
            port=8443,
            webhook_url=f"{WEBHOOK_URL}/webhook"
        )
    else:
        print("✅ Bot is running with polling...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_bot()
