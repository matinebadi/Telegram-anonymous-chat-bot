from sqlalchemy import create_engine

engine = create_engine(r"sqlite:///C:\Users\Persian Rayaneh\telegram-anonymous-bot\storage\anonbotdb.sqlite3")

with engine.connect() as conn:
    try:
        conn.execute("ALTER TABLE users ADD COLUMN last_seen DATETIME;")
        print("ستون last_seen با موفقیت اضافه شد.")
    except Exception as e:
        print("خطا در اضافه کردن ستون:", e)
