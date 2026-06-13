"""
Telegram-бот для заказа черчения
Версия для python-telegram-bot==21.5
"""

import os
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)

BOT_TOKEN = "8635597460:AAFK2X8t7eAAreAzgVMFPpVVPcMQKISdZok"
ADMIN_IDS = [5433618355]

PROFI_PHONE, PROFI_GROUP, PROFI_NAME, PROFI_RULES = range(4)
ORDER_TEACHER, ORDER_PHOTOS = range(10, 12)

DB_FILE = "db.json"

RULES_TEXT = """📋 *Правила для Профи:*

1. Выполнять заказы качественно и в срок
2. Не пропадать после принятия заказа
3. Присылать фото готовой работы до сдачи
4. При проблемах — сразу сообщать заказчику
5. Цену обговаривать лично

Нажми *Принять*, чтобы продолжить регистрацию."""

logging.basicConfig(level=logging.INFO)

def load_db():
    if not os.path.exists(DB_FILE):
        return {"profi": {}, "orders": [], "order_counter": 0}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def main_keyboard(is_admin=False):
    kb = [
        [InlineKeyboardButton("📐 Профи", callback_data="menu_profi")],
        [InlineKeyboardButton("📦 Заказ", callback_data="menu_order")],
    ]
    if is_admin:
        kb.append([InlineKeyboardButton("🔧 Админ панель", callback_data="menu_admin")])
    return InlineKeyboardMarkup(kb)

# ── START ──────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Добро пожаловать!\n\nВыбери раздел:",
        reply_markup=main_keyboard(update.effective_user.id in ADMIN_IDS)
    )

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "Главное меню:",
        reply_markup=main_keyboard(q.from_user.id in ADMIN_IDS)
    )

# ── ПРОФИ ─────────────────────────────────────────────────────────────────────
async def menu_profi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    db = load_db()
    uid = str(q.from_user.id)
    if uid in db["profi"]:
        p = db["profi"][uid]
        await q.edit_message_text(
            f"✅ *Твой профиль Профи:*\n\n👤 {p['name']}\n📚 Группа: {p['group']}\n📞 Тел: {p['phone']}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Изменить", callback_data="profi_register"),
                 InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
            ])
        )
    else:
        await q.edit_message_text(
            "📐 *Раздел Профи*\n\nЗаполни профиль чтобы принимать заказы.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Зарегистрироваться", callback_data="profi_register")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
            ])
        )

async def profi_register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("📞 Введи свой *рабочий номер телефона:*", parse_mode="Markdown")
    return PROFI_PHONE

async def profi_get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["profi_phone"] = update.message.text
    await update.message.reply_text("📚 Введи свою *группу:*", parse_mode="Markdown")
    return PROFI_GROUP

async def profi_get_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["profi_group"] = update.message.text
    await update.message.reply_text("👤 Введи *имя и фамилию:*", parse_mode="Markdown")
    return PROFI_NAME

async def profi_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["profi_name"] = update.message.text
    await update.message.reply_text(
        RULES_TEXT, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Принять правила", callback_data="profi_accept"),
             InlineKeyboardButton("❌ Отмена", callback_data="back_main")]
        ])
    )
    return PROFI_RULES

async def profi_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    db = load_db()
    uid = str(q.from_user.id)
    db["profi"][uid] = {
        "name": context.user_data["profi_name"],
        "group": context.user_data["profi_group"],
        "phone": context.user_data["profi_phone"],
        "registered_at": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    save_db(db)
    await q.edit_message_text(
        f"🎉 *Профиль создан!*\n\n"
        f"👤 {db['profi'][uid]['name']}\n"
        f"📚 {db['profi'][uid]['group']}\n"
        f"📞 {db['profi'][uid]['phone']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ В главное меню", callback_data="back_main")]])
    )
    return ConversationHandler.END

async def conv_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END

# ── ЗАКАЗ ─────────────────────────────────────────────────────────────────────
async def menu_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = [
        [InlineKeyboardButton("1 день", callback_data="od_1"), InlineKeyboardButton("2 дня", callback_data="od_2")],
        [InlineKeyboardButton("3 дня", callback_data="od_3"), InlineKeyboardButton("4 дня", callback_data="od_4")],
        [InlineKeyboardButton("5 дней", callback_data="od_5"), InlineKeyboardButton("6 дней", callback_data="od_6")],
        [InlineKeyboardButton("7 дней", callback_data="od_7"), InlineKeyboardButton("8 дней", callback_data="od_8")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
    ]
    await q.edit_message_text("📦 *Выбери срок выполнения:*", parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup(kb))

async def order_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["order_days"] = int(q.data.split("_")[1])
    context.user_data["order_photos"] = []
    await q.edit_message_text(
        f"✅ Срок: *{context.user_data['order_days']} дн.*\n\n👨‍🏫 Напиши ФИО *преподавателя:*",
        parse_mode="Markdown"
    )
    return ORDER_TEACHER

async def order_get_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["order_teacher"] = update.message.text
    await update.message.reply_text(
        "📸 Пришли *фото чертежей* (от 1 до 10 штук).\nКогда загрузишь все — нажми *«Готово»*.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Готово", callback_data="order_done")]])
    )
    return ORDER_PHOTOS

async def order_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photos = context.user_data.get("order_photos", [])
    if len(photos) >= 10:
        await update.message.reply_text("⚠️ Максимум 10 фото. Нажми *«Готово»*.", parse_mode="Markdown")
        return ORDER_PHOTOS
    photos.append(update.message.photo[-1].file_id)
    context.user_data["order_photos"] = photos
    await update.message.reply_text(
        f"📎 Фото {len(photos)}/10",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Готово", callback_data="order_done")]])
    )
    return ORDER_PHOTOS

async def order_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    photos = context.user_data.get("order_photos", [])
    if not photos:
        await q.answer("⚠️ Загрузи хотя бы 1 фото!", show_alert=True)
        return ORDER_PHOTOS

    db = load_db()
    db["order_counter"] = db.get("order_counter", 0) + 1
    user = q.from_user
    order = {
        "id": db["order_counter"],
        "user_id": user.id,
        "username": user.username or "",
        "first_name": user.first_name or "",
        "days": context.user_data["order_days"],
        "teacher": context.user_data["order_teacher"],
        "photos": photos,
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "status": "новый"
    }
    db["orders"].append(order)
    save_db(db)

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"🆕 *Новый заказ #{order['id']}*\n\n"
                f"👤 {user.first_name} (@{user.username})\n"
                f"⏱ Срок: {order['days']} дн.\n"
                f"👨‍🏫 Преподаватель: {order['teacher']}\n"
                f"📸 Фото: {len(photos)} шт.",
                parse_mode="Markdown"
            )
            from telegram import InputMediaPhoto
            await context.bot.send_media_group(admin_id, [InputMediaPhoto(f) for f in photos])
        except Exception as e:
            logging.error(e)

    await q.edit_message_text(
        f"✅ *Заказ #{order['id']} принят!*\n\n⏳ Ожидайте — с вами свяжутся.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ В главное меню", callback_data="back_main")]])
    )
    return ConversationHandler.END

# ── АДМИН ─────────────────────────────────────────────────────────────────────
async def menu_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id not in ADMIN_IDS:
        return
    await q.edit_message_text(
        "🔧 *Админ панель*", parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Заказчики", callback_data="adm_customers")],
            [InlineKeyboardButton("⚡ Короткие (1-4 дн.)", callback_data="adm_short")],
            [InlineKeyboardButton("🕐 Долгие (5-8 дн.)", callback_data="adm_long")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
        ])
    )

async def adm_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id not in ADMIN_IDS:
        return
    is_short = q.data == "adm_short"
    days_range = list(range(1, 5)) if is_short else list(range(5, 9))
    db = load_db()
    orders = [o for o in db["orders"] if o["days"] in days_range]
    label = "Короткие" if is_short else "Долгие"
    if not orders:
        await q.edit_message_text(f"📭 Заказов нет.",
                                   reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="menu_admin")]]))
        return
    kb = [[InlineKeyboardButton(f"#{o['id']} {o['days']}дн. {o['first_name']} | {o['teacher']}", callback_data=f"adm_o_{o['id']}")] for o in orders]
    kb.append([InlineKeyboardButton("◀️ Назад", callback_data="menu_admin")])
    await q.edit_message_text(f"📂 *{label} сроки:*", parse_mode="Markdown",
                               reply_markup=InlineKeyboardMarkup(kb))

async def adm_view_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id not in ADMIN_IDS:
        return
    oid = int(q.data.split("_")[2])
    db = load_db()
    o = next((x for x in db["orders"] if x["id"] == oid), None)
    if not o:
        return
    await q.edit_message_text(
        f"📋 *Заказ #{o['id']}*\n\n👤 {o['first_name']} (@{o.get('username','—')})\n"
        f"⏱ {o['days']} дн.\n👨‍🏫 {o['teacher']}\n📸 {len(o['photos'])} фото\n🕒 {o['created_at']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📸 Фото", callback_data=f"adm_ph_{oid}"),
             InlineKeyboardButton("👤 Профиль", callback_data=f"adm_cu_{o['user_id']}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="adm_short" if o['days'] <= 4 else "adm_long")]
        ])
    )

async def adm_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id not in ADMIN_IDS:
        return
    oid = int(q.data.split("_")[2])
    db = load_db()
    o = next((x for x in db["orders"] if x["id"] == oid), None)
    if not o or not o["photos"]:
        return
    from telegram import InputMediaPhoto
    await context.bot.send_media_group(q.from_user.id, [InputMediaPhoto(f) for f in o["photos"]])

async def adm_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id not in ADMIN_IDS:
        return
    db = load_db()
    seen = {}
    for o in db["orders"]:
        if o["user_id"] not in seen:
            seen[o["user_id"]] = o
    if not seen:
        await q.edit_message_text("📭 Нет заказчиков.",
                                   reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="menu_admin")]]))
        return
    kb = [[InlineKeyboardButton(f"{o['first_name']} (@{o.get('username','—')})", callback_data=f"adm_cu_{uid}")] for uid, o in seen.items()]
    kb.append([InlineKeyboardButton("◀️ Назад", callback_data="menu_admin")])
    await q.edit_message_text("👥 *Заказчики:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def adm_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id not in ADMIN_IDS:
        return
    tid = int(q.data.split("_")[2])
    db = load_db()
    orders = [o for o in db["orders"] if o["user_id"] == tid]
    if not orders:
        return
    s = orders[0]
    profi = db["profi"].get(str(tid), {})
    name = profi.get("name", s["first_name"])
    group = profi.get("group", "—")
    phone = profi.get("phone", "—")
    teachers = list({o["teacher"] for o in orders})
    total_photos = sum(len(o["photos"]) for o in orders)
    await q.edit_message_text(
        f"👤 *Профиль заказчика*\n\nИмя: {name}\nГруппа: {group}\nТелефон: {phone}\n"
        f"Преподаватели: {', '.join(teachers)}\nЗаказов: {len(orders)}\nФото: {total_photos}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📸 Все фото", callback_data=f"adm_cp_{tid}")],
            [InlineKeyboardButton("◀️ Назад", callback_data="adm_customers")]
        ])
    )

async def adm_customer_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id not in ADMIN_IDS:
        return
    tid = int(q.data.split("_")[2])
    db = load_db()
    all_photos = []
    for o in db["orders"]:
        if o["user_id"] == tid:
            all_photos.extend(o["photos"])
    all_photos = all_photos[:10]
    if not all_photos:
        return
    from telegram import InputMediaPhoto
    await context.bot.send_media_group(q.from_user.id, [InputMediaPhoto(f) for f in all_photos])

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    profi_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(profi_register_start, pattern="^profi_register$")],
        states={
            PROFI_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, profi_get_phone)],
            PROFI_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, profi_get_group)],
            PROFI_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, profi_get_name)],
            PROFI_RULES: [CallbackQueryHandler(profi_accept, pattern="^profi_accept$")],
        },
        fallbacks=[CommandHandler("cancel", conv_cancel)],
        per_message=False
    )

    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(order_deadline, pattern="^od_")],
        states={
            ORDER_TEACHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_get_teacher)],
            ORDER_PHOTOS:  [
                MessageHandler(filters.PHOTO, order_photo),
                CallbackQueryHandler(order_done, pattern="^order_done$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", conv_cancel)],
        per_message=False
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(profi_conv)
    app.add_handler(order_conv)
    app.add_handler(CallbackQueryHandler(back_to_main,       pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(menu_profi,         pattern="^menu_profi$"))
    app.add_handler(CallbackQueryHandler(menu_order,         pattern="^menu_order$"))
    app.add_handler(CallbackQueryHandler(menu_admin,         pattern="^menu_admin$"))
    app.add_handler(CallbackQueryHandler(adm_orders,         pattern="^adm_(short|long)$"))
    app.add_handler(CallbackQueryHandler(adm_view_order,     pattern="^adm_o_\\d+$"))
    app.add_handler(CallbackQueryHandler(adm_photos,         pattern="^adm_ph_\\d+$"))
    app.add_handler(CallbackQueryHandler(adm_customers,      pattern="^adm_customers$"))
    app.add_handler(CallbackQueryHandler(adm_customer,       pattern="^adm_cu_\\d+$"))
    app.add_handler(CallbackQueryHandler(adm_customer_photos,pattern="^adm_cp_\\d+$"))

    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
