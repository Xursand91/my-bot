import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ================= CONFIG =================
TOKEN = "8089913517:AAFpc7t_Nf_F9pmY8X3DHmSQtyz0kit9_gE"
ADMIN_ID = 1081829777 # admin Telegram ID
DB_NAME = "shop.db"

# ================= BOT & DISPATCHER =================
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= DATABASE =================
def db_connect():
    return sqlite3.connect(DB_NAME)

def db_init():
    conn = db_connect()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, price INTEGER, category TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS cart (
        user_id INTEGER, product_id INTEGER, quantity INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, name TEXT, phone TEXT, address TEXT,
        items TEXT, total INTEGER, status TEXT, created_time INTEGER
    )""")
    conn.commit()
    conn.close()

db_init()

# ================= FSM STATES =================
class AddProduct(StatesGroup):
    name = State()
    price = State()
    category = State()

class OrderInfo(StatesGroup):
    name = State()
    phone = State()
    address = State()

# ================= KEYBOARDS =================
customer_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛍 Katalog"), KeyboardButton(text="🛒 Savatim")],
        [KeyboardButton(text="📦 Buyurtmalarim")]
    ],
    resize_keyboard=True
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="🗑 Mahsulot o'chirish")],
        [KeyboardButton(text="📦 Buyurtmalarni ko'rish")]
    ],
    resize_keyboard=True
)

# ================= START HANDLER =================
@dp.message(F.text == "/start")
async def start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Admin panelga xush kelibsiz!", reply_markup=admin_menu)
    else:
        await message.answer("Bozorga xush kelibsiz!", reply_markup=customer_menu)

# ================= ADMIN HANDLERS =================
@dp.message(F.text == "➕ Mahsulot qo'shish", F.from_user.id==ADMIN_ID)
async def add_product_start(message: types.Message, state: FSMContext):
    await message.answer("Mahsulot nomini kiriting:")
    await state.set_state(AddProduct.name)

@dp.message(AddProduct.name, F.from_user.id==ADMIN_ID)
async def add_product_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Narxni kiriting:")
    await state.set_state(AddProduct.price)

@dp.message(AddProduct.price, F.from_user.id==ADMIN_ID)
async def add_product_price(message: types.Message, state: FSMContext):
    await state.update_data(price=int(message.text))
    await message.answer("Kategoriya kiriting:")
    await state.set_state(AddProduct.category)

@dp.message(AddProduct.category, F.from_user.id==ADMIN_ID)
async def add_product_category(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = db_connect()
    c = conn.cursor()
    c.execute("INSERT INTO products (name, price, category) VALUES (?, ?, ?)",
              (data["name"], data["price"], message.text))
    conn.commit()
    conn.close()
    await message.answer(f"{data['name']} qo‘shildi!", reply_markup=admin_menu)
    await state.clear()

@dp.message(F.text == "🗑 Mahsulot o'chirish", F.from_user.id==ADMIN_ID)
async def delete_product(message: types.Message):
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT id, name FROM products")
    products = c.fetchall()
    conn.close()
    if products:
        text = "O'chirmoqchi bo'lgan mahsulot ID sini yuboring:\n"
        for p in products:
            text += f"{p[0]}: {p[1]}\n"
        await message.answer(text)
    else:
        await message.answer("Hali mahsulotlar yo'q.", reply_markup=admin_menu)

@dp.message(F.from_user.id==ADMIN_ID)
async def delete_product_confirm(message: types.Message):
    try:
        product_id = int(message.text)
        conn = db_connect()
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        conn.close()
        await message.answer("Mahsulot o'chirildi.", reply_markup=admin_menu)
    except:
        pass
@dp.message(F.text == "📦 Buyurtmalarni ko'rish", F.from_user.id==ADMIN_ID)
async def view_orders(message: types.Message):
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT id, user_id, name, phone, address, items, total, status FROM orders ORDER BY created_time DESC")
    orders = c.fetchall()
    conn.close()
    
    if orders:
        text = "Buyurtmalar:\n\n"
        for o in orders:
            text += (
                f"Buyurtma ID: {o[0]}\n"
                f"Foydalanuvchi ID: {o[1]}\n"
                f"Ism: {o[2]}\n"
                f"Telefon: {o[3]}\n"
                f"Manzil: {o[4]}\n"
                f"Buyurtma: {o[5]}\n"
                f"Jami: {o[6]} so'm\n"
                f"Status: {o[7]}\n"
                "----------------------\n"
            )
        await message.answer(text)
    else:
        await message.answer("Hozircha buyurtma yo'q.", reply_markup=admin_menu)


# ================= MIJOZ HANDLERS =================
@dp.message(F.text == "🛍 Katalog")
async def show_products(message: types.Message):
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT id, name, price FROM products")
    products = c.fetchall()
    conn.close()
    if products:
        text = "\n".join([f"{p[0]}: {p[1]} - {p[2]} so'm" for p in products])
        await message.answer(text + "\n\nSavatingizga qo'shish uchun ID raqamini yuboring.")
    else:
        await message.answer("Mahsulotlar mavjud emas.")

@dp.message(F.text.isdigit())
async def add_to_cart(message: types.Message):
    product_id = int(message.text)
    user_id = message.from_user.id
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT id FROM products WHERE id=?", (product_id,))
    if c.fetchone():
        c.execute("SELECT quantity FROM cart WHERE user_id=? AND product_id=?", (user_id, product_id))
        res = c.fetchone()
        if res:
            c.execute("UPDATE cart SET quantity=? WHERE user_id=? AND product_id=?", (res[0]+1, user_id, product_id))
        else:
            c.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, 1)", (user_id, product_id))
        conn.commit()
        await message.answer("Mahsulot savatga qo‘shildi!", reply_markup=customer_menu)
    else:
        await message.answer("Mahsulot topilmadi.", reply_markup=customer_menu)
    conn.close()

@dp.message(F.text == "🛒 Savatim")
async def show_cart(message: types.Message):
    user_id = message.from_user.id
    conn = db_connect()
    c = conn.cursor()
    c.execute("""SELECT cart.product_id, cart.quantity, products.name, products.price 
                 FROM cart JOIN products ON cart.product_id = products.id
                 WHERE cart.user_id=?""", (user_id,))
    items = c.fetchall()
    conn.close()
    if items:
        text = "Sizning savatingiz:\n"
        total = 0
        for item in items:
            text += f"{item[2]} x{item[1]} - {item[3]*item[1]} so'm\n"
            total += item[3]*item[1]
        text += f"\nJami: {total} so'm\nBuyurtma berish uchun /order yozing"
        await message.answer(text)
    else:
        await message.answer("Savat bo'sh.")

# ===== MIJOZ BUYURTMA BERISH =====
@dp.message(F.text == "/order")
async def order_start(message: types.Message):
    await message.answer("Buyurtma berish uchun ismingizni kiriting:")
    await dp.current_state(user=message.from_user.id).set_state(OrderInfo.name)

@dp.message(OrderInfo.name)
async def order_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Telefon raqamingizni kiriting:")
    await state.set_state(OrderInfo.phone)

@dp.message(OrderInfo.phone)
async def order_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Manzilingizni kiriting:")
    await state.set_state(OrderInfo.address)

@dp.message(OrderInfo.address)
async def order_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    name = data["name"]
    phone = data["phone"]
    address = message.text

    conn = db_connect()
    c = conn.cursor()
    # Savatni olish
    c.execute("""SELECT cart.product_id, cart.quantity, products.name, products.price 
                 FROM cart JOIN products ON cart.product_id = products.id
                 WHERE cart.user_id=?""", (user_id,))
    items = c.fetchall()
    if not items:
        await message.answer("Savat bo'sh.")
        await state.clear()
        conn.close()
        return

    total = 0
    items_text = ""
    for item in items:
        items_text += f"{item[2]} x{item[1]} - {item[3]*item[1]} so'm\n"
        total += item[3]*item[1]

    # Buyurtma yozish
    c.execute("""INSERT INTO orders (user_id, name, phone, address, items, total, status, created_time)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (user_id, name, phone, address, items_text, total, "Yangi", int(datetime.now().timestamp())))
    # Savatni tozalash
    c.execute("DELETE FROM cart WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

    await message.answer(f"Buyurtmangiz qabul qilindi!\n\n{items_text}\nJami: {total} so'm", reply_markup=customer_menu)
    await state.clear()

# ===== MIJOZ BUYURTMALARIM =====
@dp.message(F.text == "📦 Buyurtmalarim")
async def my_orders(message: types.Message):
    user_id = message.from_user.id
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT id, items, total, status, created_time FROM orders WHERE user_id=? ORDER BY created_time DESC", (user_id,))
    orders = c.fetchall()
    conn.close()

    if orders:
        text = "Sizning buyurtmalaringiz:\n\n"
        for o in orders:
            date = datetime.fromtimestamp(o[4]).strftime("%d-%m-%Y %H:%M")
            text += (
                f"Buyurtma ID: {o[0]}\n"
                f"{o[1]}"
                f"Jami: {o[2]} so'm\n"
                f"Status: {o[3]}\n"
                f"Sana: {date}\n"
                "----------------------\n"
            )
        await message.answer(text, reply_markup=customer_menu)
    else:
        await message.answer("Siz hali hech qanday buyurtma bermagansiz.", reply_markup=customer_menu)

# ================= BOT START =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
