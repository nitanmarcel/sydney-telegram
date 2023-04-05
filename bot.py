import asyncio
import contextlib
import logging
import re
import uuid
from enum import Enum
from urllib.parse import parse_qs, urlparse
from io import BytesIO

from telethon import TelegramClient, events
from telethon.tl.types import UpdateBotStopped
from telethon.tl.types import UpdateBotInlineSend
from telethon.tl.types import InputMediaPhotoExternal
from telethon.tl.custom import Button

import bot_chat
import bot_config
import bot_db
import bot_oauth
import bot_strings
import bot_suggestions
import bot_markdown
import uvloop

class State(Enum):
    FIRST_START = 1
    AGREEMENT = 2
    OAUTH = 3
    DONE = 4
    UNKNOWN = 5
    SETTINGS = 6
    CONNECT_CHAT = 7

class GdprState(Enum):
    STATE_PRIVACY_POLICY = 1
    STATE_RETREIVE_DATA = 2
    STATE_DELETE_DATA = 3
    STATE_COLLECTED_INFORMATION = 4
    STATE_WHY_WE_COLECT = 5
    STATE_WHAT_WE_DO = 6
    STATE_WHAT_WE_NOT_DO = 7
    STATE_RIGHTS_TO_PROCESS = 8

STATES = {}

GDPR_STATES = {}

INLINE_QUERIES_TEXT = {}

logging.basicConfig(level=logging.INFO)

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

client = TelegramClient('sydney', bot_config.TELEGRAM_CLIENT_ID,
                        bot_config.TELEGRAM_CLIENT_HASH, catch_up=True)

client.parse_mode = bot_markdown.SydMarkdown()

async def privacy_handler(event):
    if GDPR_STATES[event.sender_id] != GdprState.STATE_DELETE_DATA:
        buttons = [
            [Button.inline('Retrieve data', 'privacy_retreive')],
            [Button.inline('Delete data', 'privacy_delete')],
            [Button.inline('Collected information', 'privacy_collected')],
            [Button.inline('Why we colect', 'privacy_why')],
            [Button.inline('What we do', 'privacy_whatdo')],
            [Button.inline('What we DO NOT do', 'privacy_whatno')],
            [Button.inline('Rights to process', 'privacy_rights')],
            [Button.inline('Back', 'back')]
        ]
        text = None
        if GDPR_STATES[event.sender_id] == GdprState.STATE_PRIVACY_POLICY:
            text = bot_strings.PRIVACY_STRING.format(bot_config.BOT_OWNER_USERNAME)
        elif GDPR_STATES[event.sender_id] == GdprState.STATE_COLLECTED_INFORMATION:
            text = bot_strings.PRIVACY_COLLECTED_INFORMATION_STRING
        elif GDPR_STATES[event.sender_id] == GdprState.STATE_WHY_WE_COLECT:
            text = bot_strings.PRIVACY_WHY_WE_COLLECT_STRING
        elif GDPR_STATES[event.sender_id] == GdprState.STATE_WHAT_WE_DO:
            text = bot_strings.PRIVACY_WHAT_WE_DO_STRING
        elif GDPR_STATES[event.sender_id] == GdprState.STATE_WHAT_WE_NOT_DO:
            text = bot_strings.PRIVACY_WHAT_WE_NOT_DO_STRING
        elif GDPR_STATES[event.sender_id] == GdprState.STATE_RIGHTS_TO_PROCESS:
            text = bot_strings.PRIVACY_RIGHT_TO_PROCESS_STRING
        if GDPR_STATES[event.sender_id] == GdprState.STATE_RETREIVE_DATA:
            text = bot_strings.PRIVACY_RETRIEVE_DATA_STRING
            data = await bot_db.retrieve_data(event.sender_id)
            if not data:
                await event.reply(bot_strings.PRIVACY_NO_DATA_STRING)
            else:
                sender = await event.get_sender()
                with BytesIO(str.encode(data)) as privacy_data:
                    privacy_data.name = f'{event.sender_id}.txt'
                    await event.reply(
                        bot_strings.PRIVACY_RETRIEVE_DATA_STRING.format(sender.last_name, event.sender_id),
                        file=privacy_data
                    )
            return
    else:
        buttons = [[Button.inline('yes')], [Button.inline('cancel')]]
        text = bot_strings.PRIVACY_DELETE_DATA_STRING
    await event.edit(text, buttons=buttons, link_preview=False)
    
        

async def start_handler(event):
    if STATES[event.sender_id] == State.DONE:
        buttons = [
            [Button.inline(text='Donate', data='donate'),
             Button.inline(text='Logout', data='logout')],
            [Button.inline(text='Source Code', data='donate'),
             Button.inline(text='Settings', data='settings')],
        ]
    else:
        buttons = [
            [Button.inline(text='Continue', data='continue'),
             Button.inline(text='Donate', data='donate')],
            [Button.inline(text='Source Code', data='donate')],
        ]
    buttons.append([Button.inline('Privacy Policy', 'privacy_policy')])
    if not hasattr(event, 'out'):
        await event.edit(bot_strings.FIRST_START_STRING, buttons=buttons)
    elif not event.out:
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
    await bot_chat.clear_session(event.sender_id)
    await event.edit("Logged out!")


async def settings_hanlder(event):
    user = await bot_db.get_user(event.sender_id)
    style = bot_chat.Style(user['style'])
    chat = user['chat']

    str_style = None
    if style == bot_chat.Style.CREATIVE:
        str_style = 'Creative'
        await bot_chat.clear_session(event.sender_id)
    if style == bot_chat.Style.BALANCED:
        str_style = 'Balanced'
        await bot_chat.clear_session(event.sender_id)
    if style == bot_chat.Style.PRECISE:
        str_style = 'Precise'
        await bot_chat.clear_session(event.sender_id)
    buttons = [
        [
            Button.inline(f'Style: {str_style}', 'style'),
            Button.inline('Remove Chat', 'rmchat')
            if chat
            else Button.inline('Connect Chat', 'conchat'),
        ],
        [Button.inline('Back', 'back')],
    ]
    await event.edit(bot_strings.SETTINGS_STRING, buttons=buttons)


async def donate_handler(event):
    back_button = Button.inline(text='Back', data='back')
    source_button = Button.url(
        text='Source Code', url='https://github.com/nitanmarcel/sydney-telegram')
    await event.edit(bot_strings.DONATION_STRING,
                     buttons=[[back_button, source_button]], link_preview=False)


async def handle_chat_connect(event):
    await event.edit(bot_strings.CHAT_CONNECT_STRING, buttons=Button.inline('Back', 'back'))

async def connect_chat(event):
    pass

async def answer_builder(userId=None, chatID=None, style=None, query=None, cookies=None, can_swipe_topics=False, retry_on_timeout=True):
    try:
        buttons = []
        answer = await bot_chat.send_message(userId, query, cookies, bot_chat.Style(style))
        if isinstance(answer, bot_chat.ResponseTypeText):
            if answer.cards:
                buttons = [Button.url(card[0], card[1]) for card in answer.cards]
                buttons = [[buttons[i], buttons[i+1]] if i+1 <
                        len(buttons) else [buttons[i]] for i in range(0, len(buttons), 2)]
                if answer.render_card:
                    buttons.append([Button.url(answer.render_card.text, answer.render_card.url)])
                if can_swipe_topics:
                    buttons.append([Button.inline(text='New Topic', data='newtopic')])
            return answer.answer, buttons or None, query, False
        if isinstance(answer, bot_chat.ResponseTypeImage):
            return answer.images, None, answer.caption, True
    except bot_chat.ChatHubException as exc:
        return str(exc), None, query, False
    except asyncio.TimeoutError as exc:
        if retry_on_timeout:
            with contextlib.suppress(asyncio.TimeoutError):
                return await answer_builder(userId, chatID, style, query, cookies, can_swipe_topics, retry_on_timeout=False)
        return bot_strings.TIMEOUT_ERROR_STRING, None, query, False


@client.on(events.NewMessage(outgoing=False, incoming=True, func=lambda e: e.is_private and not e.via_bot_id))
async def message_handler_private(event):
    global STATES
    message = event.text
    if not message:
        return
    if event.sender_id not in STATES.keys():
        STATES[event.sender_id] = State.FIRST_START
    user = await bot_db.get_user(event.sender_id)
    if message.startswith("/start"):
        STATES[event.sender_id] = State.DONE if user and user['cookies'] else State.FIRST_START
        await start_handler(event)
        return
    if STATES[event.sender_id] == State.CONNECT_CHAT:
        try:
            sender = await event.get_sender()
            permission = await client.get_permissions(int(event.text), event.sender_id)
            if not permission.is_admin:
                await event.reply(bot_strings.CHAT_CONNECT_NOT_ADMIN_STRING)
                return
            user = await bot_db.get_user(chatID=int(event.text))
            if user:
                await bot_db.insert_user(user['id'], cookies=user['cookies'], chat=None, style=user['style'])
            await client.send_message(int(event.text), bot_strings.CHAT_ID_CONNECTED_BROADCAST_STRING.format(sender.username or sender.first_name))
            user = await bot_db.get_user(event.sender_id)
            await bot_db.insert_user(event.sender_id, cookies=user['cookies'], chat=int(event.text), style=user['style'])
        except ValueError:
            await event.reply(bot_strings.INVALID_CHAT_ID_STRING)
        return
    if user and user['cookies']:
        async with client.action(event.chat_id, 'typing'):
            answer, buttons, caption, is_image = await answer_builder(userId=event.sender_id, query=message, style=user['style'],
                                                       cookies=user['cookies'], can_swipe_topics=True)
            if is_image:
                await event.reply(caption, file=[InputMediaPhotoExternal(url=link.split('?')[0]) for link in answer], buttons=buttons)
            else:
                await event.reply(answer, buttons=buttons)
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
            await event.reply(bot_strings.NOT_IN_WHITELST_STRING, buttons=[Button.url('Join', 'https://www.bing.com/new')])
            STATES[event.sender_id] = State.FIRST_START
            return
        if not cookies:
            await event.reply(bot_strings.AUTHENTIFICATION_FAILED_STRING)
            STATES[event.sender_id] = State.FIRST_START
            return
        await event.reply(bot_strings.AUTHENTIFICATION_DONE_STRING.format(bot_config.TELEGRAM_BOT_USERNAME),
                          buttons=[Button.inline('Stay logged in', 'keepcookies')])
        STATES[event.sender_id] = State.DONE
        await bot_db.insert_user(event.sender_id, cookies, style=bot_chat.Style.BALANCED.value, chat=None, keep_cookies=False)
        await start_handler(event)
    if state == State.SETTINGS:
        await settings_hanlder(event)


@client.on(events.CallbackQuery())
async def answer_callback_query(event):
    global STATES
    if event.sender_id not in STATES.keys():
        STATES[event.sender_id] = State.FIRST_START
    user = await bot_db.get_user(userID=event.sender_id)
    if user and user['cookies']:
        STATES[event.sender_id] = State.DONE
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
        await start_handler(event)
    if data == 'keepcookies':
        user = await bot_db.get_user(event.sender_id)
        save = await bot_db.insert_user(event.sender_id, cookies=user['cookies'], chat=user['chat'], style=user['style'], keep_cookies=True)
        if save:
            message = await event.get_message()
            await event.edit(message.text)
    if data == 'settings':
        STATES[event.sender_id] == State.SETTINGS
        await settings_hanlder(event)
    if data == 'style':
        user = await bot_db.get_user(event.sender_id)
        style = bot_chat.Style(user['style'])
        if style == bot_chat.Style.CREATIVE:
            await bot_db.insert_user(event.sender_id, cookies=user['cookies'], chat=user['chat'], style=bot_chat.Style.BALANCED.value)
        if style == bot_chat.Style.BALANCED:
            await bot_db.insert_user(event.sender_id, cookies=user['cookies'], chat=user['chat'], style=bot_chat.Style.PRECISE.value)
        if style == bot_chat.Style.PRECISE:
            await bot_db.insert_user(event.sender_id, cookies=user['cookies'], chat=user['chat'], style=bot_chat.Style.CREATIVE.value)
        await settings_hanlder(event)
    if data == 'conchat':
        STATES[event.sender_id] = State.CONNECT_CHAT
        await handle_chat_connect(event)
    if data == 'rmchat':
        user = await bot_db.get_user(event.sender_id)
        await bot_db.insert_user(event.sender_id, cookies=user['cookies'], chat=None, style=user['style'])
        await settings_hanlder(event)
    if data == 'newtopic':
        original_message = await event.get_message()
        if message := original_message:
            if bool(message.reply_to_msg_id):
                reply_message = await message.get_reply_message()
                if reply_message:
                    message = reply_message
            if message.sender_id == event.sender_id:
                user = await bot_db.get_user(message.sender_id)
                if not user:
                    user = await bot_db.get_user(chatID=message.chat_id)
                if user:
                    await bot_chat.clear_session(user['id'])
                    buttons = None
                    if original_message.buttons and len(original_message.buttons) > 1:
                        buttons = original_message.buttons[:-1]
                    await event.edit(text=original_message.text, file=original_message.file, buttons=buttons)
                    await event.answer(bot_strings.NEW_TOPIC_CREATED_STRING)
                    return
        await event.answer(bot_strings.TOPIC_EXPIRES_STRING, alert=True)
        return
    if data == 'privacy_policy':
        GDPR_STATES[event.sender_id] = GdprState.STATE_PRIVACY_POLICY
        await privacy_handler(event)
    if data == 'privacy_retreive':
        GDPR_STATES[event.sender_id] = GdprState.STATE_RETREIVE_DATA
        await privacy_handler(event)
    if data == 'privacy_delete':
        GDPR_STATES[event.sender_id] = GdprState.STATE_DELETE_DATA
        await privacy_handler(event)
    if data == 'privacy_collected':
        GDPR_STATES[event.sender_id] = GdprState.STATE_COLLECTED_INFORMATION
        await privacy_handler(event)
    if data == 'privacy_why':
        GDPR_STATES[event.sender_id] = GdprState.STATE_WHY_WE_COLECT
        await privacy_handler(event)
    if data == 'privacy_whatdo':
        GDPR_STATES[event.sender_id] = GdprState.STATE_WHAT_WE_DO
        await privacy_handler(event)
    if data == 'privacy_whatno':
        GDPR_STATES[event.sender_id] = GdprState.STATE_WHAT_WE_NOT_DO
        await privacy_handler(event)
    if data == 'privacy_rights':
        GDPR_STATES[event.sender_id] = GdprState.STATE_RIGHTS_TO_PROCESS
        await privacy_handler(event)
    if data == 'yes':
        if event.sender_id in GDPR_STATES.keys() and GDPR_STATES[event.sender_id] == GdprState.STATE_DELETE_DATA:
            result = await bot_db.remove_user(event.sender_id)
            GDPR_STATES[event.sender_id] = GdprState.STATE_PRIVACY_POLICY
            await privacy_handler(event)
            if not result:
                await event.reply(bot_strings.PRIVACY_NO_DATA_STRING)
    if data == 'cancel':
        if event.sender_id in GDPR_STATES.keys() and GDPR_STATES[event.sender_id] == GdprState.STATE_DELETE_DATA:
            GDPR_STATES[event.sender_id] = GdprState.STATE_PRIVACY_POLICY
            await privacy_handler(event)
    await event.answer()


@client.on(events.InlineQuery())
async def answer_inline_query(event):
    global INLINE_QUERIES_TEXT
    message = event.text
    builder = event.builder
    user = await bot_db.get_user(event.sender_id)
    if not user:
        await event.answer(switch_pm=bot_strings.INLINE_NO_COOKIE_STRING, switch_pm_param='start')
        return
    if not message:
        if bool(await bot_chat.get_session(event.sender_id)):
            await event.answer([builder.article('Start new topic', text=bot_strings.NEW_TOPIC_CREATED_STRING, id=f'{uuid.uuid4()}_newtopic')])
        return
    INLINE_QUERIES_TEXT[event.sender_id] = {}

    suggestions = await bot_suggestions.get_suggestions(message)
    articles = [builder.article(message, text=f'❓ __{message}__', buttons=[
                                Button.inline('Please wait...')])]

    if suggestions:
        for suggestion in suggestions:
            message = suggestion['query']
            if event.text != message:
                INLINE_QUERIES_TEXT[event.sender_id].update(
                    {suggestion['id']: message})
                articles.append(builder.article(message, text=f'❓ __{message}__', buttons=[
                                Button.inline('Please wait...')], id=suggestion['id']))

    await event.answer(articles)


@client.on(events.Raw(UpdateBotInlineSend))
async def handle_inline_send(event):
    user = await bot_db.get_user(event.user_id)
    query = event.query
    if event.id.endswith('_newtopic'):
        await bot_chat.clear_session(event.user_id)
        return
    if event.id in INLINE_QUERIES_TEXT[event.user_id]:
        suggestions = INLINE_QUERIES_TEXT[event.user_id]
        query = suggestions[event.id]
    answer, buttons, caption, is_image = await answer_builder(userId=event.user_id, query=query, style=user['style'], cookies=user['cookies'])
    if is_image:
        images_list = '- ' + '\n- '.join([link.split('?')[0] for link in answer])
        await client.edit_message(event.msg_id, text=f'{caption}\n\n{images_list}')
    else:
        if buttons:
            await client.edit_message(
                event.msg_id, text=f'❓ __{caption}__\n\n{answer}', buttons=buttons
            )
        else:
            await client.edit_message(event.msg_id, text=f'❓ __{caption}__\n\n{answer}')


@client.on(events.Raw(UpdateBotStopped))
async def handle_bot_stopped(event):
    if event.stopped:
        user = await bot_db.get_user(event.user_id)
        if user:
            await bot_db.remove_user(event.user_id)
            await bot_chat.clear_session(event.user_id)


@client.on(events.NewMessage(outgoing=False, incoming=True, func=lambda e: not e.is_private))
async def message_handler_groups(event):
    if event.text and event.text.split()[0] == '/id':
        await event.reply(f'`{event.chat_id}`')
        return
    if not event.mentioned or not event.text:
        return
    async with client.action(event.chat_id, 'typing'):
        user = await bot_db.get_user(userID=None, chatID=event.chat_id)
        if not user:
            user = await bot_db.get_user(userID=event.sender_id)
        message = event.text.replace(
            f'@{bot_config.TELEGRAM_BOT_USERNAME}', '').strip()
        if not user:
            answer, buttons, caption, is_image = await answer_builder(userId=None, query=message, style=bot_chat.Style.BALANCED, cookies=None)
            await event.reply(f'⚠️ {answer}', buttons=[Button.url('Log in', url=f'http://t.me/{bot_config.TELEGRAM_BOT_USERNAME}?start=help')])
            return
        answer, buttons, caption, is_image = await answer_builder(userId=user['id'], query=message, style=user['style'], cookies=user['cookies'] if user else None, can_swipe_topics=True)
        if is_image:
            await event.reply(caption, file=[InputMediaPhotoExternal(url=link.split('?')[0]) for link in answer], buttons=buttons)
        else:
            await event.reply(answer, buttons=buttons)


async def main():
    await bot_db.init(bot_config.POSTGRES_CONNECTION_STRING, bot_config.COOKIE_ENCRYPTION_KEY)
    await client.start(bot_token=bot_config.TELEGRAM_BOT_TOKEN)
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        client.loop.run_until_complete(main())
    finally:
        if client.is_connected():
            client.disconnect()
