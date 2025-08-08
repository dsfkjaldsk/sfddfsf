# Утиліти: завантаження/збереження JSON, оновлення покупок
from pathlib import Path
import json
import os

# Директорія, де лежить utils.py (тобто корінь бота)
BASE_DIR = Path(__file__).resolve().parent

PRODUCTS_FILE = BASE_DIR / "products.json"
USERS_FILE = BASE_DIR / "users.json"
PROMOCODES_FILE = BASE_DIR / "promocodes.json"
DISCOUNT_FILE = BASE_DIR / "discount.json"


def load_products():
    return json.loads(PRODUCTS_FILE.read_text(encoding='utf-8'))

def save_products(products):
    PRODUCTS_FILE.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding='utf-8')

def load_users():
    if not USERS_FILE.exists():
        USERS_FILE.write_text("{}", encoding='utf-8')
    return json.loads(USERS_FILE.read_text(encoding='utf-8'))

def save_users(users):
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding='utf-8')

def load_promocodes():
    if not PROMOCODES_FILE.exists():
        PROMOCODES_FILE.write_text("[]", encoding='utf-8')
    return json.loads(PROMOCODES_FILE.read_text(encoding='utf-8'))

def save_promocodes(promocodes):
    PROMOCODES_FILE.write_text(json.dumps(promocodes, ensure_ascii=False, indent=2), encoding='utf-8')

# Оновлення кількості покупок користувача
def update_user_purchase(user_id):
    users = load_users()
    user_id = str(user_id)
    users[user_id] = users.get(user_id, 0) + 1
    save_users(users)
    return users[user_id]

# Глобальна знижка

def load_global_discount():
    if not DISCOUNT_FILE.exists():
        DISCOUNT_FILE.write_text("0", encoding='utf-8')
    return float(DISCOUNT_FILE.read_text(encoding='utf-8'))

def save_global_discount(value):
    DISCOUNT_FILE.write_text(str(value), encoding='utf-8')