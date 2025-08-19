import logging
import sqlite3
from datetime import datetime
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ================= CONFIG =================
TOKEN ="8089913517:AAFpc7t_Nf_F9pmY8X3DHmSQtyz0kit9_gE"
ADMIN_ID = 1081829777  # Sizning Telegram IDingiz
DB_NAME = "shop.db"

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)

# ================= BOT & DISPATCHER =================
bot = Bot(token=TOKEN)
dp = Dispatcher(bot=bot, storage=MemoryStorage())

# ================= DATABASE =================
def db_connect():
    return sqlite3.connect(DB_NAME)

def db_init():
    conn = db_connect()
    c = conn.cursor()
    # Mahsulotlar
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price INTEGER,
        category TEXT
    )""")
    # Savat
    c.execute("""CREATE TABLE IF NOT EXISTS cart (
        user_id INTEGER,
        product_id INTEGER,
        quantity INTEGER
    )""")
    # Buyurtmalar
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        phone TEXT,
        address TEXT,
        items TEXT,
        total INTEGER,
        status TEXT,
        created_time INTEGER
    )""")
    conn.commit()
    conn.close()

db_init()

# ================= STATES =================
class AddProduct(StatesGroup):
    name = State()
    price = State()
    category = State()

class OrderInfo(StatesGroup):
    name = State()
    phone = State()
    address = State()

class SearchProduct(StatesGroup):
    query = State()

# ================= KEYBOARDS =================
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛍 Katalog"), KeyboardButton(text="🔍 Qidirish")],
        [KeyboardButton(text="🛒 Savat"), KeyboardButton(text="📦 Buyurtmalarim")]
    ],
    resize_keyboard=True
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="🗑 Mahsulot o'chirish")],
        [KeyboardButton(text="📜 Buyurtmalar"), KeyboardButton(text="🔙 Asosiy menyu")]
    ],
    resize_keyboard=True
)

# ================= DATABASE FUNCS =================
def add_product_db(name, price, category):
    conn = db_connect()
    c = conn.cursor()
    c.execute("INSERT INTO products (name, price, category) VALUES (?, ?, ?)", (name, price, category))
    conn.commit()
    conn.close()

def get_all_products():
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT id, name, price, category FROM products")
    rows = c.fetchall()
    conn.close()
    return rows

def search_products(query):
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT id, name, price, category FROM products WHERE name LIKE ?", ('%'+query+'%',))
    rows = c.fetchall()
    conn.close()
    return rows

def add_to_cart(user_id, product_id):
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT quantity FROM cart WHERE user_id=? AND product_id=?", (user_id, product_id))
    res = c.fetchone()
    if res:
        c.execute("UPDATE cart SET quantity=? WHERE user_id=? AND product_id=?", (res[0]+1, user_id, product_id))
    else:
        c.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, 1))
    conn.commit()
    conn.close()

def get_cart(user_id):
    conn = db_connect()
    c = conn.cursor()
    c.execute("""SELECT p.name, p.price, c.quantity, p.id 
                 FROM cart c JOIN products p ON c.product_id=p.id 
                 WHERE c.user_id=?""", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def clear_cart(user_id):
    conn = db_connect()
    c = conn.cursor()
    c.execute("DELETE FROM cart WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def create_order(user_id, name, phone, address):
    items = get_cart(user_id)
    if not items:
        return False
    item_text = ", ".join([f"{i[0]} x{i[2]}" for i in items])
    total = sum(i[1]*i[2] for i in items)
    conn = db_connect()
    c = conn.cursor()
    c.execute("""INSERT INTO orders (user_id, name, phone, address, items, total, status, created_time)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (user_id, name, phone, address, item_text, total, "Yangi", int(datetime.now().timestamp())))
    conn.commit()
    conn.close()
    clear_cart(user_id)
    return True

def delete_product_db(product_name):
    conn = db_connect()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE name=?", (product_name,))
    conn.commit()
    conn.close()

def get_all_orders():
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT id, user_id, name, phone, address, items, total, status FROM orders")
    rows = c.fetchall()
    conn.close()
    return rows

# ================= HANDLERS =================
@dp.message(F.text == "/start")
async def start_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Salom Admin! Menyuni tanlang:", reply_markup=admin_menu)
    else:
        await message.answer("Assalomu alaykum! Online do'konimizga xush kelibsiz!", reply_markup=main_menu)

# ================= FOYDALANUVCHI =================
@dp.message(F.text == "🛍 Katalog")
async def show_catalog(message: types.Message):
    products = get_all_products()
    if not products:
        await message.answer("Hozircha mahsulotlar yo‘q.")
        return
    for p in products:
        btn = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=f"➕ {p[1]}")]], resize_keyboard=True)
        await message.answer(f"{p[1]} - {p[2]} so'm ({p[3]})", reply_markup=btn)

@dp.message(F.text.startswith("➕ "))
async def add_product_cart(message: types.Message):
    product_name = message.text[2:].strip()
    products = get_all_products()
    for p in products:
        if p[1] == product_name:
            add_to_cart(message.from_user.id, p[0])
            await message.answer(f"{product_name} savatga qo‘shildi!", reply_markup=main_menu)
            return
    await message.answer("Mahsulot topilmadi.", reply_markup=main_menu)

@dp.message(F.text == "🛒 Savat")
async def view_cart(message: types.Message):
    items = get_cart(message.from_user.id)
    if not items:
        await message.answer("Savat bo‘sh.")
        return
    text = "Savatdagi mahsulotlar:\n"
    total = 0
    for i in items:
        text += f"{i[0]} x{i[2]} - {i[1]*i[2]} so'm\n"
        total += i[1]*i[2]
    text += f"\nJami: {total} so'm\n\nBuyurtma berish uchun '✅ Buyurtma berish' ni bosing."
    await message.answer(text)

@dp.message(F.text == "✅ Buyurtma berish")
async def order_start(message: types.Message, state: FSMContext):
    await message.answer("Ismingizni kiriting:")
    await state.set_state(OrderInfo.name)

@dp.message(F.state == OrderInfo.name)
async def order_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Telefon raqamingizni kiriting:")
    await state.set_state(OrderInfo.phone)

@dp.message(F.state == OrderInfo.phone)
async def order_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Manzilingizni kiriting:")
    await state.set_state(OrderInfo.address)

@dp.message(F.state == OrderInfo.address)
async def order_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    success = create_order(message.from_user.id, data['name'], data['phone'], message.text)
    if success:
        await message.answer("Buyurtma qabul qilindi! Tez orada siz bilan bog‘lanamiz.", reply_markup=main_menu)
    else:
        await message.answer("Savat bo‘sh. Buyurtma qabul qilinmadi.", reply_markup=main_menu)
    await state.clear()

# ================= SEARCH =================
@dp.message(F.text == "🔍 Qidirish")
async def search_cmd(message: types.Message, state: FSMContext):
    await message.answer("Mahsulot nomini kiriting:")
    await state.set_state(SearchProduct.query)

@dp.message(F.state == SearchProduct.query)
async def search_process(message: types.Message, state: FSMContext):
    query = message.text
    results = search_products(query)
    if results:
        for r in results:
            btn = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=f"➕ {r[1]}")]], resize_keyboard=True)
            await message.answer(f"{r[1]} - {r[2]} so'm ({r[3]})", reply_markup=btn)
    else:
        await message.answer("Hech narsa topilmadi.")
    await state.clear()

# ================= ADMIN =================
@dp.message(F.text == "➕ Mahsulot qo'shish", F.from_user.id == ADMIN_ID)
async def admin_add_product(message: types.Message, state: FSMContext):
    await message.answer("Mahsulot nomini kiriting:")
    await state.set_state(AddProduct.name)

@dp.message(F.state == AddProduct.name)
async def add_product_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Mahsulot narxini kiriting (so‘mda):")
    await state.set_state(AddProduct.price)

@dp.message(F.state == AddProduct.price)
async def add_product_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Faqat raqam kiriting!")
        return
    await state.update_data(price=int(message.text))
    await message.answer("Mahsulot kategoriyasini kiriting:")
    await state.set_state(AddProduct.category)

@dp.message(F.state == AddProduct.category)
async def add_product_category(message: types.Message, state: FSMContext):
    data = await state.get_data()
    add_product_db(data['name'], data['price'], message.text)
    await message.answer("Mahsulot qo‘shildi!", reply_markup=admin_menu)
    await state.clear()

@dp.message(F.text == "🗑 Mahsulot o'chirish", F.from_user.id == ADMIN_ID)
async def admin_delete_product(message: types.Message):
    products = get_all_products()
    if not products:
        await message.answer("Hozircha mahsulotlar yo‘q.")
        return
    btns = [[KeyboardButton(text=p[1])] for p in products]
    markup = ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)
    await message.answer("O‘chirmoqchi bo‘lgan mahsulotni tanlang:", reply_markup=markup)

@dp.message(F.from_user.id == ADMIN_ID)
async def handle_delete_product(message: types.Message):
    products = get_all_products()
    for p in products:
        if p[1] == message.text:
            delete_product_db(message.text)
            await message.answer(f"{message.text} o‘chirildi!", reply_markup=admin_menu)
            return

@dp.message(F.text == "📜 Buyurtmalar", F.from_user.id == ADMIN_ID)
async def admin_view_orders(message: types.Message):
    orders = get_all_orders()
    if not orders:
        await message.answer("Hozircha buyurtmalar yo‘q.")
        return
    text = "Buyurtmalar:\n"
    for o in orders:
        text += f"ID: {o[0]} | {o[2]} | {o[3]} | {o[4]} | {o[5]} | Jami: {o[6]} so'm | Status: {o[7]}\n\n"
    await message.answer(text, reply_markup=admin_menu)

# ================= RUN BOT =================
if __name__ == "__main__":
    asyncio.run(dp.start_polling())


