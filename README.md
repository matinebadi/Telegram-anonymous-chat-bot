# 🤖 Anonymous Chat Telegram Bot

This is a fully-featured **anonymous chat bot** built for Telegram using **Python** and the **Telethon** library.  
It allows users to create anonymous profiles, chat randomly or based on preferences, and interact without revealing their identities.

---

## 📌 Features

### 🔐 Access Control
- Users **must join a specific Telegram channel** before using the bot.
- After joining, they must **create a personal profile** including:
  - Name
  - Gender
  - Age
  - Province and City
  - Bio
  - Profile Picture (optional)

---

### 🧭 Main Features

#### 🔗 My Anonymous Link
Users can get a personal anonymous link (e.g., `https://t.me/YourBot?start=xxxx`) and **share it on social media**. Others can click this link to chat anonymously with them.

#### 💌 Connect Me to My Crush
A guided mode where users can **send anonymous messages to someone they like**, using custom instructions and controlled interaction.

#### 👤 My Profile
Users can view their own profile (as others see it) including editable details, likes received, and more.

#### 🤔 Help
Sends detailed guidance on how to use all features of the bot.

#### 📢 Invite Link
Provides a shareable message and link for users to invite others to the bot.

#### 🗣 Contact Support
Lets users send a **direct message to the admin**, and the admin can reply back via inline buttons.

#### 🔗 Connect to a Stranger
Offers multiple modes of random chat:
- 🎲 Random Search  
- 👧 Search Girls  
- 👦 Search Boys  
- 🎯 Filtered Search
  - By **Age Range**
  - By **Province / City**

Users are matched anonymously with others based on their selection.

---

### 🌟 Additional Features

- 📝 Edit Profile  
- 🗑 Delete Account  
- 💬 Like Profiles  
- ✉️ Send Direct Message  
- 📌 Request Chat  
- 🚫 Block & Unblock Users  
- 💡 Advanced filters in chat search  
- All data is securely stored in a **SQL-based database**

---

## ⚙️ Tech Stack

- **Language**: Python  
- **Library**: [Telethon](https://github.com/LonamiWebs/Telethon)  
- **Database**: SQLAlchemy ORM  
- **Hosting**: Can be deployed on **VPS**

---

## 🚀 How to Run

> ℹ️ You need Python 3.10+ installed.

1. Clone this repository  
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your `api_id`, `api_hash`, and `bot_token` in a config file.
4. Run the bot:
   ```bash
   python -m telegram_anonymous_bot
   ```

---

## 🙋 Developed by

[Matin Ebadi (GitHub)](https://github.com/matinebadi)
