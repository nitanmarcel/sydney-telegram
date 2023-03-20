import gzip
import pickle
import re

import aiohttp
import cryptography.fernet as fernet
from gino import Gino

db = Gino()

ENCRYPTION_KEY = None


def generate_key():
    encryption_key = fernet.Fernet.generate_key()
    with open('bot_config.py', 'r+') as f:
        contents = f.read()
        pattern = r"COOKIE_ENCRYPTION_KEY\s*=\s*None"
        new_contents = re.sub(
            pattern, f'COOKIE_ENCRYPTION_KEY = {encryption_key}', contents)
        f.seek(0)
        f.write(new_contents)
        f.truncate()
    print("Here is your cookie encryption key. The key has been saved in bot_config.py:",
          encryption_key, "", sep="\n\n")
    return encryption_key


def cookies_save(cookie_jar):
    f = fernet.Fernet(ENCRYPTION_KEY)
    data = pickle.dumps(cookie_jar._cookies, pickle.HIGHEST_PROTOCOL)
    compressed_data = gzip.compress(data)
    return f.encrypt(compressed_data)


def cookies_load(cookie_jar):
    f = fernet.Fernet(ENCRYPTION_KEY)
    compressed_data = f.decrypt(cookie_jar)
    data = gzip.decompress(compressed_data)
    cookies = aiohttp.CookieJar()
    cookies.clear()
    cookies._cookies = pickle.loads(data)
    return cookies


class User(db.Model):
    __tablename__ = 'usersb'
    id = db.Column(db.Integer(), primary_key=True)
    cookies = db.Column(db.LargeBinary())


USERS = {}


async def init(dbstring, encryption_key):
    global ENCRYPTION_KEY
    global USERS, ENCRYPTION_KEY
    if not encryption_key:
        ENCRYPTION_KEY = generate_key()
    else:
        ENCRYPTION_KEY = encryption_key

    await db.set_bind(dbstring)
    await db.gino.create_all()

    all_users = await db.all(User.query)
    USERS = {u.id: cookies_load(u.cookies) for u in all_users}
    return USERS


async def get_user(userID):
    return USERS[userID] if userID in USERS.keys() else None


async def insert_user(userID, cookies=None, keep_cookies=False):
    global USERS
    if cookies:
        USERS[userID] = cookies
    if userID not in USERS.keys():
        return None
    if keep_cookies and userID:
        return await User.create(id=userID, cookies=cookies_save(USERS[userID]))
    return USERS[userID]


async def remove_user(userID):
    global USERS
    if userID in USERS.keys():
        del USERS[userID]
        user = await User.get(userID)
        if user:
            return await User.delete.where(User.id == userID).gino.status()
    return False
