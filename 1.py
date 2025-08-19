from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3
from datetime import datetime
import asyncio

TOKEN = "8084295237:AAHPGFXfPq_0uK7pPqvr_VGefqtSW2HmVKY"
DB_NAME = "shop.db"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===== DATABASE =====
def db_connect():
    return sqlite3.connect(DB_NAME)

# ===== FSM STATES =====
class OrderInfo(StatesGroup):
    name = State()
    phone = State()
    address = State()

# ===== KEYBOARDS =====
customer_menu = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="🛍 Katalog"), types.KeyboardButton(text="🔍 Qidirish")],
        [types.KeyboardButton(text="🛒 Savatim"), types.KeyboardButton(text="📦 Buyurtmalarim")]
    ],
    resize_keyboard=True
)

# ===== START HANDLER =====
@dp.message(F.text == "/start")
async def start(message: types.Message):
    await message.answer("Bozorga xush kelibsiz!", reply_markup=customer_menu)

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

# ===== BOT START =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
