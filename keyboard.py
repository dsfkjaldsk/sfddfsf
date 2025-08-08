# Клавіатури для бота
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import load_products

# Додаємо кнопку "Оновити" для оновлення меню
def generate_product_keyboard(products):
    keyboard = []
    
    products = sorted(products, key=lambda p: p['price'])
    
    for product in products:
        # Перевіряємо, чи кількість товару нескінченна
        is_infinite = isinstance(product["quantity"], str) and product["quantity"].lower() == 'inf'
        
        # Перевіряємо, чи товар є в наявності
        if is_infinite or product["quantity"] > 0:
            kb_type = "buy_"
            label = f"{product['name']} - {product['price']}€"
            keyboard.append([InlineKeyboardButton(text=label, callback_data=f"{kb_type}{product['id']}")])
        else:
            kb_type = "unavailable_"
            label = f"❌ {product['name']} - {product['price']}€"
            keyboard.append([InlineKeyboardButton(text=label, callback_data=f"{kb_type}{product['id']}")])
    
    keyboard.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_order_keyboard(order_id):
    keyboard = [
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{order_id}")],
        [
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{order_id}"),
            InlineKeyboardButton(text="💬 Отклонить с причиной", callback_data=f"custom_reject_{order_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def done_keyboard(order_id):
    keyboard = [
        [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done_{order_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def promocode_yes_no_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="Да", callback_data="promo_yes")],
        [InlineKeyboardButton(text="Нет", callback_data="promo_no")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def promocode_enter_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="Вернуться", callback_data="promo_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def thanks_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="Ок", callback_data="thanks_button")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)