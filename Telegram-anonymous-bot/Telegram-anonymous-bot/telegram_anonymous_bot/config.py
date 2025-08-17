import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from sqlalchemy import create_engine

# بارگذاری متغیرهای محیطی از فایل .env
load_dotenv()

# مسیرها
PATH_ROOT = Path(__file__).resolve().parent.parent
PATH_SESSION = PATH_ROOT / 'sessions'
PATH_STORAGE = PATH_ROOT / 'storage'

# ساخت دایرکتوری‌ها در صورت نبود
PATH_SESSION.mkdir(parents=True, exist_ok=True)
PATH_STORAGE.mkdir(parents=True, exist_ok=True)

# تنظیمات تلگرام
BOT_TOKEN = os.getenv('BOT_TOKEN')
YOUR_BOT_USERNAME = os.getenv('YOUR_BOT_USERNAME')
API_ID = int(os.getenv('API_ID'))
API_KEY = os.getenv('API_KEY')

# تنظیمات پروکسی
try:
    proxy_host = os.getenv('PROXY_HOST')
    proxy_port = int(os.getenv('PROXY_PORT', 9050))
    proxy_protocol = os.getenv('PROXY_PROTOCOL', 'socks5')

    if proxy_host:
        PROXY = (proxy_protocol, proxy_host, proxy_port)
    else:
        PROXY = None
except Exception:
    PROXY = None

print('PROXY is', PROXY)

# تنظیمات پایگاه‌داده
SQL_TYPE = os.getenv('SQL_TYPE', 'sqlite')
SQL_DATABASE = os.getenv('SQL_DATABASE', 'anonbotdb.sqlite3')

if SQL_TYPE == 'sqlite':
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{PATH_STORAGE / SQL_DATABASE}"
else:
    SQL_USER = os.getenv('SQL_USER', 'user')
    SQL_PASSWORD = os.getenv('SQL_PASSWORD', 'password')
    SQL_HOST = os.getenv('SQL_HOST', 'localhost')
    SQL_PORT = int(os.getenv('SQL_PORT', '3306'))

    SQLALCHEMY_DATABASE_URL = f"{SQL_TYPE}://{SQL_USER}:{SQL_PASSWORD}@{SQL_HOST}:{SQL_PORT}/{SQL_DATABASE}"

# ساخت Engine
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)

class COMMANDS:
    START = '/start'
    CONNECT = "💌 به مخاطب خاصم وصلم کن!"
    GIVE_MY_LINK = '📩 لینک ناشناس من'
    INSTAGRAM = '/Instagram'
    LINK = '/link'
    CANCEL_CONNECT = 'انصراف'
    GET_UNSEEN_MESSAGES = '/newmsg'
    PROFILE = 'پروفایل'  # ← این رو اضافه کن

    @classmethod
    def command_list(cls) -> List[str]:
        return [getattr(cls, attr) for attr in dir(cls) if not attr.startswith("__") and not callable(getattr(cls, attr))]

# پیام‌های ثابت ربات
class MESSAGES:
    AFTER_START_COMMAND = """حله!

چه کاری برات انجام بدم؟"""
    AFTER_BAD_COMMAND = """متوجه نشدم :/

چه کاری برات انجام بدم؟"""
    AFTER_CONNECT_COMMAND = """برای اینکه بتونم به مخاطب خاصت بطور ناشناس وصلت کنم، یکی از این ۲ کار رو انجام بده:

راه اول 👈 : Username@ یا همون آی‌دی تلگرام اون شخص رو الان وارد ربات کن!

راه دوم 👈 : الان یه پیام متنی از اون شخص به این ربات فوروارد کن تا ببینم عضو هست یا نه!"""
    AFTER_GIVE_MY_LINK_COMMAND_EXTRA = f"""☝️ پیام بالا رو به دوستات و گروه‌هایی که می‌شناسی فـوروارد کن یا لـینک داخلش رو تو شبکه‌های اجتماعی بذار و توئیت کن، تا بقیه بتونن بهت پیام ناشناس بفرستن. پیام‌ها از طریق همین برنامه بهت می‌رسه.

اینستاگرام داری و میخوای دنبال کننده‌های اینستاگرامت برات پیام ناشناس بفرستن؟
پس روی دستور 👈🏻 {COMMANDS.INSTAGRAM} کلیک کن!"""
    USER_NOT_FOUND = f"""متاسفانه مخاطبت الان عضو ربات نیست!

چطوره یه جوری لینک ربات رو بهش برسونی تا بیاد و عضو بشه؟ مثلا لینک خودت رو بهش بفرستی یا اگه جزء دنبال کننده‌های اینستاگرامته لینکت رو در اینستاگرامت بذاری.

برای دریافت لینک 👈 {COMMANDS.LINK}"""
    RETRY_CONNECT = """👈 یه پیام از مخاطب خاصت برام فوروارد کن و یا آی‌دیش رو برام بفرست تا بتونم چک کنم که عضو ربات هست یا نه!"""
    YOUR_TARGET_STOPPED_THE_BOT = """مخاطبت ربات رو خاموش کرده و پیام بهش نرسید! هروقت دوباره از ربات استفاده کنه پیامت رو می‌بینه.

چه کاری برات انجام بدم؟"""
    SEND_SUCCESSFULLY = """پیام شما ارسال شد 😊

چه کاری برات انجام بدم؟"""
    GET_MESSAGE_INSTRUCTION = f"""📬 شما یک پیام ناشناس جدید دارید !

جهت دریافت کلیک کنید 👈 {COMMANDS.GET_UNSEEN_MESSAGES}"""
    NO_ANY_MESSAGES = f"""پیام نخونده‌ای نداری !

چطوره با زدن این دستور 👈 {COMMANDS.LINK} لینک خودت رو بگیری و به دوستات یا گروه‌ها بفرستی تا بتونند بهت پیام ناشناس بفرستند؟ 😊"""
    YOUR_MSG_WAS_READ = """این پیامت ☝️ رو دید!"""

    BTN_ANSWER = '✍️ پاسخ'
    BTN_BLOCK = '⛔️ بلاک'
    WAITING_TO_ANSWER = "☝️ در حال پاسخ دادن به فرستنده این پیام هستی ... ؛ منتظریم بفرستی :)"

    INSTAGRAM_DESCRIPTION = """میخوای دنبال‌کننده‌های اینستاگرامت برات پیام ناشناس بفرستن؟ 🤔

کافیه لینک ناشناس رو کپی کنی و توی پروفایلت وارد کنی

لینک مخصوصت 👇"""


class TEMPLATES_MESSAGES:
    @staticmethod
    def AFTER_GIVE_MY_LINK_COMMAND(name: str, link: str):
        return f"""سلام {name} هستم ✋️

لینک زیر رو لمس کن و هر حرفی که تو دلت هست یا هر انتقادی که نسبت به من داری رو با خیال راحت بنویس و بفرست. بدون اینکه از اسمت باخبر بشم پیامت به من می‌رسه. خودتم می‌تونی امتحان کنی و از بقیه بخوای راحت و ناشناس بهت پیام بفرستن، حرفای خیلی جالبی می‌شنوی! 😉

👇👇
{link}"""

    @staticmethod
    def READY_TO_SEND_MESSAGE(name: str):
        return f"""در حال ارسال پیام ناشناس به {name} هستی!

با خیال راحت هر حرف یا انتقادی که تو دلت هست بنویس، این پیام بصورت کاملا ناشناس ارسال میشه :)"""

    RESPOND_LIKE = 'respond'

    @staticmethod
    def RESPOND_TO_MESSAGE(message_orm_id: int):
        return f"{TEMPLATES_MESSAGES.RESPOND_LIKE}_{message_orm_id}"

    @staticmethod
    def YOUR_LINK(user_id: int):
        return f'https://t.me/{YOUR_BOT_USERNAME}?start={user_id}'
