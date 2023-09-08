import os, time, telebot, json, datetime, sqlite3, requests
from telebot import types
from currency_symbols import CurrencySymbols

instraction_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'pictures', 'instraction.jpg'))


conn = sqlite3.connect('bems', check_same_thread=False)
cursor = conn.cursor()


def db_table_val(user_id: int, name: str, username: str, last_usage: datetime.datetime) -> None:
    try:
        cursor.execute('INSERT INTO users (user_id, name, username, last_usage) VALUES (?, ?, ?, ?)',
                       (user_id, name, username, last_usage))
    except sqlite3.IntegrityError:
        cursor.execute('UPDATE users SET last_usage = ? WHERE id = ?', (last_usage, user_id))
    conn.commit()


with open('config.json', 'r', encoding='utf-8') as file:
    lib = json.load(file)

with open('ratio.json', 'r', encoding='utf-8') as file:
    items = json.load(file)

bot = telebot.TeleBot(lib['token'])


@bot.message_handler(commands=['start'])
def start(message: telebot.types.Message) -> None:
    bot.send_message(message.chat.id, lib['start_message'], parse_mode='html',
                     reply_markup=menu_keyboard)
    db_table_val(message.from_user.id, message.from_user.first_name,
                 message.from_user.username, datetime.datetime.now())


def create_keyboard_buttons(titles: list[str]) -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons: list[types.KeyboardButton] = []
    for i in range(len(titles)):
        buttons.append(types.KeyboardButton(text=titles[i]))
    markup.add(*buttons)
    return markup


menu_keyboard: types.ReplyKeyboardMarkup = create_keyboard_buttons([
                         lib['button_text1'], lib['button_text2'], lib['button_text3'],
                         lib['button_text4'], lib['button_text5'], lib['button_text6']
                     ])

items_keyboard: types.ReplyKeyboardMarkup = create_keyboard_buttons([
                lib['item_text1'], lib['item_text2'], lib['item_text3'],
                lib['item_text4'], lib['item_text5']
            ])

back_keyboard: types.ReplyKeyboardMarkup = create_keyboard_buttons([lib['back_button_text1'],
                                                                    lib['back_button_text2']])


delivery_keyboard: types.ReplyKeyboardMarkup = create_keyboard_buttons([
                lib['delivery_type1'], lib['delivery_type2'],
                lib['back_button_text1'], lib['back_button_text2']])


@bot.message_handler(content_types=['text'])
def menu(message: telebot.types.Message) -> None:
    if message.text == lib['button_text1']:
        time.sleep(0.3)
        bot.send_photo(message.chat.id, photo=open(instraction_path, 'rb'), parse_mode='html')
        return
    if message.text == lib['button_text2']:
        currency = requests.get('https://www.cbr-xml-daily.ru/daily_json.js').json()
        k: float = currency['Valute']['CNY']['Value']
        bot.send_message(message.chat.id, lib['current_rate'] + str(round(k + lib['currency_interest'], 1)) +
                         f' {CurrencySymbols.get_symbol("RUB")}')
        return
    if message.text == lib['button_text3']:
        time.sleep(0.3)
        bot.send_message(message.chat.id, lib['item_category'],
                         parse_mode='html', reply_markup=items_keyboard)
        bot.register_next_step_handler(message, item_menu)
        return
    if message.text == lib['button_text4']:
        time.sleep(0.3)
        bot.send_message(message.chat.id, lib["ask_questions"])
        time.sleep(0.5)
        bot.send_contact(message.chat.id, '+79957800448', 'BEMS', 'Manager')
        return
    if message.text == lib['button_text5']:
        time.sleep(0.3)
        bot.send_message(message.chat.id, lib["order_info"])
        time.sleep(0.5)
        bot.send_contact(message.chat.id, '+79957800448', 'BEMS', 'Manager')
        return
    if message.text == lib['button_text6']:
        time.sleep(0.3)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(lib['feedback_button_text'], url=lib['feedback_url']))
        bot.send_message(message.chat.id, lib['feedback'], reply_markup=markup)
        return

    bot.send_message(message.chat.id, lib['unknown_text'])


def delivery_menu(message: telebot.types.Message, item_ratio: float) -> None:
    bot.send_message(message.chat.id, lib['enter_delivery_type'],
                     parse_mode='html', reply_markup=delivery_keyboard)

    bot.register_next_step_handler(message, process_delivery, item_ratio)


def process_delivery(message: telebot.types.Message, item_ratio: float) -> None:
    delivery_ratio: float = 0.0
    if message.text == lib['delivery_type1']:
        delivery_ratio = items["fast_delivery"]
    elif message.text == lib['delivery_type2']:
        delivery_ratio = items["long_delivery"]
    elif message.text == lib["delivery_text1"]:
        bot.send_message(message.chat.id, lib['item_category'], parse_mode='html',
                         reply_markup=items_keyboard)
        bot.register_next_step_handler(message, item_menu)
        return
    elif message.text == lib["delivery_text2"]:
        bot.send_message(message.chat.id, lib['back_to_start'], parse_mode='html',
                         reply_markup=menu_keyboard)
        return
    calculate_price(message, delivery_ratio, item_ratio)


def calculate_price(message: telebot.types.Message, delievery_ratio: float, item_ratio: float) -> None:
    bot.send_message(message.chat.id, lib['enter_price'] + f' {CurrencySymbols.get_symbol("CNY")}',
                     parse_mode='html', reply_markup=back_keyboard)

    bot.register_next_step_handler(message, process_price, delievery_ratio, item_ratio)


def process_price(message: telebot.types.Message, delivery_ratio: float, item_ratio: float) -> None:
    if message.text == lib['back_button_text1']:
        bot.send_message(message.chat.id, lib['enter_delivery_type'], parse_mode='html',
                         reply_markup=delivery_keyboard)
        bot.register_next_step_handler(message, process_delivery, item_ratio)
        return
    elif message.text == lib['back_button_text2']:
        bot.send_message(message.chat.id, lib['back_to_start'], parse_mode='html',
                         reply_markup=menu_keyboard)
        return

    try:
        price: float = float(message.text)
        if price > 0:
            currency = requests.get('https://www.cbr-xml-daily.ru/daily_json.js').json()
            k: float = currency['Valute']['CNY']['Value']
            result: int = int(round((1.05 * price * (k + lib['currency_interest']) +
                                     item_ratio * delivery_ratio) * 1.1, -2))
            bot.send_message(message.chat.id, lib['final_price'] + f'{result} {CurrencySymbols.get_symbol("RUB")}',
                             parse_mode='html',
                             reply_markup=menu_keyboard
                             )
        else:
            bot.register_next_step_handler(message, process_price, delivery_ratio, item_ratio)
            bot.send_message(message.chat.id, lib['price_error'])
            return

    except ValueError:
        bot.register_next_step_handler(message, process_price, delivery_ratio, item_ratio)
        bot.send_message(message.chat.id, lib['price_error'])
        return


def item_menu(message: telebot.types.Message) -> None:
    item_ratio: float = 0.0

    if message.text == lib['item_text1']:
        item_ratio = items['Обувь']
    elif message.text == lib['item_text2']:
        item_ratio = items['Нижнее белье']
    elif message.text == lib['item_text3']:
        item_ratio = items['Одежда']
    elif message.text == lib['item_text4']:
        item_ratio = items['Аксессуары']
    elif message.text == lib['item_text5']:
        bot.send_message(message.chat.id, lib['back_to_start'], parse_mode='html',
                         reply_markup=menu_keyboard)
        return
    delivery_menu(message, item_ratio)


if __name__ == '__main__':
    bot.polling(none_stop=True)
