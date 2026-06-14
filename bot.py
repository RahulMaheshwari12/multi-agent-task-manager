from dotenv import load_dotenv
from tools import get_tasks, get_overdue_tasks
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from graphs import run_pipeline
from database import get_setting, save_setting, get_overdue_tasks_db, get_tasks_db
from datetime import datetime, time, timedelta, timezone
import os 

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start command"""

    user_name = update.effective_chat.first_name or "there"

    message= f"""Welcome {user_name} to AI Task Manager:-

    I can help you manage your tasks.
    
    🤖 Chat with me directly:
    - "Create a high priority task for John to deploy frontend by Friday"
    - "Show my pending tasks"
    - "What should I focus on today?"
    - "Mark task 3 as completed"
    - "Find tasks assigned to John"
    - "Plan a 3-day trip to Paris next month"

    📋 Quick Commands:
    /tasks - View all pending tasks
    /overdue - View overdue tasks
    /summary - Generate manual morning overview summary
    /help - Shows command list 

    Let's get started! 🚀"""

    await update.message.reply_text(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /help command"""

    message = """Help AI Task Manager:-
    
    📋 Commands:
    /start - Welcome message
    /tasks - View all pending tasks
    /overdue - View overdue tasks
    /summary - Generate manual morning overview summary
    /help - Show this message

    💬 Try asking me like this:
    - "Create a task for John to fix login bug by Friday"
    - "Show all high priority tasks"
    - "Mark task 1 as completed"
    - "Delete task 3"
    - "Update task 2 priority to high"
    - "What should I focus on today?"
    - "Show tasks assigned to Rahul"
    - "Plan my week"
    - "Plan a 3-day weekend trip to Paris next month" """

    await update.message.reply_text(message)

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /tasks command"""
    await update.message.reply_text("📋 Fetching your tasks...")

    try:
        tasks = await get_tasks.ainvoke({"status": "pending"}) 
        if tasks:
            await update.message.reply_text(f"Pending tasks:\n\n{tasks}")
        else:
            await update.message.reply_text("No pendding tasks found.")
    except Exception as e:
        await update.message.reply_text(f"Error fetching task : {str(e)}")

async def overdue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /overdue command"""
    await update.message.reply_text("📋 Fetching your overdue tasks...")

    try:
        overdue_tasks = await get_overdue_tasks.ainvoke({})
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
        results = await run_pipeline(user_message)
        response = results.get("final_response" , "Sorry, I could not process that.")
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"Error fetching your request: {str(e)}")

async def send_summary(context: ContextTypes.DEFAULT_TYPE):
    """fetch all pending and overdue tasks and send an morning summary to user"""
    chat_id = await get_setting("telegram_chat_id")
    if not chat_id:
        print("⚠️ No Telegram chat ID saved in settings. Skipping morning summary.")
        return
    try:
        pending = await get_tasks_db("pending")
        overdue = await get_overdue_tasks_db()

        today_str = datetime.now().strftime("%Y-%m-%d (%A)")
        prompt = f"""
        Today is {today_str}. 
        Please act as my personal productivity coach and write a warm, encouraging morning overview.
        Keep it positive, highly actionable, and formatted nicely for a mobile Telegram screen.
        DO NOT call any database write tools or create any new tasks.
        Pending Tasks: {pending}
        Overdue Tasks: {overdue}
        """

        result = await run_pipeline(prompt)
        response = result.get("final_response", "Sorry, I could not process the summary.")
        await context.bot.send_message(chat_id=chat_id, text=response)

    except Exception as e:
        print(f"❌ Error in morning summary job: {str(e)}")

        try:
            await context.bot.send_message(
            chat_id=chat_id, 
            text="⚠️ Good morning! I had trouble analyzing your tasks today. Don't worry, you can still view them on your web dashboard."
        )
        except Exception:
            pass

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows manual triggering of the morning summary for testing"""
    await update.message.reply_text("📋 Compiling your morning summary...")

    chat_id = str(update.effective_chat.id)
    await save_setting("telegram_chat_id", chat_id)

    
    await send_summary(context)


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
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    job_queue = app.job_queue
    IST = timezone(timedelta(hours=5, minutes=30))  # set timezone to India standard time

    job_queue.run_daily(send_summary, time(9, 0, 0, tzinfo=IST))
    print("📅 Morning summary scheduler registered for 9:00 AM IST")

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
