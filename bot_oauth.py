import json

import aiohttp

headers = {
    'User-Agent':
    'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/111.0 BingSapphire/24.1.410310303',
    'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}


async def get_auth_url(client_id):
    oauth_url = 'https://login.live.com/oauth20_authorize.srf'
    redirect_uri = 'https://login.live.com/oauth20_desktop.srf'
    scope = 'service::bing.com::MBI_SSL'
    response_type = 'code'
    return f'{oauth_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type={response_type}&scope={scope}'


async def auth(authCode, client_id):
    cookies = None
    has_sydney = True
    token_url = 'https://login.live.com/oauth20_token.srf'
    client_id = '0000000040170455'
    access_token = None

    headers = {
        'User-Agent':
        'Mozilla/5.0 (Linux; Android 11; WayDroid x86_64 Device Build/RQ3A.211001.001; ) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/109.0.5414.118 Safari/537.36 BingSapphire/24.1.410310303',
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
    }

    params = {
        'client_id': client_id,
        'code': authCode,
        'redirect_uri': 'https://login.live.com/oauth20_desktop.srf',
        'grant_type': 'authorization_code'
    }
    url = f'{token_url}?client_id={client_id}&code={authCode}&redirect_uri=https://login.live.com/oauth20_desktop.srf&grant_type=authorization_code'
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, data=params) as response:
            if response.status == 200:
                js = await response.json()
                access_token = js["access_token"]
        params = {
            'client_id': client_id,
            'code': authCode,
            'redirect_uri': 'https://login.live.com/oauth20_desktop.srf',
            'grant_type': 'authorization_code'
        }
        url = f'https://ssl.bing.com/fd/auth/signin?action=token&provider=windows_live_id&save_token=0&token={access_token}'
        async with session.get(url) as response:
            if response.status == 200:
                # Sometimes response.json() seems to fail so use the webpage text instead
                js = json.loads(await response.text())
                if js['success']:
                    cookies = session.cookie_jar
        if cookies:
            url = 'https://www.bing.com/sydchat'
            async with session.get(url) as response:
                if response.status != 200:
                    cookies = None
                    has_sydney = False
    return cookies, has_sydney
