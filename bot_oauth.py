import json

import aiohttp

headers = {
    'User-Agent':
    'Mozilla/5.0 (Linux; Android 11; WayDroid x86_64 Device Build/RQ3A.211001.001; ) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/109.0.5414.118 Safari/537.36 BingSapphire/24.1.410310303',
    'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
}


async def get_auth_url(client_id):
    oauth_url = 'https://login.live.com/oauth20_authorize.srf'
    redirect_uri = 'https://login.live.com/oauth20_desktop.srf'
    scope = 'service::bing.com::MBI_SSL'
    response_type = 'code'
    return f'{oauth_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type={response_type}&scope={scope}'


async def auth(authCode, client_id):
    cookies = None
    has_sydney = True
    chat_uri = 'https://www.bing.com/sydchat'
    signin_uri = 'https://ssl.bing.com/fd/auth/signin'
    token_uri = 'https://login.live.com/oauth20_token.srf'
    redirect_uri = 'https://login.live.com/oauth20_desktop.srf'
    grant_type = 'authorization_code'

    uri = f'{token_uri}?client_id={client_id}&code={authCode}&redirect_uri={redirect_uri}&grant_type={grant_type}'

    async with aiohttp.ClientSession(headers=headers) as session:
        access_token = None
        cookies = None
        async with session.post(uri, data={
            'client_id': client_id,
            'code': authCode,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }) as response:
            if response.status == 200:
                js = await response.json()
                access_token = js["access_token"]
        if access_token:
            async with session.get(f'{signin_uri}?action=token&provider=windows_live_id&save_token=0&token={access_token}') as response:
                if response.status == 200:
                    js = json.loads(await response.text())
                    if js['success']:
                        cookies = session.cookie_jar
        if cookies:
            async with session.get(chat_uri) as response:
                if response.status != 200:
                    cookies = None
                    has_sydney = False
    return cookies, has_sydney