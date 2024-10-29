import requests
import logging
import schedule
import time
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = 'ВАШ_ТОКЕН'  # Замените на ваш токен

# Глобальная переменная для хранения данных о ценах и спредах
price_data = {}
spread_data = {}

# Функция для получения цен с бирж
async def fetch_prices():
    global price_data
    exchanges = {
        "CoinGecko": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,litecoin&vs_currencies=usd"
    }

    for exchange, url in exchanges.items():
        try:
            response = requests.get(url)
            if response.status_code == 200:
                price_data[exchange] = response.json()
                logger.info(f"Данные получены с {exchange}: {price_data[exchange]}")
            else:
                logger.error(f"Ошибка при получении данных с {exchange}: {response.status_code}")
        except Exception as e:
            logger.error(f"Ошибка при запросе к {exchange}: {e}")

def run_scheduler():
    schedule.every(1).minutes.do(fetch_prices)  # Обновление каждую минуту
    while True:
        schedule.run_pending()
        time.sleep(1)

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Получить цены", callback_data='get_prices')],
        [InlineKeyboardButton("Установить интервал обновления", callback_data='set_interval')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Привет! Я бот для криптоарбитража.', reply_markup=reply_markup)

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'get_prices':
        get_prices(query.message.chat_id)
    elif query.data == 'set_interval':
        query.edit_message_text(text="Введите интервал обновления в минутах:")

def get_prices(chat_id):
    if not price_data:
        updater.bot.send_message(chat_id, "Данные еще не загружены. Пожалуйста, подождите.")
        return

    response_message = "Цены на монеты:\n"
    
    for exchange in price_data.keys():
        response_message += f"{exchange}:\n"
        for coin, data in price_data[exchange].items():
            response_message += f"{coin.capitalize()}: ${data['usd']}\n"
    
    updater.bot.send_message(chat_id, response_message)

def set_interval(update: Update, context: CallbackContext) -> None:
    if len(context.args) != 1 or not context.args[0].isdigit():
        update.message.reply_text("Используйте: /set_interval <minutes>")
        return

    interval = int(context.args[0])
    schedule.clear()  # Очистка предыдущих заданий
    schedule.every(interval).minutes.do(fetch_prices)
    
    update.message.reply_text(f"Интервал обновления установлен на {interval} минут(ы).")

def main() -> None:
    global updater
    updater = Application.builder().token(TOKEN).build()
    
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    
    # Обработка нажатий кнопок
    dispatcher.add_handler(CallbackQueryHandler(button))
    
    # Запуск планировщика в отдельном потоке
    Thread(target=run_scheduler).start()

    updater.run_polling()

if __name__ == '__main__':
    fetch_prices()  # Первоначальная загрузка данных
    main()
