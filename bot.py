import asyncio
import logging
import random
import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- SOZLAMALAR ---
BOT_TOKEN = "8622322061:AAHZagvBHRnZyr9pZHfTd8Z7cjFANEfFmtM"
ADMIN_ID = 123456789  # O'zingizning Telegram ID'ingizni yozing (@userinfobot orqali olish mumkin)
ADMIN_USERNAME = "achilov_otabek"

# Kanal va guruhlar ro'yxati (Faqat 2 ta manba)
CHANNELS = [
    {"name": "1-Guruh", "url": "https://t.me/achilovotabekh", "id": "@achilovotabekh"},
    {"name": "2-Kanal", "url": "https://t.me/ITCENTERSHAHRISABZ", "id": "@ITCENTERSHAHRISABZ"}
]

DB_NAME = "referral_bot.db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# FSM holati (Pul chiqarish uchun)
class WithdrawState(StatesGroup):
    waiting_for_details = State()

# --- BAZA BILAN ISHLASH ---
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                referrer_id INTEGER,
                balance INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                status TEXT DEFAULT 'active'
            )
        """)
        await db.commit()

# --- MAIN MENU TUGMALARI ---
def get_main_menu():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📜 Konkurs shartlari"), KeyboardButton(text="🎁 Yutuqlar")],
            [KeyboardButton(text="🚀 Konkursda qatnashish"), KeyboardButton(text="💰 To'plagan pullarim")],
            [KeyboardButton(text="💳 Pullarni chiqarish"), KeyboardButton(text="👨‍💻 Admin bilan bog'lanish")],
            [KeyboardButton(text="🏆 Reyting")]
        ],
        resize_keyboard=True
    )
    return kb

# --- OBUNA TEKSHIRISH TUGMALARI ---
def get_subscription_keyboard():
    buttons = []
    for ch in CHANNELS:
        buttons.append([InlineKeyboardButton(text=f"➕ {ch['name']}", url=ch['url'])])
    buttons.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- OBUNANI TEKSHIRISH FUNKSIYASI ---
async def is_subscribed(user_id: int) -> bool:
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch["id"], user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

# --- HANDLERLAR ---

@dp.message(CommandStart())
async def start_handler(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    args = command.args # Referal ID parametr

    referrer_id = int(args) if args and args.isdigit() and int(args) != user_id else None

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user_exists = await cursor.fetchone()

        if not user_exists:
            await db.execute(
                "INSERT INTO users (user_id, full_name, referrer_id) VALUES (?, ?, ?)",
                (user_id, full_name, referrer_id)
            )
            await db.commit()

    if not await is_subscribed(user_id):
        await message.answer(
            "👋 **Assalomu alaykum!**\n\nBotdan to'liq foydalanish va konkursda qatnashish uchun quyidagi guruh va kanalimizga a'zo bo'ling:",
            reply_markup=get_subscription_keyboard()
        )
    else:
        await message.answer("🎉 **Xush kelibsiz!** Bo'limlardan birini tanlang:", reply_markup=get_main_menu())

@dp.callback_query(F.data == "check_subscription")
async def check_sub_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await is_subscribed(user_id):
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                referrer_id = row[0] if row else None

            if referrer_id:
                async with db.execute("SELECT id FROM referrals WHERE referred_id = ?", (user_id,)) as ref_cursor:
                    already_counted = await ref_cursor.fetchone()

                if not already_counted:
                    await db.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, user_id))
                    await db.execute("UPDATE users SET balance = balance + 2000 WHERE user_id = ?", (referrer_id,))
                    await db.commit()

                    try:
                        await bot.send_message(referrer_id, "🎉 Siz taklif qilgan do'stingiz barcha guruh/kanallarga a'zo bo'ldi! Balansingizga +2 000 so'm qo'shildi.")
                    except Exception:
                        pass

        await callback.message.delete()
        await callback.message.answer("✅ Obunalar tasdiqlandi! Asosiy menyu:", reply_markup=get_main_menu())
    else:
        await callback.answer("❌ Siz hali barcha guruh va kanallarga a'zo bo'lmadingiz!", show_alert=True)

# 1-TUGMA: KONKURS SHARTLARI
@dp.message(F.text == "📜 Konkurs shartlari")
async def terms_handler(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        await message.answer("⚠️ Botdan foydalanish uchun manbalarga obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return

    text = (
        f"✨ **Assalomu alaykum, hurmatli {message.from_user.full_name}!** ✨\n\n"
        f"Bizning eksklyuziv konkursimizda sizni ko'rib turganimizdan juda xursandmiz! 🥳\n\n"
        f"📌 **Konkursimiz shartlari juda oddiy:**\n"
        f"Sizga taqdim etilgan maxsus **referal havolani** do'stlaringiz va yaqinlaringizga ulashing. "
        f"Agar ular siz yuborgan havola orqali botimizga kirib, barcha kanal va guruhlarimizga a'zo bo'lishsa, "
        f"sizga **har bir taklif qilingan inson uchun 2 000 so'm** beriladi! 💵✨\n\n"
        f"⚠️ **Eslatma:**\n"
        f"Siz taklif qilgan insonlar manbalarimizdan kamida **1 hafta** mobaynida chiqib ketmasliklari kerak! "
        f"Aks holda ularga berilgan pul balansingizdan ayirib tashlanadi.\n\n"
        f"💳 Balansingiz umumiy hisobda **50 000 so'm**ga yetganida, pullarni yechib olish uchun ariza topshirishingiz mumkin. "
        f"Mablag'lar 3 kun vaqt ichida karta raqamingizga o'tkazib beriladi. 🏦\n\n"
        f"📊 Har bir kirgan va chiqib ketgan odamlarni hamda umumiy balansingizni **'💰 To'plagan pullarim'** oynasida ko'rishingiz mumkin.\n\n"
        f"🌟 Endigi navbat sizda! **'🚀 Konkursda qatnashish'** tugmasini bosing va siz uchun ajratilgan referal havolani do'stlaringizga ulashishni boshlang! Omad! 🚀"
    )
    await message.answer(text)

# 2-TUGMA: YUTUQLAR
@dp.message(F.text == "🎁 Yutuqlar")
async def prizes_handler(message: types.Message):
    await message.answer("🎁 **Konkurs Yutuqlari:**\n\n1-o'rin: 1,000,000 so'm\n2-o'rin: 500,000 so'm\n3-o'rin: 250,000 so'm\n\nVa to'plagan har bir balansingizni kartangizga yechib olish imkoniyati!")

# 3-TUGMA: KONKURSDA QATNASHISH (REFERAL LINK & STATISTIKA)
@dp.message(F.text == "🚀 Konkursda qatnashish")
async def participate_handler(message: types.Message):
    user_id = message.from_user.id
    if not await is_subscribed(user_id):
        await message.answer("⚠️ Botdan foydalanish uchun manbalarga obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

    async with aiosqlite.connect(DB_NAME) as db:
        # To'liq a'zo bo'lganlar
        async with db.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND status = 'active'", (user_id,)) as c:
            active_refs = (await c.fetchone())[0]

        # Hali obuna bo'lmaganlar
        async with db.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ? AND user_id NOT IN (SELECT referred_id FROM referrals)", (user_id,)) as c:
            pending_refs = (await c.fetchone())[0]

    text = (
        f"🚀 **Sizning unikal referal havolangiz:**\n`{ref_link}`\n\n"
        f"📈 **Sizning takliflar statistikangiz:**\n"
        f"✅ Manbalarga to'liq a'zo bo'lganlar: **{active_refs} ta**\n"
        f"⏳ Hali obunani yakunlamaganlar: **{pending_refs} ta**\n\n"
        f"💡 Ushbu havolani do'stlaringizga yuboring va har bir to'liq a'zo bo'lgan foydalanuvchi uchun **2 000 so'm**ga ega bo'ling!"
    )
    await message.answer(text, parse_mode="Markdown")

# 4-TUGMA: TO'PLAGAN PULLARIM
@dp.message(F.text == "💰 To'plagan pullarim")
async def balance_handler(message: types.Message):
    user_id = message.from_user.id
    if not await is_subscribed(user_id):
        await message.answer("⚠️ Botdan foydalanish uchun manbalarga obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as c:
            row = await c.fetchone()
            balance = row[0] if row else 0

        async with db.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND status = 'active'", (user_id,)) as c:
            active_refs = (await c.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND status = 'left'", (user_id,)) as c:
            left_refs = (await c.fetchone())[0]

    text = (
        f"💳 **Sizning moliyaviy hisobingiz:**\n\n"
        f"💰 Asosiy balans: **{balance:,} so'm**\n"
        f"👥 Faol takliflar (2,000 so'mdan): **{active_refs} ta**\n"
        f"❌ Chiqib ketganlar: **{left_refs} ta**\n\n"
        f"📌 *Eslatma: Chiqib ketgan foydalanuvchilar uchun berilgan pullar avtomatik tarzda ayirib tashlanadi.*"
    )
    await message.answer(text)

# 5-TUGMA: PULLARNI CHIQRISH
@dp.message(F.text == "💳 Pullarni chiqarish")
async def withdraw_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not await is_subscribed(user_id):
        await message.answer("⚠️ Botdan foydalanish uchun manbalarga obuna bo'ling!", reply_markup=get_subscription_keyboard())
        return

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as c:
            balance = (await c.fetchone())[0]

    if balance < 50000:
        await message.answer(f"❌ **Balansingiz yetarli emas!**\n\nSizning balansingiz: **{balance:,} so'm**\nMinimal chiqarish summasi: **50 000 so'm**.")
        return

    await state.set_state(WithdrawState.waiting_for_details)
    await message.answer(
        "📝 **Pul chiqarish arizasi:**\n\n"
        "Iltimos, quyidagi ma'lumotlarni kiriting:\n"
        "1. **16 xonalik karta raqami**\n"
        "2. **Bank nomi** (masalan: Humo / Uzcard / Kapitalbank)\n"
        "3. **Ushbu kartaga ulangan telefon raqami**\n\n"
        "*(Masalan: 8600 1234 5678 9012, Kapitalbank, +998901234567)*"
    )

@dp.message(WithdrawState.waiting_for_details)
async def process_withdraw(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    details = message.text

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as c:
            balance = (await c.fetchone())[0]

        if balance < 50000:
            await message.answer("❌ Balansingizda minimal pul miqdori (50 000 so'm) yetarli emas!")
            await state.clear()
            return

        withdraw_amount = 100000 if balance >= 100000 else balance

        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (withdraw_amount, user_id))
        await db.commit()

    admin_text = (
        f"📥 **Yangi pul yechish arizasi!**\n\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name} (`{user_id}`)\n"
        f"💰 Chiqarish summasi: **{withdraw_amount:,} so'm**\n"
        f"📄 Revisitlar: \n{details}"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_text)
    except Exception:
        pass

    await message.answer(
        f"✅ **Arizangiz qabul qilindi!**\n\n"
        f"Sizning hisobingizdan **{withdraw_amount:,} so'm** yechildi.\n"
        f"Mablag' **3 ish kuni** ichida ko'rsatilgan karta raqamingizga o'tkaziladi."
    )
    await state.clear()

# 6-TUGMA: ADMIN BILAN BOG'LANISH
@dp.message(F.text == "👨‍💻 Admin bilan bog'lanish")
async def contact_admin(message: types.Message):
    await message.answer(f"💬 Har qanday savol va takliflar bo'yicha admin bilan bog'lanishingiz mumkin:\n\n👉 @{ADMIN_USERNAME}")

# 7-TUGMA: REYTING
@dp.message(F.text == "🏆 Reyting")
async def rating_handler(message: types.Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT u.full_name, COUNT(r.id) as ref_count 
            FROM users u 
            JOIN referrals r ON u.user_id = r.referrer_id 
            WHERE r.status = 'active'
            GROUP BY u.user_id 
            ORDER BY ref_count DESC 
            LIMIT 10
        """) as cursor:
            top_users = await cursor.fetchall()

    text = "🏆 **Eng ko'p do'st taklif qilgan TOP-10 ishtirokchilar:**\n\n"
    if top_users:
        for i, (name, count) in enumerate(top_users, 1):
            text += f"{i}. {name} — **{count} ta referal**\n"
    else:
        text += "Hali hech kim reytingga kirishga ulgurmadi."

    await message.answer(text)

# --- CHIQIB KETGAN USERLARNI NAZORAT QILISH ---
async def check_left_members_loop():
    while True:
        try:
            async with aiosqlite.connect(DB_NAME) as db:
                async with db.execute("SELECT id, referrer_id, referred_id FROM referrals WHERE status = 'active'") as cursor:
                    active_refs = await cursor.fetchall()

                for ref_id, referrer_id, referred_id in active_refs:
                    subscribed = await is_subscribed(referred_id)
                    if not subscribed:
                        await db.execute("UPDATE referrals SET status = 'left' WHERE id = ?", (ref_id,))
                        await db.execute("UPDATE users SET balance = MAX(0, balance - 2000) WHERE user_id = ?", (referrer_id,))
                        await db.commit()

                        try:
                            await bot.send_message(referrer_id, "⚠️ Siz taklif qilgan foydalanuvchi manbalardan chiqib ketdi. Balansingizdan 2 000 so'm ayirildi.")
                        except Exception:
                            pass
        except Exception as e:
            logging.error(f"Tekshiruvda xatolik: {e}")

        await asyncio.sleep(3600)

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    asyncio.create_task(check_left_members_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())