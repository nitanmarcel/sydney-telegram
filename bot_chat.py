import asyncio
import datetime
import json
import re
import uuid
import pytz
import urllib.parse
from datetime import datetime, timedelta
from dateutil.parser import parse as dateparse
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import aiohttp
import websockets
import bot_img
import bot_strings

MESSAGE_CREDS = {}

SEMAPHORE_ITEMS = {}

URL = 'wss://sydney.bing.com/sydney/ChatHub'


class ChatHubException(Exception):
    pass


@dataclass
class SydRenderCard:
    text: Optional[str]
    url: str


@dataclass
class ResponseTypeText:
    answer: str
    cards: List[str]
    render_card: Optional[SydRenderCard]


@dataclass
class ResponseTypeImage:
    images: List[str]
    caption: str


class Style(Enum):
    CREATIVE = 1
    BALANCED = 2
    PRECISE = 3


def read_until_separator(message):
    out = ""
    for x in message:
        if x == '\u001e':
            break
        out += x
    return out


async def clear_session(userID):
    if userID in MESSAGE_CREDS.keys():
        del MESSAGE_CREDS[userID]
        return True
    return False


async def get_session(userID):
    return MESSAGE_CREDS[userID] if userID in MESSAGE_CREDS.keys() else None


async def create_session(cookies):
    chat_session = {}
    error = None
    headers = {
        'User-Agent':
        'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/111.0 BingSapphire/24.1.410310303',
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
    }
    async with aiohttp.ClientSession(headers=headers, cookie_jar=cookies) as session:
        async with session.get('https://www.bing.com/turing/conversation/create') as response:
            if response.status == 200:
                js = await response.json()
                if 'result' in js.keys():
                    result = js['result']
                    if result['message']:
                        error = result['message']
                    else:
                        chat_session['traceID'] = uuid.uuid4()
                        chat_session['clientID'] = js['clientId']
                        chat_session['conversationId'] = js['conversationId']
                        chat_session['conversationSignature'] = js['conversationSignature']
    return chat_session, error


async def send_message(userID, message, cookies, style, retry_on_disconnect=True):
    global SEMAPHORE_ITEMS
    if userID not in SEMAPHORE_ITEMS.keys():
        SEMAPHORE_ITEMS[userID] = asyncio.Semaphore(1)
    seconds = 120
    async with SEMAPHORE_ITEMS[userID]:
        try:
            result = await asyncio.wait_for(_send_message(userID, message, cookies, style, retry_on_disconnect=retry_on_disconnect), timeout=seconds)
            return result
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(
                f"Function {_send_message.__name__} timed out after {seconds} seconds")


async def _send_message(userID, message, cookies, style, retry_on_disconnect=True):
    global MESSAGE_CREDS
    chat_session = None
    answer = None
    update = None
    image_query = None
    try_again = False
    cards = []
    render_card = None
    last_message_type = 0
    if userID not in MESSAGE_CREDS.keys():
        chat_session, error = await create_session(cookies)
        if error:
            raise ChatHubException(error)
        chat_session['isStartOfSession'] = True
        chat_session['style'] = style
        chat_session['invocationId'] = 0
        chat_session['conversationExpiryTime'] = None
        chat_session['numRemainingUserMessagesInConversation'] = None

        MESSAGE_CREDS[userID] = chat_session
    else:
        chat_session = MESSAGE_CREDS[userID]
        if chat_session['style'] != style or (chat_session['conversationExpiryTime'] and pytz.utc.localize(datetime.now()) >= chat_session['conversationExpiryTime']) and chat_session['numRemainingUserMessagesInConversation'] == 0:
            del MESSAGE_CREDS[userID]
            return await send_message(userID, message, cookies, style)
        chat_session['isStartOfSession'] = False
        if chat_session['invocationId'] >= 8:
            chat_session['invocationId'] = 0
        else:
            chat_session['invocationId'] += 1

    chat_session['question'] = message

    ws_messages = []
    message_payload = await build_message(**chat_session)
    async with websockets.connect(URL, ssl=True, ping_timeout=None,
                                  ping_interval=None,
                                  extensions=[
                                      websockets.extensions.permessage_deflate.ClientPerMessageDeflateFactory(
                                          server_max_window_bits=11,
                                          client_max_window_bits=11,
                                          compress_settings={
                                              'memLevel': 4},
                                      ), ]) as ws:
        await ws.send('{"protocol":"json","version":1}')
        await ws.recv()
        await ws.send('{"type":6}')
        await ws.send(json.dumps(message_payload) + '')
        async for responses in ws:
            js = json.loads(read_until_separator(responses))
            if (
                js['type'] == 2
                and js['item']['result']['value'] == 'Throttled'
            ):
                raise ChatHubException(bot_strings.RATELIMIT_STRING)
            last_message_type = js['type']
            if last_message_type == 6:
                await ws.send('{"type":6}')
            elif last_message_type == 1:
                ws_messages.append(js)
            elif last_message_type == 2:
                ws_messages.append(js)
                break
            elif last_message_type == 7:
                if js['allowReconnect'] and retry_on_disconnect:
                    try_again = True
                    break
                raise ChatHubException(
                    bot_strings.CLOSE_MESSAGE_RECEIVED_STRING)
            else:
                break
    if try_again:
        return await send_message(userID=userID, message=message, cookies=cookies, style=style, retry_on_disconnect=False)
    if ws_messages:
        for responses in ws_messages:
            if responses['type'] == 1 and 'arguments' in responses.keys():
                argument = responses['arguments'][-1]
                if messages := argument.get('messages'):
                    messages = responses['arguments'][-1]['messages']
                    for response in messages:
                        if 'text' in response.keys() and response['author'] == 'bot' and 'messageType' not in response.keys():
                            if response['text']:
                                update = response['text']
                            if 'adaptiveCards' in response.keys() and len(response['adaptiveCards']) > 0:
                                _cards = []
                                for _card in response['adaptiveCards']:
                                    if _card['type'] == 'AdaptiveCard':
                                        card = _card['body'][-1]['text']
                                        markdown_pattern = re.findall(
                                            r'\[(.*?)\]\((.*?)\)', card)
                                        _cards.extend(
                                            iter(markdown_pattern))
                                cards = _cards
                        elif 'adaptiveCards' in response.keys() and len(response['adaptiveCards']) > 0:
                            body = response['adaptiveCards'][-1]['body'][0]
                            if 'text' in body.keys():
                                update = response['adaptiveCards'][-1]['body'][0]['text']
            if responses['type'] == 2:
                cards = []
                item = responses['item']
                if 'result' in item.keys():
                    if 'error' in item['result']:
                        raise ChatHubException(
                            item['result']['error']['message'])
                if 'messages' in item.keys():
                    if 'conversationExpiryTime' in item.keys():
                        chat_session['conversationExpiryTime'] = dateparse(item['conversationExpiryTime'])
                    if 'throttling' in item.keys() and 'messages' in item.keys(): # numRemainingUserMessagesInConversation
                        if 'throttling' in responses['item']:
                            chat_session['numRemainingUserMessagesInConversation'] = responses['item']['throttling']['maxNumUserMessagesInConversation'] - responses['item']['throttling']['numUserMessagesInConversation']
                    for response in item['messages']:
                        if response['author'] == 'bot' and 'messageType' not in response.keys() and 'text' in response.keys():
                            if response['text']:
                                answer = response['text']
                            if 'adaptiveCards' in response.keys():
                                for _card in response['adaptiveCards']:
                                    if _card['type'] == 'AdaptiveCard':
                                        card = _card['body'][-1]['text']
                                        markdown_pattern = re.findall(
                                            r'\[(.*?)\]\((.*?)\)', card)
                                        cards.extend(
                                            iter(markdown_pattern))
                        elif response['author'] == 'bot' and 'messageType' in response.keys() and response['messageType'] == 'RenderCardRequest':
                            uri = 'https://www.bing.com/search?q='
                            render_card = SydRenderCard(
                                response["text"], f'{uri}{urllib.parse.quote(response["text"])}')
                        elif 'adaptiveCards' in response.keys() and len(response['adaptiveCards']) > 0:
                            body = response['adaptiveCards'][-1]['body'][0]
                            if 'text' in body:
                                answer = response['adaptiveCards'][-1]['body'][0]['text']
                        if 'contentType' in response.keys() and response['contentType'] == 'IMAGE':
                            image_query = response['text']
                        if 'contentOrigin' in response.keys() and response['contentOrigin'] == 'Apology':
                            answer = response['adaptiveCards'][0]['body'][0]['text']
                        if 'messageType' in response.keys() and response['messageType'] == 'Disengaged' and userID in MESSAGE_CREDS.keys():
                            del MESSAGE_CREDS[userID]
                    break
    if image_query:
        images, error = await bot_img.generate_image(userID, response['text'], cookies)
        if error:
            raise ChatHubException(error)
        if images:
            return ResponseTypeImage(images, response['text'])
    if not answer or not update:
        if render_card:
            answer = f'[{render_card.text}]({render_card.url})'
        else:
            raise ChatHubException(
                f'{bot_strings.PROCESSING_ERROR_STRING}: {last_message_type}')
    return ResponseTypeText(answer or update, cards, render_card)


async def build_message(question, clientID, traceID, conversationId, conversationSignature, isStartOfSession, style, invocationId, **kwargs):
    global MESSAGE_CREDS
    now = datetime.now()
    formatted_date = now.strftime('%Y-%m-%dT%H:%M:%S%z')

    optionsSets = [
        "nlu_direct_response_filter",
        "deepleo",
        "disable_emoji_spoken_text",
        "responsible_ai_policy_235",
        "enablemm",
        "galileo",
        "recansgnd",
        "dv3sugg",
        "cachewriteext",
        "e2ecachewrite",
        "nodlcpcwrite",
        "nointernalsugg",
        "dlwebtrunc",
        "glpromptv3plus"
      ]
    if style == Style.CREATIVE:
        optionsSets = [
        "nlu_direct_response_filter",
        "deepleo",
        "disable_emoji_spoken_text",
        "responsible_ai_policy_235",
        "enablemm",
        "h3imaginative",
        "recansgnd",
        "dv3sugg",
        "clgalileo",
        "gencontentv3"
      ]
    if style == Style.PRECISE:
        optionsSets = [
        "nlu_direct_response_filter",
        "deepleo",
        "disable_emoji_spoken_text",
        "responsible_ai_policy_235",
        "enablemm",
        "h3precise",
        "recansgnd",
        "dv3sugg",
        "clgalileo"
      ]

    payload = {
        "arguments": [
            {
                "source": "cib",
                "optionsSets": optionsSets,
                "allowedMessageTypes": [
                    "Chat",
                    "InternalSearchQuery",
                    "InternalSearchResult",
                    "Disengaged",
                    "InternalLoaderMessage",
                    "RenderCardRequest",
                    "AdsQuery",
                    "SemanticSerp",
                    "GenerateContentQuery",
                    "SearchQuery"
                ],
                "sliceIds": [
                    "321bic62",
                    "styleqnatg",
                    "sydpaycontrol",
                    "toneexpcf",
                    "327telmet",
                    "325content",
                    "303hubcancls0",
                    "326locnwspcs0",
                    "323glpromptv3",
                    "316e2ecache"
                ],
                "verbosity": "verbose",
                "traceId": str(traceID),
                "isStartOfSession": isStartOfSession,
                "message": {
                    "locale": "en-US",
                    "market": "en-US",
                    "region": "WW",
                    "location": "",
                    "locationHints": [
                    ],
                    "timestamp": formatted_date,
                    "author": "user",
                    "inputMethod": "Keyboard",
                    "text": question,
                    "messageType": "Chat"
                },
                "conversationSignature": conversationSignature,
                "participant": {
                    "id": clientID
                },
                "conversationId": conversationId,
            }
        ],
        "invocationId": '2',  # f'{invocationId}',
        "target": "chat",
        "type": 4
    }
    return payload
