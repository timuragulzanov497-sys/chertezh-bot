"""
Telegram-бот для заказа черчения
Запуск: pip install python-telegram-bot==20.7
python bot.py
"""

import os
import json
import logging
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)

# ─── НАСТРОЙКИ ───────────────────────────────────────────────────────────────
BOT_TOKEN = "8635597460:AAFK2X8t7eAAreAzgVMFPpVVPcMQKISdZok"
ADMIN_IDS = [5433618355]  # ← замени на свой Telegram ID

# ─── СОСТОЯНИЯ ConversationHandler ───────────────────────────────────────────
# Профи — регистрация
PROFI_PHONE, PROFI_GROUP, PROFI_NAME, PROFI_RULES = range(4)

# Заказчик — заказ
ORDER_DEADLINE, ORDER_TEACHER, ORDER_PHOTOS, ORDER_CONFIRM = range(10, 14)

# ─── БАЗА ДАННЫХ (JSON-файл) ──────────────────────────────────────────────────
DB_FILE = "db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {"profi": {}, "orders": [], "order_counter": 0}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

# ─── ПРАВИЛА (заполни свои) ───────────────────────────────────────────────────
RULES_TEXT = """📋 *Правила для Профи:*

1. Выполнять заказы качественно и в срок
2. Не пропадать после принятия заказа
3. Присылать фото готовой работы до сдачи
4. При проблемах — сразу сообщать заказчику
5. Цену обговаривать лично

Нажми *Принять*, чтобы продолжить регистрацию."""

logging.basicConfig(level=logging.INFO)

# ═══════════════════════════════════════════════════════════════════════════════
#  ГЛАВНОЕ МЕНЮ
# ═══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("📐 Профи", callback_data="menu_profi")],
        [InlineKeyboardButton("📦 Заказ", callback_data="menu_order")],
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🔧 Админ панель", callback_data="menu_admin")])

    await update.message.reply_text(
        "👋 Добро пожаловать!\n\nВыбери раздел:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    keyboard = [
        [InlineKeyboardButton("📐 Профи", callback_data="menu_profi")],
        [InlineKeyboardButton("📦 Заказ", callback_data="menu_order")],
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🔧 Админ панель", callback_data="menu_admin")])
    await query.edit_message_text("Главное меню:", reply_markup=InlineKeyboardMarkup(keyboard))

# ═══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ «ПРОФИ»
# ═══════════════════════════════════════════════════════════════════════════════

async def menu_profi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = load_db()
    user_id = str(query.from_user.id)

    if user_id in db["profi"]:
        p = db["profi"][user_id]
        text = (
            f"✅ *Твой профиль Профи:*\n\n"
            f"👤 {p['name']}\n"
            f"📚 Группа: {p['group']}\n"
            f"📞 Телефон: {p['phone']}"
        )
        keyboard = [[InlineKeyboardButton("✏️ Изменить профиль", callback_data="profi_edit"),
                     InlineKeyboardButton("◀️ Назад", callback_data="back_main")]]
        await query.edit_message_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        keyboard = [
            [InlineKeyboardButton("📝 Зарегистрироваться как Профи", callback_data="profi_register")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
        ]
        await query.edit_message_text(
            "📐 *Раздел Профи*\n\nЧтобы принимать заказы, нужно заполнить профиль.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def profi_register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📞 Введи свой *рабочий номер телефона:*", parse_mode="Markdown")
    return PROFI_PHONE

async def profi_get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["profi_phone"] = update.message.text
    await update.message.reply_text("📚 Введи свою *группу:*", parse_mode="Markdown")
    return PROFI_GROUP

async def profi_get_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["profi_group"] = update.message.text
    await update.message.reply_text("👤 Введи своё *имя и фамилию:*", parse_mode="Markdown")
    return PROFI_NAME

async def profi_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["profi_name"] = update.message.text
    keyboard = [[InlineKeyboardButton("✅ Принять правила", callback_data="profi_accept_rules"),
                 InlineKeyboardButton("❌ Отмена", callback_data="back_main")]]
    await update.message.reply_text(
        RULES_TEXT,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PROFI_RULES

async def profi_accept_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = load_db()
    user_id = str(query.from_user.id)
    db["profi"][user_id] = {
        "name": context.user_data["profi_name"],
        "group": context.user_data["profi_group"],
        "phone": context.user_data["profi_phone"],
        "registered_at": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    save_db(db)
    keyboard = [[InlineKeyboardButton("◀️ В главное меню", callback_data="back_main")]]
    await query.edit_message_text(
        f"🎉 *Профиль создан!*\n\n"
        f"👤 {db['profi'][user_id]['name']}\n"
        f"📚 {db['profi'][user_id]['group']}\n"
        f"📞 {db['profi'][user_id]['phone']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END

async def profi_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ═══════════════════════════════════════════════════════════════════════════════
#  РАЗДЕЛ «ЗАКАЗ»
# ═══════════════════════════════════════════════════════════════════════════════

async def menu_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton("1 день", callback_data="order_day_1"),
            InlineKeyboardButton("2 дня", callback_data="order_day_2"),
        ],
        [
            InlineKeyboardButton("3 дня", callback_data="order_day_3"),
            InlineKeyboardButton("4 дня", callback_data="order_day_4"),
        ],
        [
            InlineKeyboardButton("5 дней", callback_data="order_day_5"),
            InlineKeyboardButton("6 дней", callback_data="order_day_6"),
        ],
        [
            InlineKeyboardButton("7 дней", callback_data="order_day_7"),
            InlineKeyboardButton("8 дней", callback_data="order_day_8"),
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
    ]
    await query.edit_message_text(
        "📦 *Оформление заказа*\n\nВыбери срок выполнения:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def order_select_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    days = int(query.data.split("_")[2])
    context.user_data["order_days"] = days
    await query.edit_message_text(
        f"✅ Срок: *{days} {'день' if days == 1 else 'дней' if days >= 5 else 'дня'}*\n\n"
        f"👨‍🏫 Напиши ФИО *преподавателя:*",
        parse_mode="Markdown"
    )
    return ORDER_TEACHER

async def order_get_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["order_teacher"] = update.message.text
    context.user_data["order_photos"] = []
    await update.message.reply_text(
        "📸 Пришли *фотографии чертежей* (от 1 до 10 штук).\n\n"
        "Когда загрузишь все — нажми кнопку *«Готово»*.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Готово", callback_data="order_photos_done")
        ]])
    )
    return ORDER_PHOTOS

async def order_receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photos = context.user_data.get("order_photos", [])
    if len(photos) >= 10:
        await update.message.reply_text("⚠️ Максимум 10 фотографий. Нажми *«Готово»*.",
                                        parse_mode="Markdown")
        return ORDER_PHOTOS
    file_id = update.message.photo[-1].file_id
    photos.append(file_id)
    context.user_data["order_photos"] = photos
    await update.message.reply_text(
        f"📎 Фото {len(photos)}/10 принято.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Готово", callback_data="order_photos_done")
        ]])
    )
    return ORDER_PHOTOS

async def order_photos_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    photos = context.user_data.get("order_photos", [])
    if not photos:
        await query.answer("⚠️ Нужно загрузить хотя бы 1 фото!", show_alert=True)
        return ORDER_PHOTOS

    days = context.user_data["order_days"]
    teacher = context.user_data["order_teacher"]
    user = query.from_user

    db = load_db()
    db["order_counter"] = db.get("order_counter", 0) + 1
    order = {
        "id": db["order_counter"],
        "user_id": user.id,
        "username": user.username or "",
        "first_name": user.first_name or "",
        "days": days,
        "teacher": teacher,
        "photos": photos,
        "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "status": "новый"
    }
    db["orders"].append(order)
    save_db(db)

    # Уведомить всех админов
    label = "коротком" if days <= 4 else "долгом"
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"🆕 *Новый заказ #{order['id']}*\n\n"
                f"👤 {user.first_name} (@{user.username})\n"
                f"⏱ Срок: {days} дн. ({label} сроке)\n"
                f"👨‍🏫 Преподаватель: {teacher}\n"
                f"📸 Фото: {len(photos)} шт.",
                parse_mode="Markdown"
            )
            # Отправить фото пачкой
            from telegram import InputMediaPhoto
            media = [InputMediaPhoto(fid) for fid in photos]
            await context.bot.send_media_group(admin_id, media)
        except Exception as e:
            logging.error(f"Не удалось уведомить админа {admin_id}: {e}")

    keyboard = [[InlineKeyboardButton("◀️ В главное меню", callback_data="back_main")]]
    await query.edit_message_text(
        f"✅ *Заказ #{order['id']} принят!*\n\n"
        f"⏳ Ожидайте — с вами свяжутся в ближайшее время.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END

# ═══════════════════════════════════════════════════════════════════════════════
#  АДМИН ПАНЕЛЬ
# ═══════════════════════════════════════════════════════════════════════════════

async def menu_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("⛔ Нет доступа", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton("📋 Заказчики", callback_data="admin_customers")],
        [InlineKeyboardButton("⚡ Короткие сроки (1-4 дн.)", callback_data="admin_short")],
        [InlineKeyboardButton("🕐 Долгие сроки (5-8 дн.)", callback_data="admin_long")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
    ]
    await query.edit_message_text(
        "🔧 *Админ панель*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_orders_by_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return

    is_short = query.data == "admin_short"
    days_range = range(1, 5) if is_short else range(5, 9)
    label = "Короткие" if is_short else "Долгие"

    db = load_db()
    orders = [o for o in db["orders"] if o["days"] in days_range]

    if not orders:
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="menu_admin")]]
        await query.edit_message_text(
            f"📭 Заказов в разделе «{label} сроки» пока нет.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Группируем по дням
    by_day = {}
    for o in orders:
        by_day.setdefault(o["days"], []).append(o)

    keyboard = []
    for day in sorted(by_day.keys()):
        for o in by_day[day]:
            keyboard.append([InlineKeyboardButton(
                f"#{o['id']} | {o['days']} дн. | {o['first_name']} | {o['teacher']}",
                callback_data=f"admin_order_{o['id']}"
            )])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="menu_admin")])

    await query.edit_message_text(
        f"📂 *{label} сроки:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_view_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return

    order_id = int(query.data.split("_")[2])
    db = load_db()
    order = next((o for o in db["orders"] if o["id"] == order_id), None)
    if not order:
        await query.answer("Заказ не найден", show_alert=True)
        return

    text = (
        f"📋 *Заказ #{order['id']}*\n\n"
        f"👤 {order['first_name']} (@{order.get('username', '—')})\n"
        f"⏱ Срок: {order['days']} дн.\n"
        f"👨‍🏫 Преподаватель: {order['teacher']}\n"
        f"📸 Фото: {len(order['photos'])} шт.\n"
        f"🕒 Создан: {order['created_at']}\n"
        f"📌 Статус: {order['status']}"
    )
    keyboard = [
        [InlineKeyboardButton("📸 Показать фото", callback_data=f"admin_photos_{order_id}")],
        [InlineKeyboardButton("👤 Профиль заказчика", callback_data=f"admin_cust_{order['user_id']}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_short" if order['days'] <= 4 else "admin_long")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_show_order_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return

    order_id = int(query.data.split("_")[2])
    db = load_db()
    order = next((o for o in db["orders"] if o["id"] == order_id), None)
    if not order or not order["photos"]:
        await query.answer("Фото не найдены", show_alert=True)
        return

    from telegram import InputMediaPhoto
    media = [InputMediaPhoto(fid) for fid in order["photos"]]
    await context.bot.send_media_group(query.from_user.id, media)
    await query.answer(f"Отправил {len(order['photos'])} фото в чат")

async def admin_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return

    db = load_db()
    # Уникальные заказчики из заказов
    seen = {}
    for o in db["orders"]:
        uid = o["user_id"]
        if uid not in seen:
            seen[uid] = o

    if not seen:
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="menu_admin")]]
        await query.edit_message_text("📭 Заказчиков пока нет.",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return

    keyboard = []
    for uid, o in seen.items():
        keyboard.append([InlineKeyboardButton(
            f"{o['first_name']} (@{o.get('username', '—')})",
            callback_data=f"admin_cust_{uid}"
        )])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="menu_admin")])
    await query.edit_message_text("👥 *Заказчики:*", parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_customer_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return

    target_id = int(query.data.split("_")[2])
    db = load_db()

    # Все заказы этого пользователя
    user_orders = [o for o in db["orders"] if o["user_id"] == target_id]
    if not user_orders:
        await query.answer("Нет заказов", show_alert=True)
        return

    sample = user_orders[0]
    all_photos = []
    for o in user_orders:
        all_photos.extend(o["photos"])
    all_photos = all_photos[:10]  # Показываем до 10

    teachers = list({o["teacher"] for o in user_orders})

    # Попытаться получить телефон из профи-базы (если он профи)
    phone = "—"
    group = "—"
    name = sample["first_name"]
    profi = db["profi"].get(str(target_id))
    if profi:
        phone = profi["phone"]
        group = profi["group"]
        name = profi["name"]

    text = (
        f"👤 *Профиль заказчика*\n\n"
        f"Имя: {name}\n"
        f"Группа: {group}\n"
        f"Телефон: {phone}\n"
        f"Преподаватели: {', '.join(teachers)}\n"
        f"Всего заказов: {len(user_orders)}\n"
        f"Всего фото: {len(all_photos)}"
    )
    keyboard = [
        [InlineKeyboardButton("📸 Все фото (до 10)", callback_data=f"admin_custphotos_{target_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_customers")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_customer_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return

    target_id = int(query.data.split("_")[2])
    db = load_db()
    user_orders = [o for o in db["orders"] if o["user_id"] == target_id]
    all_photos = []
    for o in user_orders:
        all_photos.extend(o["photos"])
    all_photos = all_photos[:10]

    if not all_photos:
        await query.answer("Фото не найдены", show_alert=True)
        return

    from telegram import InputMediaPhoto
    media = [InputMediaPhoto(fid) for fid in all_photos]
    await context.bot.send_media_group(query.from_user.id, media)
    await query.answer(f"Отправил {len(all_photos)} фото")

# ═══════════════════════════════════════════════════════════════════════════════
#  СБОРКА ПРИЛОЖЕНИЯ
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler — регистрация Профи
    profi_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(profi_register_start, pattern="^profi_register$")],
        states={
            PROFI_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, profi_get_phone)],
            PROFI_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, profi_get_group)],
            PROFI_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, profi_get_name)],
            PROFI_RULES: [CallbackQueryHandler(profi_accept_rules, pattern="^profi_accept_rules$")],
        },
        fallbacks=[CommandHandler("cancel", profi_cancel),
                   CallbackQueryHandler(back_to_main, pattern="^back_main$")],
        per_message=False
    )

    # ConversationHandler — оформление заказа
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(order_select_deadline, pattern="^order_day_")],
        states={
            ORDER_TEACHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_get_teacher)],
            ORDER_PHOTOS:  [
                MessageHandler(filters.PHOTO, order_receive_photo),
                CallbackQueryHandler(order_photos_done, pattern="^order_photos_done$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", profi_cancel),
                   CallbackQueryHandler(back_to_main, pattern="^back_main$")],
        per_message=False
    )

    # Обычные хендлеры
    app.add_handler(CommandHandler("start", start))
    app.add_handler(profi_conv)
    app.add_handler(order_conv)
    app.add_handler(CallbackQueryHandler(back_to_main,              pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(menu_profi,                pattern="^menu_profi$"))
    app.add_handler(CallbackQueryHandler(menu_order,                pattern="^menu_order$"))
    app.add_handler(CallbackQueryHandler(menu_admin,                pattern="^menu_admin$"))
    app.add_handler(CallbackQueryHandler(admin_orders_by_range,     pattern="^admin_(short|long)$"))
    app.add_handler(CallbackQueryHandler(admin_view_order,          pattern="^admin_order_\\d+$"))
    app.add_handler(CallbackQueryHandler(admin_show_order_photos,   pattern="^admin_photos_\\d+$"))
    app.add_handler(CallbackQueryHandler(admin_customers,           pattern="^admin_customers$"))
    app.add_handler(CallbackQueryHandler(admin_customer_profile,    pattern="^admin_cust_\\d+$"))
    app.add_handler(CallbackQueryHandler(admin_customer_photos,     pattern="^admin_custphotos_\\d+$"))

    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
