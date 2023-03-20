import asyncio
import datetime
import json
import re
import uuid
from datetime import datetime

import aiohttp
import websockets

CLIENTS = {}
MESSAGE_CREDS = {}

URL = 'wss://sydney.bing.com/sydney/ChatHub'


def read_until_separator(message):
    out = ""
    for x in message:
        if x == '\u001e':
            break
        out += x
    return out


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


async def send_message(userID, message, cookies):
    global MESSAGE_CREDS
    chat_session = None
    answer = None
    cards = []
    if userID not in MESSAGE_CREDS.keys():
        chat_session, error = await create_session(cookies)
        if error:
            return error, cards
        chat_session['isStartOfSession'] = True
        chat_session['semaphore'] = asyncio.Semaphore(1)
        MESSAGE_CREDS[userID] = chat_session
    else:
        chat_session = MESSAGE_CREDS[userID]
        chat_session['isStartOfSession'] = False

    chat_session['question'] = message
    async with chat_session['semaphore']:
        message_payload = await build_message(**chat_session)
        async with websockets.connect(URL,
                                              ssl=True,
                                              extra_headers={
                                                  "Origin": "https://www.bing.com"},
                                              server_hostname='sydney.bing.com',
                                              origin='https://www.bing.com',
                                              user_agent_header='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
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
            message_payload = await build_message(**chat_session)
            await ws.send(json.dumps(message_payload) + '')
            response = await ws.recv()
            response = json.loads(read_until_separator(response))
            if (
                response['type'] == 2
                and 'item' in response.keys()
                and 'result' in response['item'].keys()
                and response['item']['result']['value'] == 'Throttled'
            ):
                answer = "⚠️ Sorry, you've reached the limit of messages you can send to Bing within 24 hours. Check back soon!"
                return answer, cards
            async for responses in ws:
                js = json.loads(read_until_separator(responses))
                if js['type'] == 2:
                    if 'item' in js.keys():
                        if 'throttling' in js['item'].keys():
                            maxNumUserMessagesInConversation = js['item'][
                                'throttling']['maxNumUserMessagesInConversation']
                            numUserMessagesInConversation = js['item']['throttling']['numUserMessagesInConversation']
                            messages = js['item']['messages']
                            for message in messages:
                                if message['author'] == 'bot' and 'messageType' not in message.keys() and 'text' in message.keys():
                                    answer = message['text']
                                    if 'adaptiveCards' in message.keys():
                                        for _card in message['adaptiveCards']:
                                            if _card['type'] == 'AdaptiveCard':
                                                card = _card['body'][-1]['text']
                                                markdown_pattern = re.findall(
                                                    r'\[(.*?)\]\((.*?)\)', card)
                                                cards.extend(
                                                    iter(markdown_pattern))
                                    break
                            if numUserMessagesInConversation >= (maxNumUserMessagesInConversation - 1) and userID in MESSAGE_CREDS:
                                del MESSAGE_CREDS[userID]
                if answer:
                    break
        return answer, cards


async def build_message(question, clientID, traceID, conversationId, conversationSignature, isStartOfSession, **kwargs):
    global MESSAGE_CREDS
    now = datetime.now()
    formatted_date = now.strftime('%Y-%m-%dT%H:%M:%S%z')

    payload = {
        "arguments": [
            {
                "source": "cib",
                "optionsSets": [
                    "nlu_direct_response_filter",
                    "deepleo",
                    "disable_emoji_spoken_text",
                    "responsible_ai_policy_235",
                    "enablemm",
                    "galileo",
                    "dv3sugg"
                ],
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

                ],
                "traceId": f"{traceID}",
                "isStartOfSession": isStartOfSession,
                "message": {
                    "locale": "en-US",
                    "market": "en-US",
                    "region": "US",
                    "location": "",
                    "locationHints": [
                    ],
                    "timestamp": formatted_date,
                    "author": "user",
                    "inputMethod": "Keyboard",
                    "text": f"{question}",
                    "messageType": "Chat"
                },
                "conversationSignature": f"{conversationSignature}",
                "participant": {
                    "id": f"{clientID}"
                },
                "conversationId": f"{conversationId}"
            }
        ],
        "invocationId": "0",
        "target": "chat",
        "type": 4
    }
    return payload
