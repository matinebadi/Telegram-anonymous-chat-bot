import re
from typing import Union, List
import asyncio
import uuid
import random
from urllib.parse import quote, unquote
import telethon.tl.types
from telethon import TelegramClient, events, Button
from telethon.events import CallbackQuery , StopPropagation
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.errors import UserNotParticipantError
from telegram_anonymous_bot.models import ActiveChat

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import Session
import time

from datetime import datetime, timedelta

from .config import API_KEY, API_ID, BOT_TOKEN, PROXY, PATH_SESSION, COMMANDS, MESSAGES, TEMPLATES_MESSAGES
from .exceptions import CanceledError
from .logger import error_logger, info_log, TELEGRAM_LOG_LEVEL
from .models import User, Message, Action, Like , DirectMessage , is_blocked , UserBlock
from .repository import UserRepository, MessageRepository, ActionRepository
from .iran_location import IRAN_PROVINCES
from .models import ChatRequest
from .models import session_factory


import os


banned_users = {}      
# ✅ فیلتر بن
async def ban_filter(event):
    user_id = getattr(event, 'sender_id', None)
    if not user_id:
        return

    ban_until = banned_users.get(user_id)
    if ban_until and ban_until > time.time():
        remaining = datetime.fromtimestamp(ban_until).strftime("%Y-%m-%d %H:%M")
        try:
            if hasattr(event, 'answer'):
                await event.answer(f"⛔️ شما تا تاریخ {remaining}مسدود هستید.", alert=True)
            else:
                await event.respond(f"⛔️ شما تا تاریخ <b>{remaining}</b> مسدود هستید.", parse_mode='html')
        except:
            pass
        raise StopPropagation()





MEDIA_FOLDER = "media"
os.makedirs(MEDIA_FOLDER, exist_ok=True)


user_repository = UserRepository()
message_repository = MessageRepository()
info_log.log(level=TELEGRAM_LOG_LEVEL, msg='BOT CONNECTED TO SQLDB ...')
if PROXY is not None:
    client = TelegramClient(str(PATH_SESSION.joinpath('bot')), API_ID, API_KEY, proxy=PROXY, connection_retries=100000).start(
        bot_token=BOT_TOKEN)
else:
    client = TelegramClient(str(PATH_SESSION.joinpath('bot')), API_ID, API_KEY, connection_retries=100000).start(
        bot_token=BOT_TOKEN)
    
client.add_event_handler(ban_filter, events.NewMessage())
client.add_event_handler(ban_filter, events.CallbackQuery())

info_log.log(level=TELEGRAM_LOG_LEVEL, msg='BOT CONNECTED TO TELEGRAM ...')



async def reset_btns(event, message):
    buttons = [
        [Button.text("🔗 به یک ناشناس وصلم کن", resize=True)],  
        [Button.text(COMMANDS.CONNECT, resize=True), Button.text(COMMANDS.GIVE_MY_LINK, resize=True)],
        [Button.text("🤔 راهنما", resize=True), Button.text("👤 پروفایل من", resize=True)],
        [Button.text("🗣 پشتیبان تلگرام", resize=True)],
        [Button.text("📢 لینک معرفی ربات", resize=True)],
        
    ]
    await event.respond(message, buttons=buttons)



@client.on(events.NewMessage(pattern="🤔 راهنما"))
async def show_help(event):
    user = await event.get_sender()
    name = user.first_name or "کاربر عزیز"

    await reset_btns(event, (
        f"💡 {name} عزیز\n\n"
        "برای استفاده از ربات ابتدا باید عضو کانال معرفی‌شده بشید.\n\n"
        "1️⃣ روی «📢 عضویت در کانال» کلیک کنید و وارد کانال بشید.\n"
        "2️⃣ بعد از عضویت، برگردید به ربات و روی «✅ عضویت انجام شد» کلیک کنید.\n\n"
        "✅ سپس ربات برای شما فعال میشه و می‌تونید از تمام امکاناتش استفاده کنید.\n\n"
        "در صورت نیاز به پشتیبانی، با ادمین در تماس باشید. 🌟"
    ))




user_profile_state = {}



@client.on(events.NewMessage(pattern="👤 پروفایل من"))
async def show_profile(event):
    user_id = event.sender_id
    user = user_repository.get_user_with_id(user_id)

    if not user:
        await event.respond(
            "⛔️ شما هنوز پروفایلی نساختید!\nبرای ساخت پروفایل، روی دکمه «ایجاد پروفایل» کلیک کنید.",
            buttons=[[Button.inline("🆕 ایجاد پروفایل", data="start_profile")]]
        )
        return

    if not all([user.first_name, user.province, user.city, user.age]):
        await event.respond(
            "⛔️ پروفایل شما هنوز کامل نشده!\nبرای تکمیل، روی دکمه زیر بزنید:",
            buttons=[[Button.inline("🆕 ایجاد پروفایل", data="start_profile")]]
        )
        return

    full_name = f"{user.first_name} {user.last_name or ''}".strip()

    profile_text = f"""
<b>❖👤 پروفایل شما:</b>

⫸ 👤 <b>نام:</b> {full_name}
⫸ 🚻 <b>جنسیت:</b> {user.gender}
⫸ 📍 <b>استان:</b> {user.province}
⫸ 🏙️ <b>شهر:</b> {user.city}
⫸ 🎂 <b>سن:</b> {user.age}
⫸ ❤️ <b>تعداد لایک‌ها:</b> {user.likes_count or 0}

⫸ 📝 <b>بیو:</b> {user.bio or "ندارد"}


╏ 🆔 <b>آیدی:</b> /user_{str(user_id)[-4:]}


<i>🟢 شما هم‌اکنون آنلاین هستید</i>
""".strip()


    buttons = [[Button.inline("✏️ ویرایش پروفایل", data="edit_profile")], [Button.inline("🗑 حذف اکانت", data="confirm_delete_account")],]

    if user.profile_photo and os.path.exists(user.profile_photo):
        await client.send_file(
            event.chat_id,
            file=user.profile_photo,
            caption=profile_text,
            parse_mode='html',
            buttons=buttons
        )
    else:
        await event.respond(profile_text, parse_mode='html', buttons=buttons)


############################################### 
###############################################
#کلاینت دیلیت اکانت         

@client.on(events.CallbackQuery(pattern="confirm_delete_account"))
async def confirm_delete_account(event):
    await event.edit(
        "⚠️ آیا مطمئنی که می‌خوای اکانتت رو حذف کنی؟ این کار غیرقابل بازگشته.",
        buttons=[
            [Button.inline("✅ بله، حذف کن", data="delete_my_account")],
            [Button.inline("❌ نه، منصرف شدم", data="back_to_menu")]
        ]
    )


@client.on(events.CallbackQuery(pattern="delete_my_account"))
async def delete_my_account(event):
    user_id = event.sender_id

    try:

        if 'message_repository' in globals():
            message_repository.delete_all_by_user(user_id)

        # پاک کردن روابط لایک، بلاک یا چت در صورت وجود
        if hasattr(user_repository, 'delete_relations'):
            user_repository.delete_relations(user_id)

        # حذف نهایی یوزر
        success = user_repository.delete_user(user_id)

        if success:
            await event.edit("✅ اکانت شما با موفقیت از ربات حذف شد.\nبرای استفاده مجدد، دوباره /start را ارسال کنید.")
        else:
            await event.edit("❌ اکانتی برای حذف پیدا نشد یا قبلاً حذف شده بود.")
    except Exception as e:
        await event.respond(f"❌ مشکلی در حذف اکانت شما پیش آمد:\n`{str(e)}`", parse_mode='md')





############################################### 
###############################################
###############################################
                        

def get_online_status(user_id: int) -> str:
    session = session_factory()
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        session.close()
        return "وضعیت آنلاین نامشخص است."

    now = datetime.utcnow()
    if not hasattr(user, 'last_seen') or user.last_seen is None:
        session.close()
        return "وضعیت آنلاین نامشخص است."

    diff = now - user.last_seen

    if diff < timedelta(minutes=5):
        active_chat = session.query(ActiveChat).filter(
            (ActiveChat.user1_id == user_id) | (ActiveChat.user2_id == user_id)
        ).first()
        session.close()
        if active_chat:
            return "🟢 آنلاین است و در حال چت است"
        else:
            return "🟢 آنلاین است"

    # تابع کمکی برای تبدیل اختلاف به رشته فارسی
    def format_time_difference(diff):
        seconds = int(diff.total_seconds())
        intervals = (
            ('سال', 31536000),   # 365*24*60*60
            ('ماه', 2592000),    # 30*24*60*60
            ('روز', 86400),      # 24*60*60
            ('ساعت', 3600),      # 60*60
            ('دقیقه', 60),
            ('ثانیه', 1),
        )

        result = []
        for name, count in intervals:
            value = seconds // count
            if value > 0:
                seconds -= value * count
                result.append(f"{value} {name}")
            if len(result) == 2:  
                break

        return ' و '.join(result)

    elapsed = format_time_difference(diff)
    session.close()

    if elapsed:
        return f"🕒 آخرین بازدید: {elapsed} پیش"
    else:
        return "🕒 چند لحظه پیش آنلاین بود"


###############################################
###############################################
###############################################
#کلاینت پروفایل کاربر و نمایش ان 

@client.on(events.NewMessage(pattern=r'/user_(\d{4})'))
async def show_user_by_id(event):
    code = event.pattern_match.group(1)
    sender_id = event.sender_id

    users = user_repository.get_all_users()
    target_user = next((u for u in users if str(u.id).endswith(code)), None)

    if not target_user:
        await event.respond("❌ چنین کاربری پیدا نشد.")
        return

    full_name = f"{target_user.first_name} {target_user.last_name or ''}".strip()

    # گرفتن وضعیت آنلاین و چت
    online_status = get_online_status(target_user.id)

    profile_text = f"""
<b>❖👤 پروفایل کاربر :</b>

⫸ 👤 <b>نام:</b> {full_name}
⫸ 🚻 <b>جنسیت:</b> {target_user.gender}
⫸ 📍 <b>استان:</b> {target_user.province}   
⫸ 🏙️ <b>شهر:</b> {target_user.city}  
⫸ 🎂 <b>سن:</b> {target_user.age}  
⫸ ❤️ <b>تعداد لایک‌ها:</b> {target_user.likes_count or 0} 
 
⫸ 📝 <b>بیو:</b> {target_user.bio or "ندارد"}  
 
╏🆔 <b>آیدی:</b> /user_{str(target_user.id)[-4:]} 

╏🔎 <b>وضعیت:</b> {online_status}
""".strip()


    # 🎯 دکمه‌ها
    buttons = []

    if target_user.id != sender_id:
        already_liked = user_repository.has_liked(sender_id, target_user.id)
        buttons.append([
            Button.inline(
                "❤️ لایک کن" if not already_liked else "✅ لایک شده",
                data=f"like_{target_user.id}"
            )
        ])
        buttons.append([
            Button.inline("💬 درخواست چت", data=f"chat_req_{target_user.id}"),
            Button.inline("📨 پیام دایرکت", data=f"direct_{target_user.id}")
        ])

        session = session_factory()
        blocked = is_blocked(session, event.sender_id, target_user.id)
        session.close()

        if blocked:
            block_button = Button.inline("🔓 آن‌بلاک کاربر", data=f"unblock_{target_user.id}")
        else:
            block_button = Button.inline("🚫 بلاک کاربر", data=f"block_{target_user.id}")

        # دکمه گزارش کاربر
        report_button = Button.inline("🚨 گزارش کاربر", data=f"report_{target_user.id}")

        buttons.append([block_button, report_button])


    # ارسال پروفایل
    if target_user.profile_photo and os.path.exists(target_user.profile_photo):
        await client.send_file(
            event.chat_id,
            file=target_user.profile_photo,
            caption=profile_text,
            parse_mode='html',
            buttons=buttons if buttons else None
        )
    else:
        await event.respond(profile_text, parse_mode='html', buttons=buttons if buttons else None)

#.....................................................................................................
#.....................................................................................................
#.....................................................................................................
#.....................................................................................................


user_report_states = {} 
report_counts = {}       
report_cooldowns = {}   

ADMINS = [7714158942]  # آیدی عددی ادمین‌ها این  آیدی پیش فرضه

# لیست دلایل گزارش
REPORT_REASONS = [
    "ارسال پیام‌های توهین‌آمیز / فحاشی",
    "ارسال پیام‌های نامناسب جنسی یا مستهجن",
    "ارسال اسپم / پیام‌های تکراری و آزاردهنده",
    "تهدید به خشونت / آسیب زدن به خود یا دیگران",
    "ارسال اطلاعات شخصی دیگران بدون اجازه",
    "ارسال لینک‌های مشکوک یا فیشینگ",
    "استفاده از نام یا هویت جعلی برای فریب",
    "درخواست اطلاعات شخصی (شماره، آدرس، عکس و...)",
    "ارسال محتوای تبلیغاتی بدون اجازه"
]




# شروع گزارش و کلاینت گزارش 
@client.on(events.CallbackQuery(pattern=r"report_(\d+)"))
async def handle_report_callback(event):
    reported_id = int(event.pattern_match.group(1))
    reporter_id = event.sender_id

    if reported_id == reporter_id:
        await event.answer("⛔️ نمی‌توانید خودتان را گزارش دهید!", alert=True)
        return

    cooldown_key = f"{reporter_id}:{reported_id}"
    if cooldown_key in report_cooldowns and report_cooldowns[cooldown_key] > time.time():
        await event.answer("⏳ شما قبلاً این کاربر را گزارش داده‌اید. لطفاً مدتی صبر کنید.", alert=True)
        return

    user_report_states[reporter_id] = reported_id

    buttons = [[Button.inline(f"{i+1}. {reason}", data=f"report_reason_{i}")] for i, reason in enumerate(REPORT_REASONS)]
    await event.respond("📋 لطفاً دلیل گزارش این کاربر را انتخاب کنید:", buttons=buttons)

# دریافت دلیل و ارسال به ادمین
@client.on(events.CallbackQuery(pattern=r"report_reason_(\d+)"))
async def handle_report_reason(event):
    reason_index = int(event.pattern_match.group(1))
    reporter_id = event.sender_id

    if reporter_id not in user_report_states:
        await event.answer("⛔️ این درخواست منقضی شده است.", alert=True)
        return

    reported_id = user_report_states.pop(reporter_id)
    reason_text = REPORT_REASONS[reason_index]

    cooldown_key = f"{reporter_id}:{reported_id}"
    report_cooldowns[cooldown_key] = time.time() + 2 * 86400  # 2 روز

    report_counts[reported_id] = report_counts.get(reported_id, 0) + 1
    count = report_counts[reported_id]

    text = f"""
🚨 <b>گزارش جدید</b>

👤 گزارش‌دهنده: /user_{str(reporter_id)[-4:]} ({reporter_id})
📌 گزارش‌شده: /user_{str(reported_id)[-4:]} ({reported_id})
📝 دلیل: <b>{reason_text}</b>
📊 تعداد گزارش‌ها: <b>{count}</b>
"""

    admin_buttons = [[Button.inline("👁 مشاهده پروفایل", data=f"admin_view_{reported_id}")]]
    if count == 1:
        admin_buttons.append([Button.inline("📩 ارسال اخطار", data=f"warn_{reported_id}")])
    elif count == 2:
        admin_buttons.append([Button.inline("🚫 مسدود 3 روزه", data=f"ban_{reported_id}_3")])
    elif count == 3:
        admin_buttons.append([Button.inline("🚫 مسدود 5 روزه", data=f"ban_{reported_id}_5")])
    elif count == 4:
        admin_buttons.append([Button.inline("🚫 مسدود 2 ماهه", data=f"ban_{reported_id}_60")])
    elif count == 5:
        admin_buttons.append([Button.inline("⚠️ اخطار حذف اکانت", data=f"warn_delete_{reported_id}")])
    elif count >= 6:
        admin_buttons.append([Button.inline("❌ حذف اکانت", data=f"delete_account_{reported_id}")])

    for admin_id in ADMINS:
        await client.send_message(admin_id, text, parse_mode='html', buttons=admin_buttons)

    await event.respond("✅ گزارش شما ثبت شد و به ادمین ارسال شد.\nتا ۲ روز دیگر نمی‌توانید دوباره همین کاربر را گزارش دهید.")

# اکشن‌های ادمین
@client.on(events.CallbackQuery(pattern=r"warn_(\d+)"))
async def warn_user(event):
    user_id = int(event.pattern_match.group(1))
    try:
        await client.send_message(user_id, "⚠️ به دلیل گزارش کاربران، به شما اخطار داده شده است.")
    except: pass
    await event.answer("✅ اخطار ارسال شد.", alert=True)

@client.on(events.CallbackQuery(pattern=r"ban_(\d+)_(\d+)"))
async def ban_user(event):
    user_id, days = map(int, event.pattern_match.groups())
    banned_users[user_id] = time.time() + days * 86400
    try:
        await client.send_message(user_id, f"⛔️ به مدت {days} روز از ربات مسدود شدید.")
    except: pass
    await event.answer("✅ کاربر مسدود شد.", alert=True)

@client.on(events.CallbackQuery(pattern=r"warn_delete_(\d+)"))
async def warn_delete(event):
    user_id = int(event.pattern_match.group(1))
    try:
        await client.send_message(user_id, "⚠️ در صورت دریافت گزارش بعدی، اکانت شما حذف خواهد شد.")
    except: pass
    await event.answer("✅ اخطار حذف ارسال شد.", alert=True)

@client.on(events.CallbackQuery(pattern=r"delete_account_(\d+)"))
async def delete_account(event):
    user_id = int(event.pattern_match.group(1))
    user_repository.delete_user(user_id)  # حذف از دیتابیس
    try:
        await client.send_message(user_id, "❌ اکانت شما به دلیل گزارش‌های متعدد حذف شد.")
    except: pass
    await event.answer("✅ اکانت حذف شد.", alert=True)


@client.on(events.CallbackQuery(pattern=r"admin_view_(\d+)"))
async def admin_view(event):
    user_id = int(event.pattern_match.group(1))
    user = user_repository.get_user_with_id(user_id)
    if not user:
        await event.edit("❌ کاربر پیدا نشد.")
        return

    full_name = f"{user.first_name} {user.last_name or ''}".strip()

    text = f"""
👤 <b>پروفایل کاربر گزارش‌شده</b>

▪️ <b>نام:</b> {full_name}
▪️ <b>جنسیت:</b> {user.gender}
▪️ <b>سن:</b> {user.age}
▪️ <b>استان:</b> {user.province}
▪️ <b>شهر:</b> {user.city}
▪️ <b>آیدی عددی:</b> <code>{user.id}</code>
▪️ <b>لینک پروفایل:</b> /user_{str(user.id)[-4:]}
""".strip()

    if user.profile_photo and os.path.exists(user.profile_photo):
        await client.send_file(
            event.chat_id,
            file=user.profile_photo,
            caption=text,
            parse_mode='html'
        )
    else:
        await event.edit(text, parse_mode='html')




#.....................................................................................................
#.....................................................................................................
#.....................................................................................................
#.....................................................................................................                   
@client.on(events.CallbackQuery(pattern=r'chat_req_(\d+)'))
async def chat_request_handler(event):
    from_user = await event.get_sender()
    to_user_id = int(event.pattern_match.group(1))

    session = session_factory()

    # بررسی بلاک بودن
    blocked = session.query(UserBlock).filter_by(blocker_id=to_user_id, blocked_id=from_user.id).first()
    if blocked:
        await event.answer("❌ شما توسط این کاربر بلاک شده‌اید و نمی‌توانید درخواست چت ارسال کنید.", alert=True)
        session.close()
        return
    session.close()

 
    # بررسی اینکه کاربر مقابل در حال چت نیست
    active_chat = session.query(ActiveChat).filter(
        ((ActiveChat.user1_id == to_user_id) | (ActiveChat.user2_id == to_user_id))
    ).first()

    if active_chat:
        await event.answer(  # <-- اینجا
            "⚠️ کاربر مورد نظر در حال چت است. می‌توانید به صورت دایرکت پیام ارسال کنید.",
            alert=True
        )
        session.close()
        return

    # بررسی داشتن پروفایل
    sender_user = user_repository.get_user_with_id(from_user.id)
    if not sender_user or not all([sender_user.first_name, sender_user.province, sender_user.city, sender_user.age]):
        await event.respond(
            "⛔️ برای ارسال درخواست چت، ابتدا باید پروفایل کامل داشته باشید.\nروی دکمه زیر بزنید:",
            buttons=[[Button.inline("🆕 ایجاد پروفایل", data="start_profile")]]
        )
        session.close()
        return

    # ذخیره درخواست در دیتابیس
    chat_request = ChatRequest(from_user_id=from_user.id, to_user_id=to_user_id)
    session.add(chat_request)
    session.commit()
    session.close()

    await event.respond(f"📨 درخواست چت شما برای کاربر /user_{str(to_user_id)[-4:]} ارسال شد...\n"
                        "⏳ منتظر بمانید. اگر تا ۳ دقیقه تأیید نشد، درخواست شما لغو می‌شود.")

    # ارسال درخواست به کاربر مقابل
    await client.send_message(
        to_user_id,
        f"📩 کاربر /user_{str(from_user.id)[-4:]} درخواست چت با شما دارد.",
        buttons=[
            [
                Button.inline("✅ قبول", data=f"accept_chat_{from_user.id}"),
                Button.inline("❌ رد", data=f"decline_chat_{from_user.id}")
            ]
        ]
    )

    # تایمر 3 دقیقه‌ای برای لغو اتوماتیک اگر جواب نداد
    async def auto_cancel():
        await asyncio.sleep(180)
        session = session_factory()
        req = session.query(ChatRequest).filter_by(
            from_user_id=from_user.id, to_user_id=to_user_id, accepted=None
        ).first()
        if req:
            req.accepted = False
            session.commit()
            await client.send_message(from_user.id, "❌ درخواست چت شما لغو شد (عدم پاسخ).")
        session.close()

    asyncio.create_task(auto_cancel())




def create_active_chat(session, user_a_id, user_b_id):
    user1_id, user2_id = sorted([user_a_id, user_b_id])
    existing = session.query(ActiveChat).filter_by(user1_id=user1_id, user2_id=user2_id).first()
    if existing:
        return existing  

    new_chat = ActiveChat(user1_id=user1_id, user2_id=user2_id)
    session.add(new_chat)
    session.commit()
    return new_chat



# قبول کردن چت
def main_menu_buttons():
    return [
        [Button.text("🤔 راهنما", resize=True), Button.text("👤 پروفایل من", resize=True)],
        [Button.text("💬 درخواست چت جدید", resize=True)]
    ]

def active_chat_buttons():
    # این بوت کیبورد پایین پیامه برای دکمه پایان چت
    return [
        [Button.text("❌ پایان چت", resize=True)]
    ]

@client.on(events.CallbackQuery(pattern=r'accept_chat_(\d+)'))
async def accept_chat(event):
    from_user_id = int(event.pattern_match.group(1))
    to_user_id = event.sender_id

    session = session_factory()
    req = session.query(ChatRequest).filter_by(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        accepted=None
    ).first()

    if req:
        req.accepted = True
        session.commit()

        # ساخت چت فعال
        create_active_chat(session, from_user_id, to_user_id)

        # دکمه‌های پایان چت
        chat_buttons = [
            [Button.text("❌ پایان چت", resize=True)]
        ]


        await client.send_message(
            from_user_id,
            "✅ درخواست شما پذیرفته شد! اکنون می‌توانید چت را شروع کنید.\nبرای پایان دادن به چت از دکمه زیر استفاده کنید.",
            buttons=chat_buttons
        )

        await client.send_message(
            to_user_id,
            "✅ شما درخواست چت را پذیرفتید! اکنون می‌توانید چت را شروع کنید.\nبرای پایان دادن به چت از دکمه زیر استفاده کنید.",
            buttons=chat_buttons
        )


# رد کردن چت
@client.on(events.CallbackQuery(pattern=r'decline_chat_(\d+)'))
async def decline_chat(event):
    from_user_id = int(event.pattern_match.group(1))
    to_user_id = event.sender_id

    session = session_factory()
    req = session.query(ChatRequest).filter_by(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        accepted=None
    ).first()

    if req:
        req.accepted = False
        session.commit()
        await client.send_message(from_user_id, "❌ درخواست شما رد شد.")
        await event.respond("❌ شما درخواست چت را رد کردید.")

        

# هندل پیام ورودی

import logging

logger = logging.getLogger("chat_logger")
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

@client.on(events.CallbackQuery(pattern=r'accept_chat_(\d+)'))
async def accept_chat(event):
    from_user_id = int(event.pattern_match.group(1))  # درخواست دهنده
    to_user_id = event.sender_id  # کسی که قبول کرده

    session = session_factory()

    # مرتب کردن user1 و user2 برای جلوگیری از رکوردهای تکراری
    user1, user2 = sorted([from_user_id, to_user_id])

    # بررسی وجود چت فعال قبلی
    existing_chat = session.query(ActiveChat).filter_by(user1_id=user1, user2_id=user2).first()
    if existing_chat:
        logger.info(f"Chat between {user1} and {user2} already active.")
        await event.respond("✅ چت فعال است ")
        return

    req = session.query(ChatRequest).filter_by(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        accepted=None
    ).first()

    if not req:
        logger.warning(f"No pending chat request found from {from_user_id} to {to_user_id}.")
        await event.respond("❌ درخواست چت پیدا نشد یا قبلاً پاسخ داده شده است.")
        return

    req.accepted = True
    session.commit()

    # افزودن چت فعال جدید
    active_chat = ActiveChat(user1_id=user1, user2_id=user2)
    session.add(active_chat)
    session.commit()

    logger.info(f"Chat activated between {user1} and {user2}.")

    await client.send_message(
        from_user_id,
        "✅ درخواست شما پذیرفته شد! اکنون می‌توانید در بات با این کاربر چت کنید."
    )
    await event.respond("✅ شما درخواست چت را پذیرفتید. اکنون می‌توانید پیام دریافت کنید.")


@client.on(events.NewMessage(incoming=True))
async def handle_incoming(event):
    sender_id = event.sender_id
    session = session_factory()

    user = session.query(User).filter_by(id=event.sender_id).first()
    if user:
        user.last_seen = datetime.utcnow()
        session.commit()
    session.close()
    


    # ✅ جلوگیری از تداخل با حالت دایرکت
    if sender_id in direct_state:
        return

    blocked_texts = [
        "/", " 👤 پروفایل من", "🤔 راهنما", "💌 به مخاطب خاصم وصلم کن!",
        "📩 لینک ناشناس من ", "انصراف", "پروفایل" , "❌ پایان چت" , "مشاهده پروفایل👤"
    ]
    if event.text and any(event.text.startswith(t) for t in blocked_texts):
        return

    # پیدا کردن همه چت‌های فعال برای فرستنده
    active_chats = session.query(ActiveChat).filter(
        ((ActiveChat.user1_id == sender_id) | (ActiveChat.user2_id == sender_id))
    ).all()

    if not active_chats:
        logger.info(f"No active chat found for user {sender_id}. Message ignored.")
        return

    if len(active_chats) > 1:
        logger.warning(f"User {sender_id} has multiple active chats ({len(active_chats)}). Cannot decide recipient.")
        await event.respond("⚠️ شما بیش از یک چت فعال دارید. فعلاً نمی‌توانید پیام ارسال کنید.")
        return

    chat = active_chats[0]
    partner_id = chat.user2_id if chat.user1_id == sender_id else chat.user1_id

    logger.info(f"Forwarding message from {sender_id} to {partner_id}.")

    try:
        if event.media:
            await client.send_file(partner_id, file=event.media, caption=event.raw_text or None)
        else:
            await client.send_message(partner_id, event.raw_text)
        logger.info("Message sent successfully.")
    except Exception as e:
        logger.error(f"Error sending message from {sender_id} to {partner_id}: {e}")




# هندل کردن کلیک روی دکمه پایان چت (بوت کیبورد)
@client.on(events.NewMessage(pattern="❌ پایان چت"))
async def ask_end_chat_confirmation(event):
    await event.respond(
        "آیا مطمئنی که می‌خواهی چت را قطع کنی؟",
        buttons=[
            [Button.inline("✅ بله، قطعش کن", data="confirm_end_chat")],
            [Button.inline("🔙 نه، برگرد به چت", data="cancel_end_chat")]
        ]
    )


# تایید قطع چت
@client.on(events.CallbackQuery(pattern="confirm_end_chat"))
async def confirm_end_chat(event):
    user_id = event.sender_id
    session = session_factory()

    chat = session.query(ActiveChat).filter(
        (ActiveChat.user1_id == user_id) | (ActiveChat.user2_id == user_id)
    ).first()

    if not chat:
        await event.respond("❌ چت فعالی پیدا نشد.")
        return

    # پیدا کردن طرف مقابل
    partner_id = chat.user2_id if chat.user1_id == user_id else chat.user1_id

    # حذف چت
    session.delete(chat)
    session.commit()


    main_menu_buttons = [
        [Button.text("🔗 به یک ناشناس وصلم کن", resize=True)],  
        [Button.text("💌 به مخاطب خاصم وصلم کن!", resize=True), Button.text("📩 لینک ناشناس من ", resize=True)],
        [Button.text("🤔 راهنما", resize=True), Button.text("👤 پروفایل من", resize=True)],
        [Button.text("🗣 پشتیبان تلگرام", resize=True)],
        [Button.text("📢 لینک معرفی ربات", resize=True)],
    ]

    # پیام‌ها برای هر دو طرف
    await client.send_message(partner_id, "❌ طرف مقابل چت را قطع کرد. چت پایان یافت.", buttons=main_menu_buttons)
    await event.respond("✅ چت با موفقیت قطع شد. به منوی اصلی بازگشتی.", buttons=main_menu_buttons)


# لغو قطع چت
@client.on(events.CallbackQuery(pattern="cancel_end_chat"))
async def cancel_end_chat(event):
    await event.respond("🔙 چت ادامه دارد. می‌توانید پیام بفرستید.")


###########################################################################
###########################################################################
###########################################################################
    
# ✅ هندلر بلاک کردن کاربر
@client.on(events.CallbackQuery(pattern=r'^block_(\d+)$'))
async def block_user(event):
    target_id = int(event.pattern_match.group(1))
    user_id = event.sender_id
    session = session_factory()

    try:
        sender = session.query(User).filter_by(id=user_id).first()
        target = session.query(User).filter_by(id=target_id).first()

        if not target:
            await event.answer("❌ کاربر مورد نظر یافت نشد.", alert=True)
            return

        exists = session.query(UserBlock).filter_by(blocker_id=user_id, blocked_id=target_id).first()
        if exists:
            await event.answer("⚠️ شما قبلاً این کاربر را بلاک کرده‌اید.", alert=True)
            return

        session.add(UserBlock(blocker_id=user_id, blocked_id=target_id))
        session.commit()

        await event.answer("🚫 کاربر بلاک شد.", alert=True)  # پیام پنجره‌ای به بلاک کننده

        await client.send_message(user_id,
            "⛔️ کاربر مورد نظر بلاک شد و دیگر نمی‌تواند به شما پیام دایرکت یا درخواست چت ارسال کند.")

        await client.send_message(target_id,
            f"❌ کاربر /user_{str(sender.id)[-4:]} شما را بلاک کرده و دیگر نمی‌توانید به او پیام دایرکت یا درخواست چت ارسال کنید.",
            parse_mode="html")

        # تغییر دکمه‌ها به آنبلاک
        msg = await event.get_message()
        new_buttons = []
        for row in msg.buttons:
            new_row = []
            for btn in row:
                if btn.data and btn.data.decode().startswith("block_"):
                    new_row.append(Button.inline("🔓 آن‌بلاک کاربر", data=f"unblock_{target_id}"))
                else:
                    new_row.append(btn)
            new_buttons.append(new_row)

        await event.edit(buttons=new_buttons)

    except Exception as e:
        session.rollback()
        await event.answer("❌ خطا در بلاک کردن.", alert=True)
        print(e)
    finally:
        session.close()


# ✅ هندلر آنبلاک کردن کاربر
@client.on(events.CallbackQuery(pattern=r'^unblock_(\d+)$'))
async def unblock_user(event):
    target_id = int(event.pattern_match.group(1))
    user_id = event.sender_id
    session = session_factory()

    try:
        sender = session.query(User).filter_by(id=user_id).first()
        target = session.query(User).filter_by(id=target_id).first()

        if not target:
            await event.answer("❌ کاربر مورد نظر یافت نشد.", alert=True)
            return

        block = session.query(UserBlock).filter_by(blocker_id=user_id, blocked_id=target_id).first()
        if not block:
            await event.answer("⚠️ این کاربر بلاک نشده است.", alert=True)
            return

        session.delete(block)
        session.commit()

        await event.answer("✅ کاربر آنبلاک شد.", alert=True)  

        await client.send_message(user_id,
            "🔓 کاربر مورد نظر آنبلاک شد و اکنون می‌تواند به شما پیام دهد.")

        await client.send_message(target_id,
            f"✅ کاربر /user_{str(sender.id)[-4:]} شما را آنبلاک کرده است.",
            parse_mode="html")

        # تغییر دکمه‌ها به بلاک
        msg = await event.get_message()
        new_buttons = []
        for row in msg.buttons:
            new_row = []
            for btn in row:
                if btn.data and btn.data.decode().startswith("unblock_"):
                    new_row.append(Button.inline("🚫 بلاک کاربر", data=f"block_{target_id}"))
                else:
                    new_row.append(btn)
            new_buttons.append(new_row)

        await event.edit(buttons=new_buttons)

    except Exception as e:
        session.rollback()
        await event.answer("❌ خطا در آنبلاک کردن.", alert=True)
        print(e)
    finally:
        session.close()


###########################################################################
###########################################################################
###########################################################################
#کلاینت کامل دایرکت
direct_state = {}

@client.on(events.CallbackQuery(pattern=r"direct_(\d+)"))
async def start_direct(event):
    sender_id = event.sender_id
    target_id = int(event.pattern_match.group(1))

    session = session_factory()

    # بررسی بلاک بودن: آیا کاربر مقابل sender_id رو بلاک کرده؟
    blocked = session.query(UserBlock).filter_by(blocker_id=target_id, blocked_id=sender_id).first()
    if blocked:
        await event.answer("❌ شما توسط این کاربر بلاک شده‌اید و نمی‌توانید پیام دایرکت ارسال کنید.", alert=True)
        session.close()
        return

    # گرفتن اطلاعات کامل فرستنده
    user = session.query(User).filter_by(id=sender_id).first()
    if not user:
        await event.respond("❌ برای ارسال پیام دایرکت باید ابتدا پروفایل بسازید.")
        session.close()
        return

    # چک کامل بودن پروفایل (مقادیر نباید None یا رشته خالی باشند)
    required_attrs = ['gender', 'province', 'city', 'age', 'bio']
    if any(not getattr(user, attr, None) or str(getattr(user, attr)).strip() == "" for attr in required_attrs):
        await event.respond("❌ برای ارسال پیام دایرکت باید ابتدا پروفایل خود را کامل کنید.")
        session.close()
        return

    # بررسی اینکه آیا target_id در چت فعالی هست یا نه (در صورت نیاز)
    active_chat = session.query(ActiveChat).filter(
        (ActiveChat.user1_id == target_id) | (ActiveChat.user2_id == target_id)
    ).first()

    session.close()

    # آماده‌سازی حالت دایرکت برای ارسال پیام
    direct_state[sender_id] = {
        "stage": "waiting_message",
        "target_id": target_id,
        "message_text": None,
        "media": None,
        "media_type": None,
        "reply_to_id": None
    }

    await event.respond("📝 لطفاً پیام دایرکت خود را وارد کنید (متن یا مدیا):")



@client.on(events.NewMessage)
async def handle_direct_message(event):
    sender_id = event.sender_id

    if sender_id not in direct_state:
        return

    state = direct_state[sender_id]
    stage = state["stage"]

    media = event.media
    text = event.raw_text.strip() if event.raw_text else None

    direct_state[sender_id]["message_text"] = text
    direct_state[sender_id]["media"] = media
    direct_state[sender_id]["media_type"] = type(media).__name__ if media else None
    direct_state[sender_id]["stage"] = "confirm_reply" if stage == "waiting_reply" else "confirm"

    msg = "✉️ پاسخ شما:\n\n" if stage == "waiting_reply" else "🔸 پیام شما:\n\n"
    msg += f"{text or '[مدیا]'}\n\nمی‌خوای ارسال بشه؟"

    buttons = [
        [Button.inline("✅ ارسال", data="send_reply" if stage == "waiting_reply" else "confirm_send")],
        [Button.inline("✏️ ویرایش", data="edit_reply" if stage == "waiting_reply" else "edit_direct")],
        [Button.inline("❌ لغو", data="cancel_reply" if stage == "waiting_reply" else "cancel_direct")]
    ]
    await event.respond(msg, buttons=buttons)


@client.on(events.CallbackQuery(pattern=r"reply:(\d+):(\d+)"))
async def reply_button_handler(event):
    sender_id = event.sender_id
    reply_target = int(event.pattern_match.group(1))
    reply_to_id = int(event.pattern_match.group(2))

    direct_state[sender_id] = {
        "stage": "waiting_reply",
        "target_id": reply_target,
        "message_text": None,
        "media": None,
        "media_type": None,
        "reply_to_id": reply_to_id
    }
    await event.respond("📝 لطفاً پاسخ خود را وارد کنید (متن یا مدیا):")


@client.on(events.CallbackQuery)
async def handle_direct_buttons(event):
    sender_id = event.sender_id
    data = event.data.decode()

 
    if data.startswith("reply:"):
        return

    if sender_id not in direct_state:
        return

    state = direct_state[sender_id]
    target_id = state["target_id"]
    text = state["message_text"]
    media = state["media"]
    media_type = state["media_type"]
    reply_to_id = state.get("reply_to_id")

    session = session_factory()
    sender_code = f"/user_{str(sender_id)[-4:]}"
    header = "📩 پاسخ دایرکت از" if data == "send_reply" else "📨 شما یک پیام دایرکت دریافت کردید از"
    caption = f"{header} {sender_code}:\n\n{text or ''}"

    if data in ["confirm_send", "send_reply"]:
        msg_record = DirectMessage(
            sender_id=sender_id,
            receiver_id=target_id,
            message_text=text,
            media_file=None,  
            media_type=media_type,
            is_reply=(data == "send_reply"),
            reply_to_id=reply_to_id
        )
        session.add(msg_record)
        session.commit()

        try:
            if media:
                await client.send_file(
                    target_id,
                    file=media,
                    caption=caption,
                    buttons=[Button.inline("📩 پاسخ دادن", data=f"reply:{sender_id}:{msg_record.id}")]
                )
            else:
                await client.send_message(
                    target_id,
                    caption,
                    buttons=[Button.inline("📩 پاسخ دادن", data=f"reply:{sender_id}:{msg_record.id}")]
                )
            await event.respond("✅ پیام ارسال شد.")
        except Exception as e:
            await event.respond(f"❌ ارسال پیام با خطا مواجه شد: {e}")

        session.close()
        del direct_state[sender_id]

    elif data in ["edit_direct", "edit_reply"]:
        direct_state[sender_id]["stage"] = "waiting_reply" if data == "edit_reply" else "waiting_message"
        await event.respond("✏️ لطفاً پیام جدید را وارد کنید:")

    elif data in ["cancel_direct", "cancel_reply"]:
        del direct_state[sender_id]
        await event.respond("❌ ارسال پیام لغو شد.")

########################################################################################
########################################################################################
########################################################################################

#کلاینت کامل ویرایش پروفایل 

edit_state = {}
province_list = list(IRAN_PROVINCES.keys())  # استان‌ها
city_map = {}  # نگهداری شهرهای مرتبط با هر کاربر

@client.on(events.CallbackQuery(pattern="edit_profile"))
async def edit_profile_handler(event):
    buttons = [
        [Button.inline("👤 تغییر نام", data="edit_name")],
        [Button.inline("🚻 تغییر جنسیت", data="edit_gender")],
        [Button.inline("🎂 تغییر سن", data="edit_age")],
        [Button.inline("📍 تغییر استان", data="edit_province")],
        [Button.inline("🏙️ تغییر شهر", data="edit_city")],
        [Button.inline("📝 تغییر بیو", data="edit_bio")],
        [Button.inline("🖼️ تغییر عکس پروفایل", data="edit_photo")]
    ]
    await event.respond("🛠 کدام بخش را می‌خواهید ویرایش کنید؟", buttons=buttons)

@client.on(events.CallbackQuery(pattern="edit_name"))
async def edit_name(event):
    edit_state[event.sender_id] = "name"
    await event.respond("📝 لطفاً نام جدید خود را وارد کنید:")

@client.on(events.CallbackQuery(pattern="edit_age"))
async def edit_age(event):
    user_id = event.sender_id
    edit_state[user_id] = "age_selecting"

    age_list = list(range(16, 100))  # لیست محدودتر برای تست
    buttons = []
    for i in range(0, len(age_list), 4):
        row = [Button.text(str(age)) for age in age_list[i:i + 4]]
        buttons.append(row)

    await event.respond("🎂 لطفاً سنت را انتخاب کن:", buttons=buttons)


@client.on(events.CallbackQuery(pattern=r"select_age_(\d+)"))
async def select_age(event):
    age = int(event.pattern_match.group(1))
    user_id = event.sender_id
    if edit_state.get(user_id) != "age_selecting":
        await event.respond("❌ لطفاً ابتدا دکمه تغییر سن را بزنید.")
        return
    session = session_factory()
    user = session.query(User).filter_by(id=user_id).first()
    if user:
        user.age = age
        session.commit()
        await event.respond(f"✅ سن شما به {age} سال تغییر یافت.")
    else:
        await event.respond("❌ خطا در یافتن پروفایل.")
    session.close()
    del edit_state[user_id]

@client.on(events.CallbackQuery(pattern="edit_province"))
async def edit_province(event):
    user_id = event.sender_id
    edit_state[user_id] = "province_selecting"

    province_list = list(IRAN_PROVINCES.keys())
    buttons = []
    for i in range(0, len(province_list), 2):
        row = [Button.text(p) for p in province_list[i:i + 2]]
        buttons.append(row)

    await event.respond("📍 لطفاً نام استان خود را انتخاب یا تایپ کنید:", buttons=buttons)


@client.on(events.CallbackQuery(pattern=r"select_province_(\d+)"))
async def select_province(event):
    user_id = event.sender_id
    idx = int(event.pattern_match.group(1))
    if idx < 0 or idx >= len(province_list):
        await event.respond("❌ استان انتخابی نامعتبر است.")
        return
    province = province_list[idx]
    session = session_factory()
    user = session.query(User).filter_by(id=user_id).first()
    if user:
        user.province = province
        session.commit()
        await event.respond(f"✅ استان شما به {province} تغییر یافت.")
    else:
        await event.respond("❌ خطا در یافتن پروفایل.")
    session.close()
    del edit_state[user_id]
    city_map[user_id] = IRAN_PROVINCES[province]  # ذخیره شهرهای استان

@client.on(events.CallbackQuery(pattern="edit_city"))
async def edit_city(event):
    user_id = event.sender_id

    session = session_factory()
    user = session.query(User).filter_by(id=user_id).first()
    session.close()

    if not user or not user.province or user.province not in IRAN_PROVINCES:
        await event.respond("❗️ ابتدا استان خود را انتخاب کنید.")
        return

    cities = IRAN_PROVINCES[user.province]
    city_map[user_id] = cities
    edit_state[user_id] = "city_selecting"

    buttons = []
    for i in range(0, len(cities), 2):
        row = [Button.text(c) for c in cities[i:i + 2]]
        buttons.append(row)

    await event.respond("🏙️ لطفاً نام شهرت را انتخاب یا تایپ کن:", buttons=buttons)


@client.on(events.CallbackQuery(pattern=r"select_city_(\d+)"))
async def select_city(event):
    user_id = event.sender_id
    idx = int(event.pattern_match.group(1))

    if edit_state.get(user_id) != "city_selecting":
        await event.respond("❌ ابتدا دکمه تغییر شهر را بزنید.")
        return

    cities = city_map.get(user_id)
    if not cities or idx >= len(cities):
        await event.respond("❌ شهر انتخابی نامعتبر است.")
        return

    city = cities[idx]
    session = session_factory()
    user = session.query(User).filter_by(id=user_id).first()
    if user:
        user.city = city
        session.commit()
        await event.respond(f"✅ شهر شما به {city} تغییر یافت.")
    else:
        await event.respond("❌ خطا در یافتن پروفایل.")
    session.close()
    del edit_state[user_id]

@client.on(events.CallbackQuery(pattern="edit_bio"))
async def edit_bio(event):
    edit_state[event.sender_id] = "bio"
    await event.respond("📝 لطفاً بیوی جدید خود را وارد کنید:")

@client.on(events.CallbackQuery(pattern="edit_photo"))
async def edit_photo_handler(event):
    edit_state[event.sender_id] = "awaiting_photo"
    await event.respond("📤 لطفاً عکس جدید خود را ارسال کنید:")

@client.on(events.NewMessage(incoming=True))
async def handle_edit_input(event):
    user_id = event.sender_id
    if user_id in direct_state:
        return
    if user_id not in edit_state or edit_state[user_id] == "awaiting_photo":
        return

    field = edit_state[user_id]
    text = event.raw_text.strip()

    session = session_factory()
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        await event.respond("❌ خطا در یافتن پروفایل.")
        session.close()
        return

    if field == "age_selecting":
        if not text.isdigit():
            await event.respond("❗ لطفاً سن را فقط به صورت عدد وارد کن.")
            return
        user.age = int(text)

    elif field == "name":
        user.first_name = text

    elif field == "bio":
        user.bio = text

    elif field == "province_selecting":
        if text not in IRAN_PROVINCES:
            await event.respond("❌ استان وارد شده معتبر نیست. لطفاً یکی از دکمه‌ها را انتخاب کنید یا نام استان را درست وارد کنید.")
            return
        user.province = text
        city_map[user_id] = IRAN_PROVINCES[text]

    elif field == "city_selecting":
        if not user.province or user.province not in IRAN_PROVINCES:
            await event.respond("❗ ابتدا استان خود را انتخاب کنید.")
            return
        if text not in IRAN_PROVINCES[user.province]:
            await event.respond("❌ شهر وارد شده مربوط به استان انتخابی شما نیست.")
            return
        user.city = text

    session.commit()
    session.close()
    del edit_state[user_id]

    # ارسال پیام موفقیت و بازگشت به منوی اصلی
    await reset_btns(event, "✅ تغییرات با موفقیت ذخیره شد.")



@client.on(events.NewMessage(incoming=True))
async def handle_photo_upload(event):
    user_id = event.sender_id
    if edit_state.get(user_id) != "awaiting_photo":
        return
    if not event.photo:
        await event.respond("❌ لطفاً یک عکس ارسال کنید.")
        return
    filename = f"media/photo_{user_id}_{uuid.uuid4().hex}.jpg"
    await event.download_media(file=filename)
    session = session_factory()
    user = session.query(User).filter_by(id=user_id).first()
    if user.profile_photo and os.path.exists(user.profile_photo):
        try: os.remove(user.profile_photo)
        except Exception as e: print(f"Error deleting old photo: {e}")
    user.profile_photo = filename
    session.commit()
    session.close()
    del edit_state[user_id]
    await event.respond("✅ عکس پروفایل شما بروزرسانی شد.")

##
    
@client.on(events.CallbackQuery(pattern="edit_gender"))
async def edit_gender(event):
    edit_state[event.sender_id] = "gender_selecting"
    buttons = [
        [Button.inline("👦 پسر", data="change_gender_boy")],
        [Button.inline("👧 دختر", data="change_gender_girl")]
    ]
    await event.respond("🚻 لطفاً جنسیت خود را انتخاب کنید:", buttons=buttons)

@client.on(events.CallbackQuery(pattern=r"change_gender_"))
async def handle_gender_change(event):
    user_id = event.sender_id

    if edit_state.get(user_id) != "gender_selecting":
        await event.respond("❌ ابتدا دکمه تغییر جنسیت را بزنید.")
        return

    # استخراج دقیق gender
    data = event.data.decode()
    gender_code = data.replace("change_gender_", "")
    gender = "پسر" if gender_code == "boy" else "دختر"

    session = session_factory()
    user = session.query(User).filter_by(id=user_id).first()

    if not user:
        await event.respond("❌ خطا در یافتن پروفایل.")
        session.close()
        return

    user.gender = gender
    session.commit()
    session.close()
    del edit_state[user_id]

    await event.respond(f"✅ جنسیت شما به {gender} تغییر یافت.")



########################################################################################
########################################################################################
########################################################################################


# @client.on(events.NewMessage())
# async def bad_command(event):
#     user: telethon.tl.types.User = event.chat
#     UserRepository().insert(User(user_id=user.id, access_hash=user.access_hash, first_name=user.first_name, last_name=user.last_name, username=user.username, status=User.STATUS.ACTIVE))
#     if event.message.message not in COMMANDS.command_list() and not str(event.message.message).startswith(COMMANDS.START):
#         await reset_btns(event, MESSAGES.AFTER_BAD_COMMAND)




@client.on(events.NewMessage(pattern=COMMANDS.START))
async def start(event):
    user = await event.get_sender()
    channel_username = 'zero0channel'  # ای دی کانال بدون @

    try:
        
        participant = await client(GetParticipantRequest(
            channel=channel_username,
            participant=user.id
        ))
    except UserNotParticipantError:
        await event.respond(
            "🚫 *دسترسی محدود* 🚫\n\n"
            "برای استفاده از ربات، ابتدا باید عضو کانال زیر شوید:",
            buttons=[
                [Button.url("📢 عضویت در کانال", f"https://t.me/{channel_username}")],
                [Button.inline("✅ عضویت انجام شد، ادامه بده", data="check_join")]
            ],
            parse_mode='md'
        )
        return
    except Exception as e:
        await event.respond(f"❗️ خطایی رخ داد:\n`{str(e)}`", parse_mode='md')
        return

    # اگر عضو بود ادامه‌ی پردازش...
    UserRepository().insert(User(
        user_id=user.id,
        access_hash=user.access_hash,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        status=User.STATUS.ACTIVE
    ))

    if len(event.message.message.split()) >= 2:
        target_user_id = event.message.message.split()[1]
        ref_user = UserRepository().get_user_with_id(target_user_id)
        await do_connection(event, ref_user)
    else:
        await reset_btns(event, MESSAGES.AFTER_START_COMMAND)

#######################################################################################
#کلاینت چک کردن عضویت
@client.on(events.CallbackQuery(data=b"check_join"))
async def handle_check_join(event: CallbackQuery.Event):
    user = await event.get_sender()
    channel_username = 'zero0channel'  # ای دی کانال بدون @

    try:
        await client(GetParticipantRequest(
            channel=channel_username,
            participant=user.id
        ))
        # ✅ کاربر عضو شده
        await event.edit("✅ شما با موفقیت عضو شدید!\n\nبرای شروع می‌تونید دوباره روی /start بزنید.")
    except UserNotParticipantError:
        # ❌ هنوز عضو نشده
        await event.answer("⛔️ هنوز عضو کانال نیستید!", alert=True)
    except Exception as e:
        await event.answer(f"⚠️ خطا: {str(e)}", alert=True)



###############################################################################################



@client.on(events.NewMessage(pattern=COMMANDS.CONNECT))
async def do_connection(event, the_user=None):
    async def loop_to_get_target(conv) -> Union[User, None]:
        while True:
            response = await conv.get_response(timeout=600)
            if response.message == COMMANDS.CANCEL_CONNECT:
                raise CanceledError()
            if response.message.startswith('@'):
                username = re.findall('^@[^\s]+', response.message)[0]
                target_user = await client.get_entity(username)
                target_user_id = target_user.id
            else:
                if not hasattr(response, "forward") or response.forward is None:
                    await conv.send_message(MESSAGES.RETRY_CONNECT)
                    continue
                target_user_id = response.forward.chat_id
                if target_user_id is None:
                    await conv.send_message(MESSAGES.RETRY_CONNECT)
                    continue
            user = UserRepository().get_user_with_id(target_user_id)
            return user

    info_log.log(level=TELEGRAM_LOG_LEVEL, msg=f'{event.chat.first_name} clicked {COMMANDS.CONNECT}')
    async with client.conversation(event.chat, timeout=600, total_timeout=600) as conv:
        await conv.send_message(
            MESSAGES.AFTER_CONNECT_COMMAND,
            buttons=[Button.text(COMMANDS.CANCEL_CONNECT, resize=True, single_use=True)]
        )

        try:
            if the_user is None:
                the_user: Union[User, None] = await loop_to_get_target(conv)
            if the_user is None:
                await reset_btns(event, MESSAGES.USER_NOT_FOUND)
                return

            await conv.send_message(TEMPLATES_MESSAGES.READY_TO_SEND_MESSAGE(the_user.first_name))
            response = await conv.get_response(timeout=600)
            if response.message == COMMANDS.CANCEL_CONNECT:
                raise CanceledError()

            # پردازش پیام (متنی یا رسانه‌ای)
            message_text = response.message if response.message else None
            file_path = None
            media_type = None

            if response.media:
                file_path = await response.download_media(file=os.path.join(MEDIA_FOLDER, f"{response.id}"))
                media_type = response.media.__class__.__name__

            # ساخت پیام برای ذخیره‌سازی
            new_message = Message(
                from_user_id=event.chat.id,
                to_user_id=the_user.id,
                message=message_text,
                msg_id=response.id,
                media_path=file_path,
                media_type=media_type
            )
            MessageRepository().insert(new_message)


            try:
                target_entity = await client.get_entity(
                    telethon.tl.types.InputPeerUser(user_id=the_user.id, access_hash=int(the_user.access_hash))
                )

               
                await client.send_message(
                    target_entity,
                    "📬 شما یک پیام ناشناس جدید دارید !\n\nجهت دریافت کلیک کنید 👈 /newmsg"
                )

                await reset_btns(event, MESSAGES.SEND_SUCCESSFULLY)
                new_message.status = Message.STATUS.SENT
                MessageRepository().commit()
                return

            except Exception as e:
                new_message.status = Message.STATUS.FAILED
                error_logger.error(f"send_anonymous_message_error {type(e)}-{e}-{event.chat}")
                MessageRepository().commit()
                print('SENDING ERROR:', type(e), e)
                await reset_btns(event, MESSAGES.YOUR_TARGET_STOPPED_THE_BOT)
                return

        except CanceledError:
            return
        except Exception as e:
            error_logger.error(f"do_connection_error {type(e)}-{e}")
            await reset_btns(event, MESSAGES.USER_NOT_FOUND)
            return



@client.on(events.NewMessage(pattern=COMMANDS.GET_UNSEEN_MESSAGES))
async def get_new_messages(event):
    user_id = event.chat.id
    message_list: List[Message] = list(MessageRepository().all_unseen_messages(user_id))

    if not message_list:
        await reset_btns(event, MESSAGES.NO_ANY_MESSAGES)
        return

    for message_orm in message_list:
        sender_user = UserRepository().get_user_with_id(message_orm.from_user_id)
        try:
            if message_orm.media_path:
                # ارسال فایل به کاربر
                message_from_bot = await event.respond(
                    file=message_orm.media_path,
                    buttons=[
                        [Button.inline(MESSAGES.BTN_BLOCK, data=1),
                        Button.inline(MESSAGES.BTN_ANSWER, data=TEMPLATES_MESSAGES.RESPOND_TO_MESSAGE(message_orm.id))]
                    ]
                )
            else:
                
                if message_orm.media_path and os.path.exists(message_orm.media_path):
                    try:
                        await event.respond(file=message_orm.media_path)
                    except Exception as e:
                        error_logger.error(f"Cannot send media file: {e}")

  
                message_text = message_orm.message or ""
                if len(message_text.strip()) < 3 and not message_orm.media_path:
                    message_text = "پیام خالی است."

                message_from_bot = await event.respond(message_text, buttons=[
                    [Button.inline(MESSAGES.BTN_BLOCK, data=1),
                    Button.inline(MESSAGES.BTN_ANSWER, data=TEMPLATES_MESSAGES.RESPOND_TO_MESSAGE(message_orm.id))]
                ])


            message_orm.msg_from_bot_id = message_from_bot.id
            message_orm.status = Message.STATUS.SEEN
            MessageRepository().commit()

            # اطلاع به فرستنده پیام
            sender_entity = await client.get_entity(
                telethon.tl.types.InputPeerUser(user_id=sender_user.id, access_hash=int(sender_user.access_hash))
            )
            await client.send_message(entity=sender_entity, message=MESSAGES.YOUR_MSG_WAS_READ, reply_to=message_orm.msg_id)

        except Exception as e:
            error_logger.error(f"read_message_error {type(e)}-{e}")




@client.on(events.CallbackQuery())
async def handel_callback(event):
    body = event.data.decode('utf8')
    info_log.log(level=TELEGRAM_LOG_LEVEL, msg=f'{event.sender_id} clicked a callback btn - btn_body={body}')
    if body.startswith(TEMPLATES_MESSAGES.RESPOND_LIKE):
        message_orm_id = int(body.split('_')[-1])
        sender_message_orm = MessageRepository().get_with_message_id(message_orm_id)

        info_log.log(level=TELEGRAM_LOG_LEVEL, msg=f'DEBUG-{sender_message_orm}')

        async with client.conversation(event.chat, timeout=600, total_timeout=600) as conv:
            await conv.send_message(MESSAGES.WAITING_TO_ANSWER, buttons=[Button.text(COMMANDS.CANCEL_CONNECT, resize=True, single_use=True)], reply_to=sender_message_orm.msg_from_bot_id)
            response = await conv.get_response()
            if response.message == COMMANDS.CANCEL_CONNECT:
                return

            message_text = response.message if response.message else ""
            media_path = None
            media_type = None

            # اگر رسانه‌ای هست، ذخیره کن
            if response.media:
                file_path = await response.download_media(file=MEDIA_FOLDER)
                media_path = file_path
                media_type = response.media.__class__.__name__  # مثلاً MessageMediaDocument یا MessageMediaPhoto

            # ذخیره در دیتابیس
            new_message = Message(
                from_user_id=sender_message_orm.to_user_id,
                to_user_id=sender_message_orm.from_user_id,
                message=message_text,
                msg_id=response.id,
                media_path=media_path,
                media_type=media_type,
            )
            MessageRepository().insert(new_message)

            try:
                # فقط اعلان بفرست
                the_user = UserRepository().get_user_with_id(new_message.to_user_id)
                target_entity = await client.get_entity(
                    telethon.tl.types.InputPeerUser(user_id=the_user.id, access_hash=int(the_user.access_hash))
                )

                await client.send_message(
                    target_entity,
                    "📬 شما یک پیام ناشناس جدید دارید !\n\nجهت دریافت کلیک کنید 👈 /newmsg"
                )

                await reset_btns(event, MESSAGES.SEND_SUCCESSFULLY)
                new_message.status = Message.STATUS.SENT
                MessageRepository().commit()
                return

            except Exception as e:
                new_message.status = Message.STATUS.FAILED
                error_logger.error(f"{type(e)}-{e}-{event.chat}")
                MessageRepository().commit()
                await reset_btns(event, MESSAGES.YOUR_TARGET_STOPPED_THE_BOT)
                return



@client.on(events.NewMessage(func=lambda e: e.sender_id in user_profile_state and 'awaiting_photo' == user_profile_state[e.sender_id].get('step') and e.photo))
async def handle_profile_photo(event):
    user_id = event.sender_id
    
    # دانلود عکس پروفایل و ذخیره مسیرش در دیکشنری وضعیت
    file_path = await event.download_media(file=f"media/profile_{user_id}.jpg")
    user_profile_state[user_id]['photo_path'] = file_path
    user_profile_state[user_id]['step'] = 'awaiting_name'
    
    await event.respond("✅ عکس ذخیره شد.\n\n✏️ حالا لطفاً نام خود را وارد کنید.")


@client.on(events.CallbackQuery(data=b"start_profile"))
async def start_profile_creation(event):
    user_id = event.sender_id
    user_profile_state[user_id] = {'step': 'awaiting_photo'}
    await event.edit("📸 لطفاً یک عکس برای پروفایل خود ارسال کنید.")



@client.on(events.NewMessage())
async def handle_profile_building(event):
    user_id = event.sender_id

    if user_id not in user_profile_state:
        return

    step = user_profile_state[user_id].get("step")

    # مرحله دریافت نام
    if step == 'awaiting_name':

        if not event.raw_text or event.media:
            return

        name = event.raw_text.strip()

        if len(name) < 2:
            await event.respond("❗️ نام وارد شده نامعتبر است. لطفاً نام کامل خود را وارد کنید.")
            return

        # ذخیره نام و رفتن به مرحله بعد
        user_profile_state[user_id]['name'] = name
        user_profile_state[user_id]['step'] = 'awaiting_gender'

        await event.respond(
            f"✅ نام شما ذخیره شد: {name}\n\n👫 حالا لطفاً جنسیت خود را انتخاب کنید:",
            buttons=[
                [Button.inline("👦 پسر", data="gender_boy"), Button.inline("👧 دختر", data="gender_girl")]
            ]
        )


@client.on(events.CallbackQuery(pattern=b"^gender_(boy|girl)$"))
async def handle_gender_selection(event):
    user_id = event.sender_id

    if user_id not in user_profile_state or user_profile_state[user_id].get("step") != "awaiting_gender":
        await event.answer("⛔️ مشکلی در وضعیت پروفایل شما وجود دارد.", alert=True)
        return

    gender_code = event.data.decode()
    gender = "پسر" if gender_code == "gender_boy" else "دختر"

    user_profile_state[user_id]['gender'] = gender
    user_profile_state[user_id]['step'] = 'awaiting_province'

    # ذخیره در دیتابیس
    session = session_factory()
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        user = User()
        user.id = user_id
        session.add(user)

    user.gender = gender
    session.commit()
    session.close()

    await event.respond(
        f"✅ جنسیت شما ثبت شد: {gender}\n\n📍 حالا استان خود را انتخاب کنید:",
        buttons=build_province_keyboard()
    )


def build_province_keyboard():
    buttons = []
    row = []
    for province in IRAN_PROVINCES.keys():
        row.append(Button.text(province))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return buttons


def build_city_keyboard(province_name):
    cities = IRAN_PROVINCES.get(province_name, [])
    buttons = []
    row = []
    for city in cities:
        row.append(Button.text(city))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return buttons


def build_age_keyboard():
    buttons = []
    row = []
    for age in range(16, 100):
        row.append(Button.text(str(age)))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return buttons

user_cache = {}

@client.on(events.NewMessage())
async def handle_profile_inputs(event):
    user_id = event.sender_id
    text = event.raw_text.strip()


    if user_id not in user_profile_state:
        return

    step = user_profile_state[user_id].get("step")

    # انتخاب استان
    if step == "awaiting_province":
        if text in IRAN_PROVINCES:
            user_cache[user_id] = {"province": text}
            user_profile_state[user_id]['step'] = 'awaiting_city'

            await event.respond(
                f"🏙️ استان {text} انتخاب شد.\n\nحالا شهر خود را انتخاب کنید:",
                buttons=build_city_keyboard(text)
            )
            return

    # انتخاب شهر
    elif user_profile_state[user_id].get("step") == "awaiting_city":
        province = user_cache[user_id]["province"]
        if text in IRAN_PROVINCES.get(province, []):
            user_cache[user_id]["city"] = text
            user_profile_state[user_id]['step'] = 'awaiting_age'

            await event.respond(
                f"📍 شهر شما: {text}\n\n🎂 حالا سنت رو انتخاب کن:",
                buttons=build_age_keyboard()
            )
            return

    # انتخاب سن
    elif user_profile_state[user_id].get("step") == "awaiting_age":
        if text.isdigit() and 16 <= int(text) <= 99:
            user_cache[user_id]["age"] = int(text)
            user_profile_state[user_id]['step'] = 'awaiting_bio'


            await event.respond("📝 لطفاً یک بیو برای پروفایل خود وارد کنید:")
            return
        

    # وارد کردن بیو
    elif user_profile_state[user_id].get("step") == "awaiting_bio":
        bio = text
        if len(bio) < 5:
            await event.respond("⚠️ بیو باید حداقل ۵ کاراکتر داشته باشه.")
            return

        user_cache[user_id]["bio"] = bio

        data = {**user_profile_state.get(user_id, {}), **user_cache.get(user_id, {})}

        user = user_repository.get_user_with_id(user_id)
        user.first_name = data.get("name")
        user.province = data.get("province")
        user.city = data.get("city")
        user.age = data.get("age")
        user.bio = data.get("bio")
        user.profile_photo = data.get("photo_path")

        user_repository.commit()

        del user_cache[user_id]
        del user_profile_state[user_id]

        await reset_btns(event, "✅ پروفایل شما با موفقیت ساخته شد!\nبرای دیدن پروفایل خود روی «پروفایل من» کلیک کنید.")


#کلاینت هندلر لایک 


@client.on(events.CallbackQuery(pattern=r'like_(\d+)'))
async def handle_like(event):
    from_user_id = event.sender_id
    to_user_id = int(event.pattern_match.group(1))

    session = session_factory()


    already_liked = session.query(Like).filter_by(
        liker_id=from_user_id,
        liked_id=to_user_id
    ).first()

    if already_liked:
        await event.answer("❗️شما قبلاً این کاربر را لایک کرده‌اید.", alert=True)
        return


    like = Like(liker_id=from_user_id, liked_id=to_user_id)
    session.add(like)


    user = session.query(User).filter_by(id=to_user_id).first()
    if user:
        user.likes_count = (user.likes_count or 0) + 1

    session.commit()

    await event.answer("✅ لایک ثبت شد!", alert=True)

#**********************************************************************************************************
#**********************************************************************************************************
#**********************************************************************************************************

MAIN_MENU_BUTTONS = [
    [Button.text("🔗 به یک ناشناس وصلم کن", resize=True)],  
    [Button.text("💌 به مخاطب خاصم وصلم کن!", resize=True), Button.text("📩 لینک ناشناس من ", resize=True)],
    [Button.text("🤔 راهنما", resize=True), Button.text("👤 پروفایل من", resize=True)],
    [Button.text("🗣 پشتیبان تلگرام", resize=True)],
    [Button.text("📢 لینک معرفی ربات", resize=True)],
]

#کلاینت "🔗 به یک ناشناس وصلم کن"
@client.on(events.NewMessage(pattern="🔗 به یک ناشناس وصلم کن"))
async def handle_connect_menu(event):
    buttons = [
        [Button.inline("🎲جستجوی شانسی🎲", data="random_search")],
        [Button.inline("🙍‍♀️ جستجوی دختر", data="girl_search"), Button.inline("🙎‍♂️ جستجوی پسر", data="boy_search")],
        [Button.inline("🔎جستجوی فیلتر شده🔍", data="filtered_search")],
        [Button.inline("🔙 بازگشت به منوی اصلی", data="back_to_main")]
    ]

    await event.respond("🔎 لطفاً نوع جستجو را انتخاب کنید:", buttons=buttons)


# کلاینت جستجوی فیلتر شده 
@client.on(events.CallbackQuery(pattern="filtered_search"))
async def handle_filtered_search_menu(event):
    buttons = [
        [Button.inline("🔍 جستجو براساس سن", data="search_by_age")],
        [Button.inline("🔍 جستجو براساس شهر", data="search_by_city")],
        [Button.inline("🔙 بازگشت به منوی اصلی", data="back_to_main")],
    ]
    await event.edit("📌 لطفاً یکی از گزینه‌های جستجو را انتخاب کنید:", buttons=buttons)


# بازگشت به منوی اصلی
@client.on(events.CallbackQuery(pattern="back_to_main"))
async def handle_back_to_main_menu(event):
    await event.edit("🏠 به منوی اصلی برگشتید.", buttons=MAIN_MENU_BUTTONS)

# هدایت به جستجو براساس سن
@client.on(events.CallbackQuery(pattern="search_by_age"))
async def handle_go_to_age_search(event):
    await event.delete()  
    await handle_search_by_age(event)  # فراخوانی تابع اصلی جستجوی سنی

# هدایت به جستجو براساس شهر
@client.on(events.CallbackQuery(pattern="search_by_city"))
async def handle_go_to_city_search(event):
    await event.delete()
    await handle_search_by_city(event)  # فراخوانی تابع اصلی جستجوی شهری


#**********************************************************************************************************
#**********************************************************************************************************
#**********************************************************************************************************
    
waiting_users = []
active_chats = {}
pending_tasks = {}
pending_confirmations = set()


MAIN_MENU_BUTTONS = [
    [Button.text("🔗 به یک ناشناس وصلم کن", resize=True)],  
    [Button.text("💌 به مخاطب خاصم وصلم کن!", resize=True), Button.text("📩 لینک ناشناس من ", resize=True)],
    [Button.text("🤔 راهنما", resize=True), Button.text("👤 پروفایل من", resize=True)],
    [Button.text("🗣 پشتیبان تلگرام", resize=True)],
    [Button.text("📢 لینک معرفی ربات", resize=True)],
]

# دکمه‌های پایان چت و مشاهده پروفایل کنار هم
CHAT_ACTIONS_BUTTONS = [
    [
        Button.text("❌ پایان چت", resize=True),
        Button.text("مشاهده پروفایل👤", resize=True)
    ]
]

CONFIRM_END_CHAT = [
    [Button.inline("✅ بله، قطعش کن", data="confirm_end_chat")],
    [Button.inline("🔙 نه، برگرد به چت", data="cancel_end_chat")]
]

#کد کلاینت جستجوی شانسی 

@client.on(events.CallbackQuery(pattern="random_search"))
async def handle_random_search(event):
    user_id = event.sender_id

    if user_id in waiting_users or user_id in active_chats:
        await event.answer("⛔️ در حال حاضر نمی‌تونی دوباره جستجو کنی.", alert=True)
        return

    if waiting_users:
        partner_id = waiting_users.pop(0)

        task = pending_tasks.pop(partner_id, None)
        if task:
            task.cancel()

        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        bot_id_user = f"user_{str(user_id)[-4:]}"
        bot_id_partner = f"user_{str(partner_id)[-4:]}"        

        await client.send_message(
            user_id,
            f"✅ به کاربر متصل شدید و می‌توانید شروع به چت کنید.\n\nبرای پایان دادن به چت یا مشاهده پروفایل، از دکمه‌های زیر استفاده کنید.",
            buttons=CHAT_ACTIONS_BUTTONS
        )

        await client.send_message(
            partner_id,
            f"✅ به کاربر متصل شدید و می‌توانید شروع به چت کنید.\n\nبرای پایان دادن به چت یا مشاهده پروفایل، از دکمه‌های زیر استفاده کنید.",
            buttons=CHAT_ACTIONS_BUTTONS
        )

    else:
        waiting_users.append(user_id)
        await event.respond("⏳ در صف انتظار برای اتصال به یک نفر دیگه هستی...\nاگر تا 2 دقیقه کسی پیدا نشه، جستجو لغو می‌شود.")
        task = asyncio.create_task(cancel_if_no_match(user_id))
        pending_tasks[user_id] = task

async def cancel_if_no_match(user_id):
    await asyncio.sleep(120)
    if user_id in waiting_users:
        waiting_users.remove(user_id)
        pending_tasks.pop(user_id, None)
        try:
            await client.send_message(user_id, "❌ تا ۲ دقیقه کسی پیدا نشد. جستجو لغو شد.")
        except:
            pass

@client.on(events.NewMessage(pattern="❌ پایان چت"))
async def ask_end_chat_confirmation(event):
    user_id = event.sender_id
    if user_id not in active_chats or user_id in pending_confirmations:
        return

    pending_confirmations.add(user_id)

@client.on(events.CallbackQuery(pattern="confirm_end_chat"))
async def confirm_end_chat(event):
    user_id = event.sender_id
    if user_id not in active_chats:
        await event.answer("چتی برای پایان دادن وجود ندارد.", alert=True)
        return

    partner_id = active_chats.pop(user_id, None)
    active_chats.pop(partner_id, None)
    pending_confirmations.discard(user_id)

    await client.send_message(user_id, "❌ شما چت را پایان دادید.", buttons=MAIN_MENU_BUTTONS)
    await client.send_message(partner_id, "❗️ طرف مقابل چت را قطع کرد.", buttons=MAIN_MENU_BUTTONS)

@client.on(events.CallbackQuery(pattern="cancel_end_chat"))
async def cancel_end_chat(event):
    user_id = event.sender_id
    pending_confirmations.discard(user_id)
    await event.edit("✅ به چت برگشتید.", buttons=CHAT_ACTIONS_BUTTONS)


# هندل پیام دکمه مشاهده پروفایل
@client.on(events.NewMessage(pattern="مشاهده پروفایل👤"))
async def show_partner_profile(event):
    sender_id = event.sender_id

    if sender_id not in active_chats:
        await event.respond("❌ شما در حال حاضر با کسی در حال چت نیستید.")
        return

    partner_id = active_chats[sender_id]
    target_user = user_repository.get_user_with_id(partner_id)

    if not target_user:
        await event.respond("❌ پروفایل کاربر مقابل یافت نشد.")
        return

    if not all([target_user.first_name, target_user.province, target_user.city, target_user.age]):
        await event.respond("❌ پروفایل کاربر مقابل کامل نیست.")
        return

    full_name = f"{target_user.first_name} {target_user.last_name or ''}".strip()
    online_status = get_online_status(partner_id)

    profile_text = f"""
<b>❖👤 پروفایل کاربر :</b>

⫸ 👤 <b>نام:</b> {full_name}
⫸ 🚻 <b>جنسیت:</b> {target_user.gender}
⫸ 📍 <b>استان:</b> {target_user.province}   
⫸ 🏙️ <b>شهر:</b> {target_user.city}  
⫸ 🎂 <b>سن:</b> {target_user.age}  
⫸ ❤️ <b>تعداد لایک‌ها:</b> {target_user.likes_count or 0} 
 
⫸ 📝 <b>بیو:</b> {target_user.bio or "ندارد"}  
 
╏🆔 <b>آیدی:</b> /user_{str(target_user.id)[-4:]} 

╏🔎 <b>وضعیت:</b> {online_status}
""".strip()

    # 🎯 دکمه‌ها
    buttons = []
    already_liked = user_repository.has_liked(sender_id, partner_id)
    buttons.append([
        Button.inline(
            "❤️ لایک کن" if not already_liked else "✅ لایک شده",
            data=f"like_{partner_id}"
        )
    ])
    buttons.append([
        Button.inline("💬 درخواست چت", data=f"chat_req_{partner_id}"),
        Button.inline("📨 پیام دایرکت", data=f"direct_{partner_id}")
    ])

    session = session_factory()
    blocked = is_blocked(session, sender_id, partner_id)
    session.close()

    if blocked:
        buttons.append([Button.inline("🔓 آن‌بلاک کاربر", data=f"unblock_{partner_id}")])
    else:
        buttons.append([Button.inline("🚫 بلاک کاربر", data=f"block_{partner_id}")])

    if target_user.profile_photo and os.path.exists(target_user.profile_photo):
        await client.send_file(
            event.chat_id,
            file=target_user.profile_photo,
            caption=profile_text,
            parse_mode='html',
            buttons=buttons
        )
    else:
        await event.respond(profile_text, parse_mode='html', buttons=buttons)


@client.on(events.NewMessage)
async def handle_chat_messages(event):
    user_id = event.sender_id

    if user_id not in active_chats:
        return

    partner_id = active_chats[user_id]

    control_texts = ["مشاهده پروفایل👤", "❌ پایان چت"]
    if event.raw_text in control_texts:
        return

    text = event.raw_text

    text_filtered = re.sub(r"/user_\d{1,10}", "[کاربر]", text)

    try:
        if event.message.media:
            caption = event.message.message or ""
         
            caption_filtered = re.sub(r"/user_\d{1,10}", "[کاربر]", caption)
            await client.send_file(partner_id, event.message, caption=caption_filtered)
        else:
            await client.send_message(partner_id, text_filtered)
    except Exception as e:
        await client.send_message(user_id, "⛔️ خطا در ارسال پیام به طرف مقابل.")



#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  
        
# کد کلاینت جستجو پسر و دختر 

waiting_users_by_target = {
    "دختر": [],
    "پسر": []
}

search_targets = {}  

@client.on(events.CallbackQuery(pattern="girl_search"))
async def handle_girl_search(event):
    await start_gender_based_search(event, target_gender="دختر")

@client.on(events.CallbackQuery(pattern="boy_search"))
async def handle_boy_search(event):
    await start_gender_based_search(event, target_gender="پسر")


async def start_gender_based_search(event, target_gender):
    user_id = event.sender_id
    user = user_repository.get_user_with_id(user_id)

    if not user:
        await event.answer("⛔️ ابتدا پروفایل خود را کامل کنید.", alert=True)
        return

    if user_id in active_chats:
        await event.answer("⛔️ شما هم‌اکنون در حال چت هستید.", alert=True)
        return

  
    if any(user_id in queue for queue in waiting_users_by_target.values()):
        await event.answer("⏳ شما در حال جستجو هستید.\nلطفاً تا پایان ۲ دقیقه صبر کنید.", alert=True)
        return

  
    for gender, queue in waiting_users_by_target.items():
        if user_id in queue:
            queue.remove(user_id)

    search_targets[user_id] = target_gender
    matched_id = None

    
    possible_partners = waiting_users_by_target[user.gender]

    for uid in possible_partners:
        their_target = search_targets.get(uid)
        if their_target == user.gender:
            matched_id = uid
            break

    if matched_id:
        possible_partners.remove(matched_id)
        search_targets.pop(matched_id, None)
        search_targets.pop(user_id, None)
        task = pending_tasks.pop(matched_id, None)
        if task:
            task.cancel()

        active_chats[user_id] = matched_id
        active_chats[matched_id] = user_id

        await client.send_message(user_id, "✅ به یک کاربر متصل شدید.", buttons=CHAT_ACTIONS_BUTTONS)
        await client.send_message(matched_id, "✅ به یک کاربر متصل شدید.", buttons=CHAT_ACTIONS_BUTTONS)
    else:
        waiting_users_by_target[target_gender].append(user_id)
        await event.respond(
            f"⏳ منتظر اتصال به یک {target_gender} هستی...\nاگر تا ۲ دقیقه کسی پیدا نشه، جستجو لغو می‌شود."
        )
        task = asyncio.create_task(cancel_if_no_match_target(user_id, target_gender))
        pending_tasks[user_id] = task


async def cancel_if_no_match_target(user_id, target_gender):
    await asyncio.sleep(120)
    if user_id in waiting_users_by_target[target_gender]:
        waiting_users_by_target[target_gender].remove(user_id)
        search_targets.pop(user_id, None)
        pending_tasks.pop(user_id, None)
        try:
            await client.send_message(user_id, "❌ تا ۲ دقیقه کسی پیدا نشد. جستجو لغو شد.")
        except:
            pass







###############################################00000000000000000000000000000000000000000000000000000000000
###############################################00000000000000000000000000000000000000000000000000000000000
###############################################00000000000000000000000000000000000000000000000000000000000

# کد کلاینت جستجو بر اساس سن


user_states = {}  
PAGE_SIZE = 5

@client.on(events.NewMessage(pattern="🔍 جستجو براساس سن"))
async def handle_search_by_age(event):
    user_id = event.sender_id
    user_states[user_id] = {"step": "select_age"}

    age_list = list(range(16, 100))
    buttons = []

    for i in range(0, len(age_list), 3):
        row = [
            Button.text(f"{age} سال")
            for age in age_list[i:i+3]
        ]
        buttons.append(row)

    await event.respond("🎂 لطفاً سنی که می‌خواهید براساس آن جستجو انجام شود را انتخاب کنید:", buttons=buttons)


@client.on(events.NewMessage)
async def handle_age_text_input(event):
    user_id = event.sender_id
    state = user_states.get(user_id)

    if not state or state.get("step") != "select_age":
        return

    text = event.raw_text.strip().replace(" سال", "")
    if not text.isdigit():
        return await event.respond("❗ لطفاً یکی از سن‌های پیشنهادی را از دکمه‌ها انتخاب کنید.")

    age = int(text)
    if age < 16 or age > 100:
        return await event.respond("❗ محدوده سن انتخابی نامعتبر است.")

    user_states[user_id] = {
        "step": "select_gender_for_age",
        "age": age,
        "page": 0
    }

    buttons = [[
        Button.inline("👧 دختر", data="age_gender_female"),
        Button.inline("👦 پسر", data="age_gender_male"),
        Button.inline("👥 باهم", data="age_gender_all")
    ]]
    await event.respond(f"✅ سن انتخاب شد: {age}\n\n🚻 حالا جنسیت مورد نظر را انتخاب کنید:", buttons=buttons)

@client.on(events.CallbackQuery(pattern=r"^age_gender_(female|male|all)$"))
async def handle_age_gender_selection(event):
    user_id = event.sender_id
    state = user_states.get(user_id)
    if not state or state.get("step") != "select_gender_for_age":
        return await event.answer("⛔️ مرحله معتبر نیست.", alert=True)

    selected = event.data.decode().split("_")[2]
    gender = None if selected == "all" else selected

    user_states[user_id].update({
        "gender": gender,
        "step": "show_age_results",
        "page": 0
    })

    await event.answer()
    await show_age_results(event, user_id, page=0)


async def show_age_results(event, user_id, page=0):
    state = user_states.get(user_id)
    if not state:
        return

    age = state["age"]
    gender = state.get("gender")
    offset = page * PAGE_SIZE
    recent_time = datetime.utcnow() - timedelta(days=3)

    session = session_factory()
    query = session.query(User).filter(
        User.age == age,
        User.last_online >= recent_time,
        User.status == User.STATUS.ACTIVE,
        User.id != user_id
    )

    if gender in ("male", "female"):
        gender_map = {
            "male": "پسر",
            "female": "دختر"
        }
        query = query.filter(User.gender == gender_map[gender])

    users = query.order_by(User.last_online.desc()).offset(offset).limit(PAGE_SIZE).all()
    session.close()

    if not users:
        await event.respond("❌ هیچ کاربری با این مشخصات پیدا نشد.", buttons=MAIN_MENU_BUTTONS)
        user_states[user_id] = {}
        return

    lines = [f"📍 افراد سن {age} که در ۳ روز اخیر آنلاین بوده‌اند:\n"]

    for user in users:
        bot_id = f"user_{str(user.id)[-4:]}"
        username_display = f"/{bot_id}"
        name = user.first_name or "❓"
        province = user.province or "نامشخص"
        city = user.city or "نامشخص"
        chat_status = " (درحال چت🗣)" if user.in_chat else ""
        online_status = get_online_status(user.id)  

        lines.append(
            f"{user.age} 🙍{name} {username_display} {province}({city})\n"
            f"{online_status}{chat_status}\n{'〰️'*8}"
        )

    lines.append(f"\n📅 جستجو شده در {datetime.now().strftime('%Y/%m/%d %H:%M')}")
    text = "\n".join(lines)

    buttons = []
    if page > 0:
        buttons.append(Button.inline("⏮ لیست قبلی", data="age_prev"))
    if len(users) == PAGE_SIZE:
        buttons.append(Button.inline("⏭ لیست بعدی", data="age_next"))
    buttons.append(Button.text("🔙 بازگشت به منوی اصلی"))

    await event.respond(text, buttons=[buttons])



@client.on(events.NewMessage(pattern="🔙 بازگشت به منوی اصلی"))
async def back_to_main_menu(event):
    user_id = event.sender_id
    user_states[user_id] = {}
    await event.respond("🏠 به منوی اصلی برگشتید.", buttons=MAIN_MENU_BUTTONS)


@client.on(events.CallbackQuery(pattern=r"^age_(next|prev)$"))
async def handle_age_pagination(event):
    user_id = event.sender_id
    state = user_states.get(user_id)
    if not state or state.get("step") != "show_age_results":
        return await event.answer("⛔️ مرحله نامعتبر", alert=True)

    if event.data == b"age_next":
        state["page"] += 1
    elif event.data == b"age_prev":
        state["page"] = max(0, state["page"] - 1)

    await show_age_results(event, user_id, page=state["page"])



###############################################00000000000000000000000000000000000000000000000000000000000
###############################################00000000000000000000000000000000000000000000000000000000000
###############################################00000000000000000000000000000000000000000000000000000000000

# ....کد بقیه کلاینت ها لایک و

@client.on(events.NewMessage(pattern=COMMANDS.LINK))
async def do_link(event):
    info_log.log(level=TELEGRAM_LOG_LEVEL, msg=f'{event.chat.first_name} clicked {COMMANDS.LINK}')
    user = UserRepository().get_user_with_id(event.chat.id)
    link = TEMPLATES_MESSAGES.YOUR_LINK(user.id)
    await reset_btns(event, TEMPLATES_MESSAGES.AFTER_GIVE_MY_LINK_COMMAND(user.first_name, link))
    await reset_btns(event, MESSAGES.AFTER_GIVE_MY_LINK_COMMAND_EXTRA)




@client.on(events.NewMessage(pattern=COMMANDS.GIVE_MY_LINK))
async def do_link(event):
    info_log.log(level=TELEGRAM_LOG_LEVEL, msg=f'{event.chat.first_name} clicked {COMMANDS.GIVE_MY_LINK}')
    user = UserRepository().get_user_with_id(event.chat.id)
    link = TEMPLATES_MESSAGES.YOUR_LINK(user.id)
    await reset_btns(event, TEMPLATES_MESSAGES.AFTER_GIVE_MY_LINK_COMMAND(user.first_name, link))
    await reset_btns(event, MESSAGES.AFTER_GIVE_MY_LINK_COMMAND_EXTRA)


@client.on(events.NewMessage(pattern=COMMANDS.INSTAGRAM))
async def do_link(event):
    info_log.log(level=TELEGRAM_LOG_LEVEL, msg=f'{event.chat.first_name} clicked {COMMANDS.INSTAGRAM}')
    user = UserRepository().get_user_with_id(event.chat.id)
    link = TEMPLATES_MESSAGES.YOUR_LINK(user.id)
    await reset_btns(event, MESSAGES.INSTAGRAM_DESCRIPTION)
    await reset_btns(event, link)


@client.on(events.NewMessage(pattern=COMMANDS.CANCEL_CONNECT))
async def do_cancel(event):
    info_log.log(level=TELEGRAM_LOG_LEVEL, msg=f'{event.chat.first_name} clicked {COMMANDS.CANCEL_CONNECT}')
    await start(event)


@client.on(events.NewMessage())
async def capture_all_actions_for_debugging(event):
    msg_id = event.message.id
    user_id = event.chat.id
    action = event.message.message
    ActionRepository().insert(Action(msg_id=msg_id, user_id=user_id, action=action))
    info_log.log(level=TELEGRAM_LOG_LEVEL, msg=f'{event.chat.first_name.encode("ascii", errors="replace").decode()} sent-> {action}')


###############################################00000000000000000000000000000000000000000000000000000000000
###############################################00000000000000000000000000000000000000000000000000000000000
###############################################00000000000000000000000000000000000000000000000000000000000

# کد کلاینت جستجو بر اساس شهر     
user_states = {}

def chunk_buttons(items, n=3):
    return [items[i:i+n] for i in range(0, len(items), n)]

PAGE_SIZE = 5

MAIN_MENU_BUTTONS = [
    [Button.text("🔗 به یک ناشناس وصلم کن", resize=True)],  
    [Button.text("💌 به مخاطب خاصم وصلم کن!", resize=True), Button.text("📩 لینک ناشناس من ", resize=True)],
    [Button.text("🤔 راهنما", resize=True), Button.text("👤 پروفایل من", resize=True)],
    [Button.text("🗣 پشتیبان تلگرام", resize=True)],
    [Button.text("📢 لینک معرفی ربات", resize=True)],
]

@client.on(events.NewMessage(pattern="🔍 جستجو براساس شهر"))
async def handle_search_by_city(event):
    user_id = event.sender_id
    user_states[user_id] = {"step": "select_province"}
    provinces = list(IRAN_PROVINCES.keys())
    buttons = chunk_buttons([Button.text(prov) for prov in provinces], 3)
    await event.respond("🗺️ لطفا ابتدا استان مورد نظر را انتخاب کنید:", buttons=buttons)

@client.on(events.NewMessage)
async def handle_province_or_city_or_gender(event):
    user_id = event.sender_id
    state = user_states.get(user_id)
    if not state or state.get("step") not in ["select_province", "select_city", "select_gender"]:
        return

    text = event.text.strip()

    if state["step"] == "select_province":
        if text not in IRAN_PROVINCES:
            return await event.respond("❗ لطفا یکی از استان‌های موجود را از دکمه‌ها انتخاب کنید.")
        user_states[user_id].update({"province": text, "step": "select_city"})
        cities = IRAN_PROVINCES[text]
        buttons = chunk_buttons([Button.text(city) for city in cities], 3)
        await event.respond(f"🏙️ استان «{text}» انتخاب شد.\nحالا یکی از شهرهای زیر را انتخاب کنید:", buttons=buttons)

    elif state["step"] == "select_city":
        province = state["province"]
        cities = IRAN_PROVINCES.get(province, [])
        if text not in cities:
            return await event.respond("❗ لطفا یکی از شهرهای موجود را از دکمه‌ها انتخاب کنید.")
        user_states[user_id].update({"city": text, "step": "select_gender"})
        buttons = [[
            Button.inline("👧 دختر", data="gender_female"),
            Button.inline("👦 پسر", data="gender_male"),
            Button.inline("👥 باهم", data="gender_all"),
        ]]
        await event.respond("🚻 حالا کدام جنسیت را می‌خواهید جستجو کنم؟", buttons=buttons)

@client.on(events.CallbackQuery(pattern=r'^gender_(female|male|all)$'))
async def handle_gender_selection(event):
    user_id = event.sender_id
    state = user_states.get(user_id)
    if not state or state.get("step") != "select_gender":
        return await event.answer("❗ مرحله نامعتبر", alert=True)

    selected = event.data.decode().split("_")[1]
    gender = None if selected == "all" else selected


    user_states[user_id].update({"gender": gender, "step": "show_results", "page": 0})
    await event.answer()
    await show_city_users(event, user_id, state["province"], state["city"], gender, page=0)

async def show_city_users(event, user_id, province, city, gender=None, page=0):
    session = session_factory()

    try:
        users = get_users_by_city(session, province, city, gender, page=page, limit=PAGE_SIZE)
    except Exception as e:
        await event.respond(f"⛔️ مشکلی در دریافت لیست کاربران پیش آمد.\n\n{str(e)}")
        user_states[user_id] = {}
        session.close()
        return

    session.close()

    if not users:
        await event.respond("❌ هیچ کاربری در این شهر با این مشخصات پیدا نشد.", buttons=MAIN_MENU_BUTTONS)
        user_states[user_id] = {}
        return

    lines = [f"📍 لیست افراد شهر «{city}» که در 3 روز اخیر آنلاین بوده‌اند:\n"]

    for user in users:
        bot_id = f"user_{str(user.id)[-4:]}"
        username_display = f"/{bot_id}"
        name = user.first_name or "❓"
        age = user.age or "❓"
        province_ = user.province or "نامشخص"
        city_ = user.city or "نامشخص"
        chat_status = " (درحال چت🗣)" if user.in_chat else ""
        online_status = get_online_status(user.id)

        lines.append(
            f"{age} 🙍{name} {username_display} {province_}({city_})\n"
            f"{online_status}{chat_status}\n"
            f"{'〰️'*8}"
        )

    date_str = datetime.now().strftime("%Y/%m/%d %H:%M")
    lines.append(f"\n📅 جستجو شده در {date_str}")
    text = "\n".join(lines)

    buttons = []
    if page > 0:
        buttons.append(Button.inline("⏮ لیست قبلی", data="prev_page"))
    if len(users) == PAGE_SIZE:
        buttons.append(Button.inline("⏭ لیست بعدی", data="next_page"))
    buttons.append(Button.text("🔙 بازگشت به منوی اصلی"))

    await event.respond(text, buttons=[buttons])

@client.on(events.NewMessage(pattern="🔙 بازگشت به منوی اصلی"))
async def handle_back_to_main(event):
    user_id = event.sender_id
    user_states[user_id] = {}
    await event.respond("🏠 به منوی اصلی برگشتید.", buttons=MAIN_MENU_BUTTONS)

@client.on(events.CallbackQuery(pattern=r'^(next_page|prev_page)$'))
async def handle_pagination(event):
    user_id = event.sender_id
    state = user_states.get(user_id)
    if not state or state.get("step") != "show_results":
        return await event.answer("❗ مرحله نامعتبر", alert=True)

    if event.data == b'next_page':
        state["page"] += 1
    elif event.data == b'prev_page':
        state["page"] = max(0, state["page"] - 1)

    await show_city_users(
        event, user_id,
        state["province"], state["city"],
        state.get("gender"), state["page"]
    )

def get_users_by_city(session, province, city, gender=None, page=0, limit=5):
    offset = page * limit
    recent_time = datetime.utcnow() - timedelta(days=3)

    query = session.query(User).filter(
        User.province == province,
        User.city == city,
        User.last_online >= recent_time,
        User.status == User.STATUS.ACTIVE
    )

    if gender in ("male", "female"):
        
        gender_map = {
            "male": "پسر",
            "female": "دختر"
        }
        query = query.filter(User.gender == gender_map[gender])

    return query.order_by(User.last_online.desc()).offset(offset).limit(limit).all()

###############################################00000000000000000000000000000000000000000000000000000000000
###############################################00000000000000000000000000000000000000000000000000000000000
###############################################00000000000000000000000000000000000000000000000000000000000    

#کد کلاینت لینک معرفی ربات 

@client.on(events.NewMessage(pattern="📢 لینک معرفی ربات"))
async def send_invite_link(event):
    bot_username = "Space_123321bot"
    invite_link = f"https://t.me/{bot_username}"

    text = (
        "🎭 حس می‌کنی کسی نیست که بدون قضاوت باهاش حرف بزنی؟\n"
        "📱 می‌خوای با آدمایی از سراسر ایران بدون اینکه هویتت معلوم شه گپ بزنی؟\n"
        "یا شاید فقط دنبال یه هم‌صحبت جدیدی...\n\n"
        "💬 اینجا جاییه که ناشناس بودن یعنی آزادی!\n"
        "هرکی یه اسم انتخاب می‌کنه، یه استان و شهر، و وارد چتی می‌شه که ممکنه... خیلی خاص بشه 💘\n\n"
        "🎲 تصادفی گپ بزن، پروفایل ببین، لایک بگیر، و حتی دوستای جدید پیدا کن...\n\n"
        "🎯 برای شروع فقط کافیه ربات رو استارت بزنی:\n\n"
        f"👇👇👇\n🔗 لینک ربات:\n{invite_link}\n\n"
        "بزن بریم... ناشناس باش، خودت باش! 😎"
    )

    photo_path = r"C:\Users\Persian Rayaneh\telegram-anonymous-bot\photo_2025-07-09_22-38-50.jpg"
    await event.reply(file=photo_path, message=text)

######################################################################################################
#کد برای پسام دادن ب پشتیبان و جواب دادن پشتیبان ب کاربر 

support_sessions = {}       
admin_reply_sessions = {}   

SUPPORT_ADMIN_ID = 7714158942  # آی دی عددی پشتیبان این آی دی فرضیه


@client.on(events.NewMessage(pattern="🗣 پشتیبان تلگرام"))
async def contact_support(event):
    user_id = event.sender_id
    user = await client.get_entity(user_id)
    profile = {
        "first_name": getattr(user, "first_name", ""),
        "last_name": getattr(user, "last_name", ""),
        "username": getattr(user, "username", ""),
        "user_id": user_id,
        "bio": "",
    }
    support_sessions[user_id] = {"waiting": True, "profile": profile}
    await event.respond("🗣 در حال اتصال به پشتیبان...\nلطفاً پیام خود را ارسال کنید ✍️\n\n🚨توجه داشته باشید که فقط پیام های متنی برای پشتیبان ارسال میشود " )


@client.on(events.NewMessage)
async def forward_user_message(event):
    user_id = event.sender_id
    text = event.raw_text.strip()

    if support_sessions.get(user_id, {}).get("waiting") and text == "🗣 پشتیبان تلگرام":
        return

    if support_sessions.get(user_id, {}).get("waiting"):
        support_sessions[user_id]["waiting"] = False

        buttons = [
            [Button.inline(f"✏️ پاسخ به کاربر", data=f"reply_{user_id}")]
        ]

        short_id = str(user_id)[-4:]
        await client.send_message(
            SUPPORT_ADMIN_ID,
            f"📩 پیام جدید از کاربر:/user_{short_id}\n\n{text}",
            parse_mode="markdown",
            buttons=buttons
        )

        await reset_btns(event, "✅ پیام شما برای پشتیبان ارسال شد. بازگشت به منوی اصلی ⬇️")
        return

    if user_id == SUPPORT_ADMIN_ID and user_id in admin_reply_sessions:
        target_user = admin_reply_sessions[user_id]
        try:
            await client.send_message(target_user, f"پاسخ پشتیبان 🛟:\n{event.text}")
            await event.respond("✅ پیام شما برای کاربر ارسال شد.")
        except Exception as e:
            await event.respond(f"❌ خطا در ارسال پیام: {e}")
        del admin_reply_sessions[user_id]


@client.on(events.CallbackQuery(pattern=b"reply_(\d+)"))
async def handle_admin_reply(event):
    user_id = int(event.pattern_match.group(1))
    admin_reply_sessions[event.sender_id] = user_id
    await event.answer()
    await event.respond(f"📝 لطفاً پیام خود را برای کاربر /user_{str(user_id)[-4:]} بنویسید:", parse_mode="markdown")




client.run_until_disconnected()
