import sqlite3
import random
import validators
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import aiosqlite

BOT_TOKEN = 'BOT_TOKEN'
DB_NAME = 'links_database.db'


async def add_article(user_id: int, url: str) -> bool:
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT INTO articles (user_id, url) VALUES (?, ?)",
                (user_id, url)
            )
            await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def check_article_exists(user_id: int, url: str) -> bool:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT 1 FROM articles WHERE user_id = ? AND url = ?",
            (user_id, url)
        ) as cursor:
            result = await cursor.fetchone()
            return result is not None


async def get_random_article(user_id: int) -> tuple[int, str] | None:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, url FROM articles WHERE user_id = ? ORDER BY RANDOM() LIMIT 1",
            (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result


async def delete_article(article_id: int, user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM articles WHERE id = ? AND user_id = ?",
            (article_id, user_id)
        )
        await db.commit()


def init_db_sync():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                UNIQUE(user_id, url)
            )
        ''')
        conn.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    start_text = (
        "Привет! я бот, который поможет не забыть прочитать статьи,\n"
        "найденные тобой в интернете :)\n"
        "- Чтобы я запомнил статью, достаточно передать мне ссылку\n"
        "на нее. К примеру https://example.com.\n"
        "- Чтобы получить случайную статью, достаточно передать мне\n"
        "команду /get_article.\n"
        "Но помни! отдавая статью тебе на прочтение, она больше не\n"
        "хранится в моей базе. Так что тебе точно нужно ее изучить"
    )
    await update.message.reply_text(start_text)


async def get_article_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    random_article = await get_random_article(user_id)
    if random_article:
        article_id, article_url = random_article
        response_text = f"Вы хотели прочитать:\n{article_url}\nСамое время это сделать!"
        await update.message.reply_text(response_text)
        await delete_article(article_id, user_id)
    else:
        response_text = "Вы пока не сохранили ни одной статьи :) Если нашли что-то стоящее, я жду!"
        await update.message.reply_text(response_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text
    if validators.url(message_text):
        url = message_text
        exists = await check_article_exists(user_id, url)
        if exists:
            response_text = "Упс, вы уже это сохраняли :)"
            await update.message.reply_text(response_text)
        else:
            added = await add_article(user_id, url)
            if added:
                response_text = "Сохранил, спасибо!"
                await update.message.reply_text(response_text)
            else:
                await update.message.reply_text("Произошла ошибка при сохранении ссылки (возможно, дубликат).")
    else:
        pass


def main():
    init_db_sync()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("get_article", get_article_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Starting bot...")
    application.run_polling()


if __name__ == '__main__':
    main()