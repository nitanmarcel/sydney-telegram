import asyncio
import datetime
import json
import re
import uuid
import pytz
from datetime import datetime
from dateutil.parser import parse as dateparse
from enum import Enum

import aiohttp
import websockets
import bot_img
import bot_strings

MESSAGE_CREDS = {}

URL = 'wss://sydney.bing.com/sydney/ChatHub'


class ChatHubException(Exception):
    pass


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
    if userID in MESSAGE_CREDS.keys():
        return MESSAGE_CREDS[userID]
    return None


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
    global MESSAGE_CREDS
    chat_session = None
    answer = None
    image_query = None
    try_again = False
    cards = []
    if userID not in MESSAGE_CREDS.keys():
        chat_session, error = await create_session(cookies)
        if error:
            raise ChatHubException(error)
        chat_session['isStartOfSession'] = True
        chat_session['semaphore'] = asyncio.Semaphore(1)
        chat_session['style'] = style
        chat_session['invocationId'] = 0
        MESSAGE_CREDS[userID] = chat_session
    else:
        chat_session = MESSAGE_CREDS[userID]
        if chat_session['style'] != style:
            del MESSAGE_CREDS[userID]
            return await send_message(userID, message, cookies, style)
        chat_session['isStartOfSession'] = False
        if chat_session['invocationId'] >= 8:
            chat_session['invocationId'] = 0
        else:
            chat_session['invocationId'] += 1

    chat_session['question'] = message

    ws_messages = []

    async with chat_session['semaphore']:
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
            response = await ws.recv()
            response = json.loads(read_until_separator(response))
            if response['type'] == 2:
                if response['item']['result']['value'] == 'Throttled':
                    raise ChatHubException(bot_strings.RATELIMIT_STRING)
            async for responses in ws:
                js = json.loads(read_until_separator(responses))
                if js['type'] == 6:
                    await ws.send('{"type":6}')
                if js['type'] == 2 or js['type'] == 3:
                    ws_messages.append(js)
                    break
                if js['type'] == 7:
                    if js['allowReconnect'] and retry_on_disconnect:
                        try_again = True
                        break
                    raise ChatHubException(
                        bot_strings.CLOSE_MESSAGE_RECEIVED_STRING)
    if try_again:
        return await send_message(userID=userID, message=message, cookies=cookies, style=style, retry_on_disconnect=False)
    if ws_messages:
        for responses in ws_messages:
            if js['type'] == 2:
                item = js['item']
                conversationExpiryTime = item['conversationExpiryTime']
                conversationExpiryTime = dateparse(conversationExpiryTime)
                if 'throttling' in item.keys() and 'messages' in item.keys():
                    maxNumUserMessagesInConversation = js['item'][
                        'throttling']['maxNumUserMessagesInConversation']
                    numUserMessagesInConversation = js['item']['throttling']['numUserMessagesInConversation']
                    if pytz.utc.localize(datetime.now()) >= conversationExpiryTime or numUserMessagesInConversation >= maxNumUserMessagesInConversation:
                        del MESSAGE_CREDS[userID]
                        return await send_message(userID=userID, message=message, cookies=cookies, style=style)
                for response in item['messages']:
                    if response['author'] == 'bot' and 'messageType' not in response.keys() and 'text' in response.keys():
                        answer = response['text']
                        if 'adaptiveCards' in response.keys():
                            for _card in response['adaptiveCards']:
                                if _card['type'] == 'AdaptiveCard':
                                    card = _card['body'][-1]['text']
                                    markdown_pattern = re.findall(
                                        r'\[(.*?)\]\((.*?)\)', card)
                                    cards.extend(
                                        iter(markdown_pattern))
                        else:
                            if 'adaptiveCards' in response.keys() and len(response['adaptiveCards']) > 0:
                                answer = response['adaptiveCards'][-1]['body'][0]['text']
                    if 'contentType' in response.keys() and response['contentType'] == 'IMAGE':
                        image_query = response['text']
                    if 'contentOrigin' in response.keys() and response['contentOrigin'] == 'Apology':
                        answer = response['adaptiveCards'][0]['body'][0]['text']
                    if 'messageType' in response.keys() and response['messageType'] == 'Disengaged' and userID in MESSAGE_CREDS.keys():
                        del MESSAGE_CREDS[userID]
    if image_query:
        answer, error = await bot_img.generate_image(userID, response['text'], cookies)
        if error:
            raise ChatHubException(error)
    if not answer:
        raise ChatHubException(bot_strings.PROCESSING_ERROR_STRING)
    return answer, cards


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
        "telmet",
        "contentability",
        "cachewriteext",
        "e2ecachewrite",
        "dv3sugg",
    ]
    if style == Style.CREATIVE:
        optionsSets.extend(['h3imaginative',
                           'clgalileo', 'gencontentv3'])
    if style == Style.BALANCED:
        optionsSets.extend(
            ['galileo', 'glprompt'])
    if style == Style.PRECISE:
        optionsSets.extend(
            ['h3precise', 'clgalileo'])

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
        "invocationId": f'{invocationId}',
        "target": "chat",
        "type": 4
    }
    return payload
