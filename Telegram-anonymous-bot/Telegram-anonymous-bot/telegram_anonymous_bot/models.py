from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, DateTime,
    ForeignKey, Text, Enum, Integer, BIGINT , UniqueConstraint , Boolean , BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
from .config import engine

# Base و Session تعریف
Base = declarative_base()
_SessionFactory = sessionmaker(bind=engine)


def session_factory():
    """ایجاد جداول و بازگرداندن session جدید"""
    Base.metadata.create_all(engine)
    return _SessionFactory()


# اجرای اولیه ساخت جداول
session_factory()

class User(Base):
    __tablename__ = 'users'

    class STATUS:
        ACTIVE = 'active'
        DEACTIVATE = 'deactivate'

    id = Column(BIGINT(), primary_key=True, autoincrement=False)
    access_hash = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    username = Column(String(100))
    status = Column(Enum(STATUS.ACTIVE, STATUS.DEACTIVATE, name="status_s"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    in_chat = Column(Boolean, default=False)

    
    last_seen = Column(DateTime, nullable=True)  # ✅ جدید
    last_online = Column(DateTime, default=datetime.utcnow)

    # فیلدهای جدید برای پروفایل
    profile_photo = Column(String(255), nullable=True)
    gender = Column(String(10), nullable=True)
    province = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    age = Column(Integer, nullable=True)
    bio = Column(Text, nullable=True)
    likes_count = Column(Integer, default=0)

    def __init__(self, user_id, last_name, first_name, access_hash, status, created_at=None, username=None,
                 profile_photo=None, gender=None, province=None, city=None, age=None, bio=None, likes_count=0):
        self.id = user_id
        self.last_name = last_name
        self.first_name = first_name
        self.username = username
        self.access_hash = str(access_hash)
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.profile_photo = profile_photo
        self.gender = gender
        self.province = province
        self.city = city
        self.age = age
        self.bio = bio
        self.likes_count = likes_count

    def __repr__(self):
        return f"<User id={self.id}, name={self.first_name}>"


class Message(Base):
    __tablename__ = 'messages'

    class STATUS:
        CREATED = 'created'
        SENT = 'sent'
        SEEN = 'seen'
        FAILED = 'failed'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    from_user_id = Column(BIGINT, ForeignKey('users.id'), nullable=False)
    to_user_id = Column(BIGINT, ForeignKey('users.id'), nullable=False)
    msg_id = Column(BIGINT, nullable=True)
    msg_from_bot_id = Column(BIGINT, nullable=True)
    message = Column(Text, nullable=True)

    # 🔹 فیلدهای جدید برای فایل
    media_path = Column(String(255), nullable=True)
    media_type = Column(String(50), nullable=True)

    status = Column(Enum(
        STATUS.CREATED, STATUS.SENT, STATUS.FAILED, STATUS.SEEN,
        name='status_m'), default=STATUS.CREATED)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, from_user_id, to_user_id, message=None, msg_id=None, created_at=None, msg_from_bot_id=None, media_path=None, media_type=None):
        self.from_user_id = from_user_id
        self.to_user_id = to_user_id
        self.message = message
        self.msg_id = msg_id
        self.msg_from_bot_id = msg_from_bot_id
        self.media_path = media_path
        self.media_type = media_type
        self.created_at = created_at or datetime.utcnow()

    def __repr__(self):
        return f"<Message id={self.id} from={self.from_user_id} to={self.to_user_id}>"


class Action(Base):
    __tablename__ = 'actions'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = Column(BIGINT, ForeignKey('users.id'), nullable=False)
    msg_id = Column(BIGINT(), nullable=False)
    action = Column(Text(), nullable=False)
    created_at = Column(DateTime(), default=datetime.utcnow, nullable=False)

    def __init__(self, user_id, action, msg_id):
        self.user_id = user_id
        self.action = action
        self.msg_id = msg_id
        self.created_at = datetime.utcnow()


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True)
    liker_id = Column(Integer, ForeignKey('users.id'))      # کسی که لایک کرده
    liked_id = Column(Integer, ForeignKey('users.id'))      # کسی که لایک شده
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('liker_id', 'liked_id', name='one_like_per_pair'),
    )


class ChatRequest(Base):
    __tablename__ = 'chat_requests'

    id = Column(Integer, primary_key=True)
    from_user_id = Column(Integer, ForeignKey("users.id"))
    to_user_id = Column(Integer, ForeignKey("users.id"))
    accepted = Column(Boolean, default=None)  # None = منتظر / True = قبول / False = رد
    created_at = Column(DateTime, default=datetime.utcnow)


class ActiveChat(Base):
    __tablename__ = 'active_chats'

    id = Column(Integer, primary_key=True)
    user1_id = Column(BigInteger, nullable=False)
    user2_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user1_id', 'user2_id', name='unique_chat'),
    )

    def __init__(self, user1_id, user2_id):
        # تضمین اینکه همیشه user1_id کوچکتره
        if user1_id <= user2_id:
            self.user1_id = user1_id
            self.user2_id = user2_id
        else:
            self.user1_id = user2_id
            self.user2_id = user1_id

    def is_participant(self, user_id):
        return self.user1_id == user_id or self.user2_id == user_id


class DirectMessage(Base):
    __tablename__ = "direct_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(BigInteger, nullable=False)
    receiver_id = Column(BigInteger, nullable=False)
    message_text = Column(Text, nullable=True)
    media_file = Column(String, nullable=True)  # ← مطمئن شو این هست
    media_type = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    is_reply = Column(Boolean, default=False)
    reply_to_id = Column(Integer, ForeignKey("direct_messages.id"), nullable=True)

    reply_to = relationship("DirectMessage", remote_side=[id], backref="replies")




class UserBlock(Base):
    __tablename__ = "user_blocks"
    id = Column(Integer, primary_key=True)
    blocker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    blocked_id = Column(Integer, ForeignKey("users.id"), nullable=False)

def is_blocked(session, blocker_id: int, blocked_id: int) -> bool:
    record = session.query(UserBlock).filter_by(blocker_id=blocker_id, blocked_id=blocked_id).first()
    return record is not None