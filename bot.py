import logging
import re
from enum import Enum
from urllib.parse import parse_qs, urlparse

from telethon import TelegramClient, events
from telethon.tl.custom import Button

import bot_chat
import bot_config
import bot_db
import bot_oauth
import bot_strings


class State(Enum):
    FIRST_START = 1
    AGREEMENT = 2
    OAUTH = 3
    DONE = 4


STATES = {}

logging.basicConfig(level=logging.INFO)


client = TelegramClient('sydney', bot_config.TELEGRAM_CLIENT_ID,
                        bot_config.TELEGRAM_CLIENT_HASH, catch_up=True)


async def parse_footnotes(text):
    pattern = r"\[\^(\d+)\^\]"
    superscript_table = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

    def replace_fn(match):
        fn_number = match.group(1)
        return fn_number.translate(superscript_table)
    return re.sub(pattern, replace_fn, text)


async def start_handler(event):
    if STATES[event.sender_id] == State.DONE:
        buttons = [
            [Button.inline(text='Donate', data='donate'),
                   Button.inline(text='Logout', data='logout')],
                   [Button.inline(text='Source Code', data='donate')],
                   ]
    else:
        buttons = [
            [Button.inline(text='Continue', data='continue'),
             Button.inline(text='Donate', data='donate')],
            [Button.inline(text='Source Code', data='donate')],
        ]
    if hasattr(event, 'out') and event.out:
        await event.edit(bot_strings.FIRST_START_STRING, buttons=buttons)
    else:
        await client.send_message(event.chat_id, bot_strings.FIRST_START_STRING, buttons=buttons)


async def agreement_handler(event):
    back_button = Button.inline(text='Back', data='back')
    accept_button = Button.inline(text='Agree', data='agree')
    await event.edit(bot_strings.AGREEMENT_STRING,
                     buttons=[[back_button, accept_button]])


async def oauth_handler(event):
    oauth_url = await bot_oauth.get_auth_url(bot_config.SYDNEY_CLIENT_ID)
    oauth_button = Button.url("Log in", url=oauth_url)
    await event.edit(bot_strings.OAUTH_STRING, buttons=[[oauth_button]])


async def logout_handler(event):
    await bot_db.remove_user(event.sender_id)
    await event.edit("Logged out!")


async def donate_handler(event):
    back_button = Button.inline(text='Back', data='back')
    source_button = Button.url(text='Source Code', url='https://github.com/nitanmarcel/sydney-telegram')
    await event.edit(bot_strings.DONATION_STRING,
                     buttons=[[back_button, source_button]], link_preview=False)


@client.on(events.NewMessage(outgoing=False, incoming=True))
async def message_handler(event):
    global STATES
    message = event.text
    if not message:
        return
    if event.sender_id not in STATES.keys():
        STATES[event.sender_id] = State.FIRST_START
    cookies = await bot_db.get_user(event.sender_id)
    if message.startswith("/start"):
        STATES[event.sender_id] = State.DONE if cookies else State.FIRST_START
        await start_handler(event)
        return
    if cookies:
        message, cards = await bot_chat.send_message(event.sender_id, message, cookies)
        message = await parse_footnotes(message)
        buttons = [Button.url(card[0], card[1]) for card in cards]
        buttons = [[buttons[i], buttons[i+1]] if i+1 <
                   len(buttons) else [buttons[i]] for i in range(0, len(buttons), 2)]
        await event.reply(message, buttons=buttons or None)
        return
    state = STATES[event.sender_id]
    if state == State.FIRST_START:
        await start_handler(event)
    if state == State.AGREEMENT:
        await agreement_handler(event)
    if state == State.OAUTH:
        parsed_auth_url = urlparse(message)
        params_auth_url = parse_qs(parsed_auth_url.query)
        if 'code' not in params_auth_url.keys():
            await event.reply(bot_strings.AUTHENTIFICATION_URL_NOT_VALID_STRING)
            return
        auth_code = parse_qs(parsed_auth_url.query)['code'][0]
        cookies, has_sydney = await bot_oauth.auth(auth_code, bot_config.SYDNEY_CLIENT_ID)
        if not has_sydney:
            await event.reply(bot_strings.NOT_IN_WHITELST_STRING)
            STATES[event.sender_id] = State.FIRST_START
            return
        if not cookies:
            await event.reply(bot_strings.AUTHENTIFICATION_FAILED_STRING)
            STATES[event.sender_id] = State.FIRST_START
            return
        await event.reply(bot_strings.AUTHENTIFICATION_DONE_STRING)
        STATES[event.sender_id] = State.DONE
        await bot_db.insert_user(event.sender_id, cookies)


@client.on(events.CallbackQuery())
async def answer_callback_query(event):
    global STATES
    data = event.data.decode()
    if data == 'donate':
        await donate_handler(event)
    if data == 'continue':
        if STATES[event.sender_id] != State.DONE:
            STATES[event.sender_id] = State.AGREEMENT
        await agreement_handler(event)
    if data == 'agree':
        await oauth_handler(event)
        if STATES[event.sender_id] != State.DONE:
            STATES[event.sender_id] = State.OAUTH
    if data == 'back':
        if STATES[event.sender_id] != State.DONE:
            STATES[event.sender_id] = State.FIRST_START
        await start_handler(event)
    if data == 'logout':
        await logout_handler(event)
        STATES[event.sender_id] = State.FIRST_START


async def main():
    await bot_db.init(bot_config.POSTGRES_CONNECTION_STRING, bot_config.COOKIE_ENCRYPTION_KEY)
    await client.start(bot_token=bot_config.TELEGRAM_BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
