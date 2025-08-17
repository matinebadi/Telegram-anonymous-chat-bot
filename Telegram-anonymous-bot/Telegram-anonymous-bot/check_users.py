from datetime import datetime, timedelta
from models import session_factory, User
 

session = session_factory()
recent_time = datetime.utcnow() - timedelta(days=3)

users = session.query(User).filter(
    User.last_online >= recent_time
).all()

print(f"🔍 تعداد کل کاربران فعال در 3 روز اخیر: {len(users)}\n")

for user in users:
    print(f"""
🧑‍💼 ID: {user.id}
📛 Name: {user.first_name}
🚻 Gender: {user.gender}
📍 Province: {user.province}
🏙️ City: {user.city}
🕒 Last Online: {user.last_online}
📶 Status: {user.status}
""")

session.close()
