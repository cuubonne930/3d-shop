import os
import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

from db import add_model, get_models

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
WEBAPP_URL = os.getenv("WEBAPP_URL")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- МАШИНА СОСТОЯНИЙ ДЛЯ ДОБАВЛЕНИЯ ТОВАРА ---
class AddModel(StatesGroup):
    waiting_photo = State()
    waiting_title = State()
    waiting_desc = State()
    waiting_price = State()

# --- ХЕНДЛЕРЫ БОТА ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Кнопка внутри чата
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    # Нижняя постоянная клавиатура
    reply_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎁 Магазин", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True
    )
    
    await message.answer(
        "Каталог и корзина открываются внутри Telegram.\nНажми кнопку ниже 👇",
        reply_markup=inline_kb
    )
    await message.answer("Или используй меню внизу экрана:", reply_markup=reply_kb)

@dp.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет прав на добавление товаров.")
        return
    await message.answer("📸 Отправьте фотографию модели (или напишите /cancel для отмены).")
    await state.set_state(AddModel.waiting_photo)

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Добавление отменено.")

@dp.message(AddModel.waiting_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    # Берем картинку в максимальном качестве
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{photo.file_id}.jpg"
    await bot.download_file(file.file_path, file_path)
    
    await state.update_data(photo_path=file_path)
    await message.answer("✅ Фото сохранено. Теперь введите название модели:")
    await state.set_state(AddModel.waiting_title)

@dp.message(AddModel.waiting_title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("✍️ Теперь введите описание модели:")
    await state.set_state(AddModel.waiting_desc)

@dp.message(AddModel.waiting_desc)
async def process_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("💰 Введите стоимость (только цифры, например: 1500):")
    await state.set_state(AddModel.waiting_price)

@dp.message(AddModel.waiting_price)
async def process_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введите только число (например: 1500).")
        return
        
    price = int(message.text)
    data = await state.get_data()
    
    add_model(
        title=data['title'],
        description=data['description'],
        price=price,
        photo_path=data['photo_path']
    )
    
    await state.clear()
    await message.answer("✅ Модель успешно добавлена в каталог! Она уже видна в мини-аппе.")

# --- ВЕБ-СЕРВЕР (FASTAPI) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запускаем бота при старте сервера
    asyncio.create_task(dp.start_polling(bot))
    yield
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

# Разрешаем доступ к папке uploads (для фото)
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# API для получения списка моделей
@app.get("/api/models")
async def api_get_models():
    return JSONResponse(content=get_models())

# Отдаем index.html
@app.get("/")
async def serve_index():
    return FileResponse("webapp/index.html")

# Отдаем js файлы, если понадобятся
app.mount("/webapp", StaticFiles(directory="webapp"), name="webapp")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)