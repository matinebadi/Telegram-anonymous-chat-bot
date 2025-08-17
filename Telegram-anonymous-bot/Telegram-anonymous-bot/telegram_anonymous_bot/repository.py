import abc
from sqlalchemy import and_
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from .models import Message, User, session_factory, Action , Like
from .logger import info_log, error_logger


def singleton(class_):
    """Singleton decorator for repository classes."""
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


class BaseRepository(abc.ABC):
    _Model = None  

    def __init__(self):
        self.session: Session = session_factory()

    def insert(self, obj):
        try:
            self.session.add(obj)
            self.session.commit()
            info_log.info(f"Inserted object: {obj}")
        except IntegrityError as e:
            self.session.rollback()
            error_logger.error(f"IntegrityError in insert(): {e}")
        except DataError as e:
            self.session.rollback()
            error_logger.error(f"DataError in insert(): {e}")
            raise

    def insert_many(self, obj_list):
        try:
            self.session.add_all(obj_list)
            self.session.commit()
            info_log.info(f"Inserted multiple objects: {obj_list}")
        except Exception as e:
            self.session.rollback()
            error_logger.error(f"Error in insert_many(): {e}")
            raise

    def delete(self, obj):
        try:
            self.session.delete(obj)
            self.session.commit()
            info_log.info(f"Deleted object: {obj}")
        except Exception as e:
            self.session.rollback()
            error_logger.error(f"Error in delete(): {e}")
            raise

    def delete_many(self, obj_list):
        try:
            for obj in obj_list:
                self.session.delete(obj)
            self.session.commit()
            info_log.info(f"Deleted multiple objects.")
        except Exception as e:
            self.session.rollback()
            error_logger.error(f"Error in delete_many(): {e}")
            raise

    def commit(self):
        try:
            self.session.commit()
            info_log.info(f"Session committed successfully.")
        except Exception as e:
            self.session.rollback()
            error_logger.error(f"Error in commit(): {e}")
            raise

    def all(self):
        try:
            return self.session.query(self._Model).all()
        except Exception as e:
            error_logger.error(f"Error in all(): {e}")
            return []


@singleton
class UserRepository(BaseRepository):
    _Model = User

    def get_user_with_id(self, user_id: int):
        try:
            return self.session.query(User).filter(User.id == user_id).first()
        except Exception as e:
            error_logger.error(f"Error in get_user_with_id({user_id}): {e}")
            return None

    def update_profile(self, user_id: int, **kwargs):
        """
        آپدیت فیلدهای پروفایل کاربر.
        kwargs می‌تواند شامل profile_photo, gender, province, city, age, bio و ... باشد.
        """
        try:
            user = self.session.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            self.session.commit()
            info_log.info(f"User profile updated: {user_id}")
            return True
        except Exception as e:
            self.session.rollback()
            error_logger.error(f"Error updating profile for user {user_id}: {e}")
            return False

    def get_profile(self, user_id: int):
        """
        گرفتن پروفایل کامل کاربر (همان آبجکت User)
        """
        try:
            return self.session.query(User).filter(User.id == user_id).first()
        except Exception as e:
            error_logger.error(f"Error in get_profile({user_id}): {e}")
            return None
        
    def get_user_by_short_id(self, short_id: str):
        """
        گرفتن کاربری که آیدی‌اش با چهار رقم خاص تمام می‌شود (برای /user_1234)
        """
        try:
            all_users = self.session.query(User).all()
            for user in all_users:
                if str(user.id).endswith(short_id):
                    return user
            return None
        except Exception as e:
            error_logger.error(f"Error in get_user_by_short_id({short_id}): {e}")
            return None

    def get_all_users(self):
        """
        دریافت تمام کاربران از دیتابیس
        """
        try:
            return self.session.query(User).all()
        except Exception as e:
            error_logger.error(f"Error in get_all_users(): {e}")
            return []
        


    def like_user(self, liker_id: int, liked_id: int):
        try:
            if liker_id == liked_id:
                return False, "You cannot like yourself."

            # آیا قبلاً لایک کرده؟
            existing_like = self.session.query(Like).filter_by(
                liker_id=liker_id,
                liked_id=liked_id
            ).first()
            if existing_like:
                return False, "You already liked this user."

            new_like = Like(liker_id=liker_id, liked_id=liked_id)
            self.session.add(new_like)

            # افزایش شمارش لایک در جدول users
            user = self.session.query(User).filter_by(id=liked_id).first()
            if user:
                user.likes_count = (user.likes_count or 0) + 1

            self.session.commit()
            return True, "Like registered."
        except Exception as e:
            self.session.rollback()
            error_logger.error(f"Error in like_user: {e}")
            return False, "Error occurred.s"


    def has_liked(self, liker_id, liked_id):
        session = session_factory()
        return session.query(Like).filter_by(liker_id=liker_id, liked_id=liked_id).first() is not None

    def delete_user(self, user_id: int):
        """
        حذف کامل کاربر از دیتابیس
        """
        try:
            user = self.session.query(User).filter_by(id=user_id).first()
            if user:
                self.session.delete(user)
                self.session.commit()
                info_log.info(f"User {user_id} deleted successfully.")
                return True
            else:
                info_log.warning(f"User {user_id} not found for deletion.")
                return False
        except Exception as e:
            self.session.rollback()
            error_logger.error(f"Error deleting user {user_id}: {e}")
            return False

            
            


@singleton
class MessageRepository(BaseRepository):
    _Model = Message

    def get_with_message_id(self, message_id: int):
        try:
            return self.session.query(Message).filter(Message.id == message_id).first()
        except Exception as e:
            error_logger.error(f"Error in get_with_message_id({message_id}): {e}")
            return None

    def all_unseen_messages(self, user_id: int):
        try:
            return self.session.query(Message).filter(
                and_(Message.to_user_id == user_id, Message.status == Message.STATUS.SENT)
            ).all()
        except Exception as e:
            error_logger.error(f"Error in all_unseen_messages({user_id}): {e}")
            return []

    def delete_all_by_user(self, user_id: int):
        try:
            self.session.query(Message).filter(
                (Message.sender_id == user_id) | (Message.receiver_id == user_id)
            ).delete(synchronize_session=False)
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            error_logger.error(f"Error deleting messages for user {user_id}: {e}")
            return False
        





@singleton
class ActionRepository(BaseRepository):
    _Model = Action


if __name__ == '__main__':
  
    all_users = UserRepository().all()
    print(f"Found {len(all_users)} users")
