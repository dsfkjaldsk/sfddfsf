# Обробники подій та FSM логіка
from aiogram import Router, F, types
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from config import ADMINS
from utils import load_products, update_user_purchase, save_products, load_promocodes, save_promocodes, load_global_discount
from keyboard import generate_product_keyboard, admin_order_keyboard, done_keyboard, promocode_yes_no_keyboard, promocode_enter_keyboard, back_keyboard, thanks_keyboard
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import json

MENU_FILE = "bots/zheka_shop/menu_text.txt"
MENU_IMMUTABLE_LINE = "\n\n <i>Сделал @Ruthlessnessalbificative, обращайтесь</i>"

router = Router()
orders = {}
order_id_counter = 0

# Словник для зберігання ID повідомлень, які потрібно видаляти
user_messages_to_delete = {}
# Словник для зберігання ID повідомлень-меню, щоб їх не видаляв обробник thank_you
user_menu_message_id = {}
# Словник для зберігання ID повідомлень-хелп
user_help_message_id = {}

# --- Оголошення класів FSM ---
# Стан очікування місця та часу
class OrderFSM(StatesGroup):
    waiting_promocode_choice = State()
    waiting_promocode_input = State()
    waiting_place_time = State()

# Стан для адмінської команди оновлення продуктів
class AdminFSM(StatesGroup):
    waiting_product_update = State()
# --- Кінець оголошення FSM ---


# Клавіатура для /help з кнопкою "Назад"
def help_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_from_help")]
    ])
    return keyboard


# Обробник кнопки "Назад" з /help
@router.callback_query(F.data == "back_from_help")
async def back_from_help(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    try:
        await callback.message.delete()
        if user_id in user_help_message_id:
            del user_help_message_id[user_id]
        
    except Exception:
        pass

    await state.clear()


# Команда /start або /menu
@router.message(lambda m: m.text in ["/start", "/menu"])
async def show_menu(message: types.Message, state: FSMContext):
    # Видаляємо попереднє повідомлення меню, якщо воно існує
    user_id = message.from_user.id
    if user_id in user_menu_message_id:
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=user_menu_message_id[user_id])
        except Exception:
            pass

    try:
        with open(MENU_FILE, "r", encoding="utf-8") as f:
            text = f.read().rstrip()
        if not text.endswith(MENU_IMMUTABLE_LINE.strip()):
            text += MENU_IMMUTABLE_LINE
        products = load_products()
        kb = generate_product_keyboard(products)
        sent_message = await message.answer(text, reply_markup=kb, parse_mode='HTML')
        user_menu_message_id[user_id] = sent_message.message_id
    except Exception:
        products = load_products()
        kb = generate_product_keyboard(products)
        sent_message = await message.answer(MENU_IMMUTABLE_LINE, reply_markup=kb, parse_mode='HTML')
        user_menu_message_id[user_id] = sent_message.message_id

# Обробник кнопки "Оновити"
@router.callback_query(F.data == "refresh_menu")
async def refresh_menu(callback: types.CallbackQuery):
    products = load_products()
    kb = generate_product_keyboard(products)
    
    # Завантажуємо текст з файлу, щоб оновити і його
    try:
        with open(MENU_FILE, "r", encoding="utf-8") as f:
            text = f.read().rstrip()
        if not text.endswith(MENU_IMMUTABLE_LINE.strip()):
            text += MENU_IMMUTABLE_LINE
    except FileNotFoundError:
        text = MENU_IMMUTABLE_LINE

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode='HTML')
        await callback.answer("Меню обновлено!")
    except Exception as e:
        if "message is not modified" in str(e):
            await callback.answer("Меню обновлено!")
        else:
            await callback.answer("Ошибка при обновлении меню.")

# Обробка покупки товару
@router.callback_query(F.data.startswith("buy_"))
async def handle_buy(callback: types.CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    products = load_products()
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        await callback.message.answer("Товар не найден.")
        return
    if product["quantity"] != "inf" and product["quantity"] <= 0:
        await callback.message.answer("Извините, этого товара нет в наличии.")
        return
    await state.set_data({"product": product})
    await state.set_state(OrderFSM.waiting_promocode_choice)
    sent_message = await callback.message.answer("Использовать промокод?", reply_markup=promocode_yes_no_keyboard())

    # Зберігаємо ID повідомлення для подальшого видалення
    user_id = callback.from_user.id
    if user_id not in user_messages_to_delete:
        user_messages_to_delete[user_id] = []
    user_messages_to_delete[user_id].append(sent_message.message_id)

# НОВИЙ ОБРОБНИК для недоступних товарів
@router.callback_query(F.data.startswith("unavailable_"))
async def handle_unavailable(callback: types.CallbackQuery):
    await callback.answer("Этого товара нет в наличии.", show_alert=True)

@router.callback_query(F.data == "promo_no")
async def promo_no(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.set_state(OrderFSM.waiting_place_time)
    sent_message = await callback.message.answer("Напишите время и место где вы хотите получить товар", reply_markup=back_keyboard())

    user_id = callback.from_user.id
    if user_id not in user_messages_to_delete:
        user_messages_to_delete[user_id] = []
    user_messages_to_delete[user_id].append(sent_message.message_id)

@router.callback_query(F.data == "promo_yes")
async def promo_yes(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите промокод:", reply_markup=promocode_enter_keyboard())
    await state.set_state(OrderFSM.waiting_promocode_input)

@router.callback_query(F.data == "promo_back")
async def promo_back(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Использовать промокод?", reply_markup=promocode_yes_no_keyboard())
    await state.set_state(OrderFSM.waiting_promocode_choice)

@router.message(OrderFSM.waiting_promocode_input)
async def promo_input(message: types.Message, state: FSMContext):
    code = message.text.strip().lower()
    promocodes = load_promocodes()
    data = await state.get_data()
    product = data["product"]
    user_id = message.from_user.id
    found = None
    for p in promocodes:
        if p["code"] == code:
            found = p
            break
    if not found:
        await message.answer("Неправильный промокод. Попробуйте ещё раз или нажмите 'Вернуться'.", reply_markup=back_keyboard())
        return
    # Перевірка ліміту використань
    if found.get("limit") is not None and found["times_used"] >= found["limit"]:
        await message.answer("Лимит использований этого промокода исчерпан.", reply_markup=back_keyboard())
        return
    # Підрахунок знижки
    discount = found["discount"] / 100
    # Додатковий бонус автору (до 50%)
    author_bonus = 0
    if found.get("author_id") == user_id:
        author_bonus = min(found.get("author_bonus", 0), 50) / 100
        price = product["price"] * (1 - author_bonus)
    else:
        price = product["price"] * (1 - discount)

    # Округлення до 0.1 (10 центів)
    price = round(price * 10) / 10
    await state.update_data({"discount": discount, "promo_code": code, "price": price, "author_bonus": author_bonus, "promocode_data": found})
    await state.set_state(OrderFSM.waiting_place_time)
    
    # Видаляємо повідомлення з промокодом та відповідь
    try:
        await message.bot.delete_message(chat_id=user_id, message_id=message.message_id - 1)
        await message.delete()
    except Exception:
        pass
        
    sent_message = await message.answer(f"Промокод применён! Ваша цена: {price}€. Теперь напишите время и место, где вы хотите получить товар.", reply_markup=back_keyboard())
    
    user_id = message.from_user.id
    if user_id not in user_messages_to_delete:
        user_messages_to_delete[user_id] = []
    user_messages_to_delete[user_id].append(sent_message.message_id)


# Отримання часу і місця
@router.message(OrderFSM.waiting_place_time)
async def handle_place_time(message: types.Message, state: FSMContext):
    global order_id_counter
    user_data = await state.get_data()
    product = user_data["product"]
    price = user_data.get("price", product["price"])
    discount = user_data.get("discount", 0)
    author_bonus = user_data.get("author_bonus", 0)
    promo_code = user_data.get("promo_code", None)
    promocode_data = user_data.get("promocode_data", None)

    order_id_counter += 1
    order_id = order_id_counter
    user_id = message.from_user.id
    count = update_user_purchase(user_id)
    if not promo_code:
        discount = 0.3 if count % 4 == 0 else 0
        price = round(product["price"] * (1 - discount) * 10) / 10
    order = {
        "order_id": order_id,
        "user_id": user_id,
        "username": message.from_user.username,
        "product": product,
        "place_time": message.text,
        "discount": discount,
        "price": price,
        "promo_code": promo_code,
        "author_bonus": author_bonus,
        "promocode_data": promocode_data,
        "admin_message_ids": {}
    }
    orders[order_id] = order
    await state.clear()

    order_text = (
        f"🧾 ЗАКАЗ #{order_id}\n"
        f"👤 @{order['username']}\n"
        f"📦 <b>{product['name']}</b>\n"
        f"💰 Цена: {price}€ (скидка: {int(discount*100)}%)\n"
        f"📍 {message.text}"
    )
    for admin_id in ADMINS:
        sent_message = await message.bot.send_message(admin_id, order_text, reply_markup=admin_order_keyboard(order_id), parse_mode='HTML')
        order["admin_message_ids"][admin_id] = sent_message.message_id
    
    # Видаляємо всі зайві повідомлення у користувача
    if user_id in user_messages_to_delete:
        for msg_id in user_messages_to_delete[user_id]:
            try:
                await message.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception:
                pass
        del user_messages_to_delete[user_id]
        
    # Видаляємо повідомлення користувача і бота з запитом місця/часу
    try:
        # Повідомлення користувача з місцем/часом
        await message.bot.delete_message(chat_id=user_id, message_id=message.message_id)
        # Повідомлення бота з запитом місця/часу
        # Оскільки ми видаляли попередні повідомлення, це буде останнє
        last_bot_message_id = message.message_id - 1
        await message.bot.delete_message(chat_id=user_id, message_id=last_bot_message_id)
    except Exception:
        pass
        
    sent_message = await message.answer("Ваш заказ отправлен на подтверждение. Ожидайте ответа администратора.")
    user_messages_to_delete[user_id] = [sent_message.message_id]
    
# Прийняття замовлення
@router.callback_query(F.data.startswith("accept_"))
async def accept_order(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    order = orders.get(order_id)
    if not order:
        await callback.answer("Этот заказ уже был обработан.", show_alert=True)
        return
    
    admin_id_accepted = callback.from_user.id
    order_text_admin = callback.message.text + "\n✅ Заказ принят"
    
    # Редагуємо повідомлення для адміна, який прийняв замовлення
    await callback.message.edit_text(order_text_admin, reply_markup=done_keyboard(order_id))
    
    # Видаляємо повідомлення для інших адмінів
    for admin_id, msg_id in order["admin_message_ids"].items():
        if admin_id != admin_id_accepted:
            try:
                await callback.bot.delete_message(chat_id=admin_id, message_id=msg_id)
            except Exception:
                pass

    # Видаляємо старе повідомлення про очікування
    user_id = order["user_id"]
    if user_id in user_messages_to_delete:
        for msg_id in user_messages_to_delete[user_id]:
            try:
                await callback.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception:
                pass
        del user_messages_to_delete[user_id]

    # Відправляємо нове повідомлення з повною інформацією про замовлення
    order_info_for_user = (
        f"✅ <b>Заказ принят!</b>\n\n"
        f"🧾 ЗАКАЗ #{order_id}\n"
        f"📦 <b>{order['product']['name']}</b>\n"
        f"💰 Цена: {order['price']}€\n"
        f"📍 {order['place_time']}\n\n"
        f"<i>Приготовьте точную сумму</i> 😊"
    )
    sent_message = await callback.bot.send_message(user_id, order_info_for_user, reply_markup=thanks_keyboard(), parse_mode='HTML')
    user_messages_to_delete[user_id] = [sent_message.message_id]
    

# Відмова
@router.callback_query(F.data.startswith("reject_"))
async def reject_order(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    order = orders.get(order_id)
    if not order:
        await callback.answer("Этот заказ уже был обработан.", show_alert=True)
        return
    
    user_id = order["user_id"]
    if user_id in user_messages_to_delete:
        for msg_id in user_messages_to_delete[user_id]:
            try:
                await callback.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception:
                pass
        del user_messages_to_delete[user_id]
            
    sent_message = await callback.bot.send_message(user_id, "Ваш заказ отклонён.", reply_markup=thanks_keyboard())
    user_messages_to_delete[user_id] = [sent_message.message_id]

    # Видаляємо повідомлення у всіх адмінів
    for admin_id, msg_id in order["admin_message_ids"].items():
        try:
            await callback.bot.delete_message(chat_id=admin_id, message_id=msg_id)
        except Exception:
            pass
            
    del orders[order_id]

# Відмова з повідомленням
@router.callback_query(F.data.startswith("custom_reject_"))
async def custom_reject(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminFSM.waiting_product_update)
    order_id = int(callback.data.split("_")[2])
    # Зберігаємо оригінальний ID повідомлення, щоб потім його видалити
    await state.set_data({"original_admin_message_id": callback.message.message_id, "order_id": order_id})
    await callback.message.answer("Введите причину отказа:")

# Прийом причини
@router.message(AdminFSM.waiting_product_update)
async def reason_response(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order = orders.get(data["order_id"])
    if order:
        user_id = order["user_id"]
        # Видаляємо старе повідомлення про очікування
        if user_id in user_messages_to_delete:
            for msg_id in user_messages_to_delete[user_id]:
                try:
                    await message.bot.delete_message(chat_id=user_id, message_id=msg_id)
                except Exception:
                    pass
            del user_messages_to_delete[user_id]
        
        sent_message = await message.bot.send_message(order["user_id"], message.text, reply_markup=thanks_keyboard())
        user_messages_to_delete[user_id] = [sent_message.message_id]
    
    # Видаляємо оригінальне повідомлення у всіх адмінів
    if order:
        for admin_id, msg_id in order["admin_message_ids"].items():
            try:
                await message.bot.delete_message(chat_id=admin_id, message_id=msg_id)
            except Exception:
                pass
    
    await state.clear()
    if order:
        del orders[data["order_id"]]
    # Видаляємо повідомлення адміна з причиною
    try:
        await message.delete()
    except Exception:
        pass


# Оновлюємо промокод і кількість товару тільки коли адмін натискає "Выполнено"
@router.callback_query(F.data.startswith("done_"))
async def mark_done(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    order = orders.get(order_id)
    if not order:
        await callback.answer("Заказ уже обработан или не существует.", show_alert=True)
        return
    
    products = load_products()
    product_name_to_update = order["product"]["name"]
    found_product = False
    for p in products:
        if p["name"] == product_name_to_update:
            if p["quantity"] != "inf":
                p["quantity"] -= 1
            found_product = True
            break
            
    if not found_product:
        del orders[order_id]
        await callback.message.edit_text(callback.message.text + "\n✅ ВЫПОЛНЕНО (Товар не найден, возможно, был удалён)")
        return
        
    save_products(products)
    
    if order.get("promocode_data"):
        promocodes = load_promocodes()
        for p in promocodes:
            if p["code"] == order["promo_code"]:
                p["times_used"] = p.get("times_used", 0) + 1
                if p.get("author_id") and p["author_id"] != order["user_id"]:
                    p["author_bonus"] = min(p.get("author_bonus", 0) + 1, 50)
                save_promocodes(promocodes)
                break
    
    await callback.message.edit_text(callback.message.text + "\n✅ ВЫПОЛНЕНО")
    
    user_id = order["user_id"]
    if user_id in user_messages_to_delete:
        for msg_id in user_messages_to_delete[user_id]:
            try:
                await callback.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception:
                pass
        del user_messages_to_delete[user_id]
    
    thanks_text = "Ваш заказ выполнен! Спасибо за покупку 🛍️ Приходите еще!"
    sent_message = await callback.bot.send_message(user_id, thanks_text, reply_markup=thanks_keyboard())
    user_messages_to_delete[user_id] = [sent_message.message_id]
    
    del orders[order_id]

# Новий обробник для кнопки "Дякую!"
@router.callback_query(F.data == "thanks_button")
async def handle_thanks(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    try:
        # Видаляємо всі повідомлення, пов'язані з останнім замовленням
        if user_id in user_messages_to_delete:
            for msg_id in user_messages_to_delete[user_id]:
                await callback.bot.delete_message(chat_id=user_id, message_id=msg_id)
            del user_messages_to_delete[user_id]
        
        # Видаляємо і саме повідомлення з кнопкою "Спасибо"
        await callback.message.delete()
    except Exception:
        pass

# Команда для адмінів для оновлення кількості та ціни продуктів
@router.message(F.text.startswith("/update"), F.from_user.id.in_(ADMINS))
async def update_products_admin(message: types.Message):
    try:
        # Підтримка: /update delete <назва>, /update change <назва> - <кількість> - <ціна>, /update <назва> - <кількість> [- ціна]
        parts = message.text.split(" ", 1)
        if len(parts) < 2:
            await message.answer("Неверный формат. Используйте: /update <действие/название> ...")
            return

        updates_str = parts[1].strip()
        products = load_products()
        updated_count = 0
        deleted_count = 0
        changed_count = 0
        new_product_id = max([p["id"] for p in products]) + 1 if products else 1

        # DELETE
        if updates_str.lower().startswith("delete "):
            product_name = updates_str[7:].strip()
            found = False
            for p in products[:]:
                if p["name"].lower() == product_name.lower():
                    products.remove(p)
                    deleted_count += 1
                    found = True
                    break
            if found:
                save_products(products)
                await message.answer(f"Продукт '{product_name}' удалён.")
            else:
                await message.answer(f"Продукт '{product_name}' не найден.")
            return

        # CHANGE
        if updates_str.lower().startswith("change "):
            rest = updates_str[7:].strip()
            try:
                product_name, quantity_str, price_str = [x.strip() for x in rest.split("-", 2)]
                quantity = int(quantity_str) if quantity_str.lower() != 'inf' else 'inf'
                price = int(price_str)
            except Exception:
                await message.answer("Неверный формат. Используйте: /update change <название> - <количество> - <цена>")
                return
            found = False
            for p in products:
                if p["name"].lower() == product_name.lower():
                    p["quantity"] = quantity
                    p["price"] = price
                    changed_count += 1
                    found = True
                    break
            if found:
                save_products(products)
                await message.answer(f"Продукт '{product_name}' обновлён: количество={quantity}, цена={price}.")
            else:
                await message.answer(f"Продукт '{product_name}' не найден.")
            return

        # ADD/UPDATE: /update <название> - <количество> [- цена], можно несколько через запятую
        product_updates = [update.strip().split("-") for update in updates_str.split(",") if update.strip()]
        for update in product_updates:
            if len(update) < 2:
                await message.answer(f"Неверный формат: {'-'.join(update)}. Используйте: Название - количество [- цена]")
                continue
            product_name = update[0].strip()
            try:
                quantity_str = update[1].strip().lower()
                quantity = int(quantity_str) if quantity_str != 'inf' else 'inf'
                price = None
                if len(update) > 2:
                    price = int(update[2].strip())
            except Exception:
                await message.answer(f"Неверное количество или цена для '{product_name}'. Введите числа или 'inf'.")
                continue
            found = False
            for p in products:
                if p["name"].lower() == product_name.lower():
                    if quantity != 'inf':
                        if p["quantity"] == 'inf':
                            p["quantity"] = 0
                        p["quantity"] += quantity
                    else:
                        p["quantity"] = 'inf'
                    if price is not None:
                        p["price"] = price
                    updated_count += 1
                    found = True
                    break
            if not found and price is not None:
                products.append({"id": new_product_id, "name": product_name, "price": price, "quantity": quantity})
                new_product_id += 1
                updated_count += 1
            elif not found and price is None:
                await message.answer(f"Для нового продукта '{product_name}' нужно указать цену.")
        save_products(products)
        await message.answer(f"Обновлено {updated_count} продуктов. Удалено {deleted_count}. Изменено {changed_count}.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при обновлении продуктов: {e}")

@router.message(F.text.startswith("/promo -"))
async def create_promocode(message: types.Message):
    # Формат: /promo - <назва> - [<відсоток>] - [<ліміт>]
    parts = [p.strip() for p in message.text.split("-")]
    if len(parts) < 2:
        await message.answer("Использование: /promo - &lt;название&gt; - [&lt;процент&gt;] - [&lt;лимит&gt;]")
        return
    code = parts[1].replace(" ", "_").lower()
    is_admin = message.from_user.id in ADMINS
    promocodes = load_promocodes()
    
    # Перевірка на унікальність коду
    if any(p["code"] == code for p in promocodes):
        await message.answer("Такой промокод уже существует. Выберите другое название.")
        return
    
    # Перевірка для звичайних користувачів: тільки один промокод
    if not is_admin:
        user_id = message.from_user.id
        if any(p.get("author_id") == user_id for p in promocodes):
            await message.answer("Вы уже создали промокод. Один пользователь может создать только один промокод.")
            return
    
    if is_admin:
        # Адмін може задати відсоток і ліміт
        try:
            discount = int(parts[2]) if len(parts) > 2 else 5
            if len(parts) > 3:
                if parts[3].lower() == 'inf':
                    limit = None
                else:
                    limit = int(parts[3])
            else:
                limit = None
        except Exception:
            await message.answer("Введите корректный процент и лимит (или 'inf').")
            return
        promocode = {
            "code": code,
            "discount": discount,
            "author_id": None,
            "author_username": "Система",
            "times_used": 0,
            "limit": limit
        }
    else:
        promocode = {
            "code": code,
            "discount": 5,
            "author_id": message.from_user.id,
            "author_username": message.from_user.username or str(message.from_user.id),
            "times_used": 0,
            "author_bonus": 0
        }
    promocodes.append(promocode)
    save_promocodes(promocodes)
    await message.answer(f"Промокод '{code}' создан!")

@router.message(F.text == "/help")
async def user_help_command(message: types.Message):
    user_help_text = """<b>Добро пожаловать в магазин! 🛒</b>

<b>Как купить товар:</b>
1. Выберите товар из списка
2. Решите, использовать ли промокод
3. Укажите время и место получения
4. Ждите подтверждения от администратора

<b>Промокоды:</b>
• Каждый пользователь может создать только один промокод
• Ваш промокод даёт 5% скидки
• За каждое использование вашего промокода вы получаете +1% к скидке на любые ваши покупки сделанные с использованием вашего промокода (максимум 50%)
• Создать промокод: /promo - &lt;название&gt;

<b>Автоматические скидки:</b>
• Каждый 4-й товар получает автоматическую скидку 30%

<b>Правила:</b>
• Промокоды можно использовать только при реальных покупках
• Статистика промокода обновляется только после подтверждения заказа администратором
• Один пользователь = один промокод
• Не передавайте деньги незнакомцам!

<b>Команды:</b>
• /start или /menu — показать товары
• /promo - &lt;название&gt; — создать промокод
• /help — эта справка"""

    admin_help_text = """

---

<b>Команды администратора:</b>

<b>Управление товарами:</b>
• /update &lt;название&gt; - &lt;количество&gt; [- цена] — добавить/обновить товар
• /update &lt;название&gt; - inf [- цена] — сделать товар бесконечным
• /update delete &lt;название&gt; — удалить товар
• /update change &lt;название&gt; - &lt;количество&gt; - &lt;цена&gt; — изменить товар

<b>Промокоды:</b>
• /promo - &lt;название&gt; — создать промокод (5% скидка)
• /promo - &lt;название&gt; - &lt;процент&gt; - &lt;лимит&gt; — создать админ-промокод
• /promo - &lt;название&gt; - &lt;процент&gt; - inf — создать безлимитный промокод

<b>Меню:</b>
• /menu_edit &lt;текст&gt; — изменить текст меню (HTML поддерживается)
• /start или /menu — показать меню

<b>Примеры:</b>
• /update Cola - 10 - 50
• /update Coca Cola - 10 - 50
• /update Coca Cola - inf - 50
• /update delete Coca Cola
• /promo - mycode - 20 - 5
• /menu_edit &lt;b&gt;Добро пожаловать!&lt;/b&gt; 😊"""

    try:
        await message.delete()
    except Exception:
        pass

    user_id = message.from_user.id
    if user_id in user_help_message_id:
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=user_help_message_id[user_id])
        except Exception:
            pass

    if message.from_user.id in ADMINS:
        full_help_text = user_help_text + admin_help_text
        sent_message = await message.answer(full_help_text, reply_markup=help_keyboard(), parse_mode='HTML')
        user_help_message_id[user_id] = sent_message.message_id
    else:
        sent_message = await message.answer(user_help_text, reply_markup=help_keyboard(), parse_mode='HTML')
        user_help_message_id[user_id] = sent_message.message_id

# --- універсальна кнопка "Повернутися" для FSM-діалогів ---
@router.callback_query(F.data == "back")
async def universal_back(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    
    user_id = callback.from_user.id
    # Видаляємо всі повідомлення, пов'язані з поточним FSM-діалогом
    if user_id in user_messages_to_delete:
        for msg_id in user_messages_to_delete[user_id]:
            try:
                await callback.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception:
                pass
        del user_messages_to_delete[user_id]

    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.answer("Вы вернулись в главное меню.")
    await show_menu(callback.message, state)


@router.message(F.text.startswith("/menu_edit"), F.from_user.id.in_(ADMINS))
async def menu_edit(message: types.Message):
    # /menu_edit <текст>
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        await message.answer("Использование: /menu_edit <текст>\n\nПоддерживается HTML-форматирование:\n<b>жирный</b>\n<i>курсив</i></i>\n<u>подчеркнутый</u>\n😀 смайлики")
        return
    new_text = parts[1].strip()
    # Додаємо незмінний останній рядок
    if not new_text.endswith(MENU_IMMUTABLE_LINE.strip()):
        new_text = new_text.rstrip() + MENU_IMMUTABLE_LINE
    with open(MENU_FILE, "w", encoding="utf-8") as f:
        f.write(new_text)
    await message.answer("Текст меню обновлён с поддержкой HTML-форматирования.")