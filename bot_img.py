import aiohttp
import asyncio
from urllib.parse import quote, parse_qs, urlparse
from bs4 import BeautifulSoup

import bot_strings
import bot_chat

TRIES = {}
MAX_TRIES = 3


async def get_images(url, aiosession):
    images = []
    async with aiosession.get(url) as response:
        content = await response.text()
        soup = BeautifulSoup(content, "html.parser")
        if img_tags := soup.find_all("img"):
            images = [img.get('src') for img in img_tags]
    return images


async def generate_image(userID, query, cookies, request_id=None):
    global TRIES
    headers = {
        'User-Agent':
        'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/111.0 BingSapphire/24.1.410310303',
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
        'Origin': 'https://www.bing.com',
        'Referer': 'https://www.bing.com/images/create?FORM=GENILP',
        'Accept-Language': 'en-US,en;q=0.5'
    }
    data = {'q': query,
            'qs': 'ds'}

    params = {'q': query,
              'rt': 3,
              'FORM': 'GENCRE'}

    images, error = [], None

    if userID in TRIES.keys():
        return [], bot_strings.POCESSING_ALREADY_STRING, False

    TRIES[userID] = 0
    canceled = False
    async with aiohttp.ClientSession(headers=headers, cookie_jar=cookies) as session:
        async with session.post('https://www.bing.com/images/create', params=params, data=data) as response:
            if not response.history:
                error = bot_strings.PROCESSING_ERROR_STRING
            else:
                parsed_url = urlparse(str(response.url))
                id = parse_qs(parsed_url.query)['id'][0]
                async with session.get(f'https://www.bing.com/images/create/async/results/{id}?q={quote(query)}') as response:
                    if response.status == 200:
                        while not images:
                            if not (await bot_chat.is_pending(request_id)):
                                canceled = True
                                break
                            images = await get_images(str(response.url), session)
                            if TRIES[userID] > MAX_TRIES:
                                break
                            await asyncio.sleep(5)

    del TRIES[userID]
    return images, error, canceled
