import requests
import logging
import schedule
import time
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = '7494647108:AAF72N--PTZOFCaRbqKPn4v377aJ2ADIwsA'  # Замените на ваш токен

# Глобальная переменная для хранения данных о ценах и спредах
price_data = {}
spread_data = {}

# Функция для получения цен с бирж
def fetch_prices():
    global price_data
    exchanges = {
        "ByBit": "https://api.bybit.com/v2/public/tickers",
        "MEXC": "https://www.mexc.com/api/v2/market/tickers",
        "HTX": "https://api.hbg.com/market/tickers",
        "BitGet": "https://api.bitget.com/api/v1/market/tickers",
        "KuCoin": "https://api.kucoin.com/api/v1/market/allTickers",
        "BingX": "https://api.bingx.com/api/v1/market/tickers",
        "Gate.io": "https://api.gate.io/api2/1/tickers",
        "OKX": "https://www.okx.com/api/v5/market/tickers"
    }

    for exchange, url in exchanges.items():
        try:
            response = requests.get(url)
            if response.status_code == 200:
                price_data[exchange] = response.json()
                calculate_spreads()  # Вычисляем спреды после получения данных
            else:
                logger.error(f"Ошибка при получении данных с {exchange}: {response.status_code}")
        except Exception as e:
            logger.error(f"Ошибка при запросе к {exchange}: {e}")

def calculate_spreads():
    global spread_data
    spread_data.clear()  # Очищаем предыдущие данные о спредах

    for exchange in price_data.keys():
        try:
            if 'result' in price_data[exchange]:
                for ticker in price_data[exchange]['result']:
                    if 'ask' in ticker and 'bid' in ticker:
                        ask = float(ticker['ask'])
                        bid = float(ticker['bid'])
                        spread = ask - bid
                        percent_spread = (spread / ask) * 100 if ask != 0 else 0  # Избегаем деления на ноль

                        spread_data[ticker['symbol']] = {
                            'price': ask,
                            'exchange': exchange,
                            'percent_spread': percent_spread,
                            'blockchain': ticker.get('blockchain', 'Неизвестно'),  # Информация о блокчейне
                            'withdraw_fee': ticker.get('withdraw_fee', 'Неизвестно')  # Комиссия за вывод
                        }
            else:
                logger.warning(f"Нет данных 'result' на {exchange}.")
        
        except Exception as e:
            logger.error(f"Ошибка при вычислении спредов для {exchange}: {e}")

def run_scheduler():
    schedule.every(1).minutes.do(fetch_prices)  # Обновление каждую минуту
    while True:
        schedule.run_pending()
        time.sleep(1)

def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Получить цены", callback_data='get_prices')],
        [InlineKeyboardButton("Установить интервал обновления", callback_data='set_interval')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Привет! Я бот для криптоарбитража.', reply_markup=reply_markup)

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

    response_message = ""
    for exchange, data in price_data.items():
        response_message += f"{exchange}:\n"
        if 'result' in data:  # Проверка наличия ключа 'result'
            for ticker in data['result']:
                symbol = ticker['symbol']
                if symbol in spread_data:
                    spread_info = spread_data[symbol]
                    response_message += (
                        f"{symbol}: {ticker['last_price']}, "
                        f"Блокчейн: {spread_info['blockchain']}, "
                        f"Комиссия за вывод: {spread_info['withdraw_fee']}, "
                        f"Процент спреда: {spread_info['percent_spread']:.2f}%\n"
                    )
    
    updater.bot.send_message(chat_id, response_message)

def set_interval(update: Update, context: CallbackContext) -> None:
    if len(context.args) != 1 or not context.args[0].isdigit():
        update.message.reply_text("Используйте: /set_interval <minutes>")
        return

    interval = int(context.args[0])
    schedule.clear()  # Очистка предыдущих заданий
    schedule.every(interval).minutes.do(fetch_prices)
    
    update.message.reply_text(f"Интервал обновления установлен на {interval} минут(ы).")

def show_spread(update: Update, context: CallbackContext) -> None:
    if not spread_data:
        update.message.reply_text("Спреды еще не загружены. Пожалуйста, подождите.")
        return

    response_message = "Спреды по валютным парам:\n"
    
    for pair in spread_data.keys():
        price_info = spread_data[pair]
        response_message += (
            f"{pair}: {price_info['price']} на {price_info['exchange']}, "
            f"Процент спреда: {price_info['percent_spread']:.2f}%, "
            f"Блокчейн: {price_info['blockchain']}, Комиссия за вывод: {price_info['withdraw_fee']}\n"
        )

    updater.bot.send_message(update.message.chat_id, response_message)

def main() -> None:
    global updater
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("set_interval", set_interval))
    
    # Обработка нажатий кнопок
    dispatcher.add_handler(CallbackQueryHandler(button))
    
    # Команда для показа спреда
    dispatcher.add_handler(CommandHandler("show_spread", show_spread))

    # Запуск планировщика в отдельном потоке
    Thread(target=run_scheduler).start()

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    fetch_prices()  # Первоначальная загрузка данных
    main()
