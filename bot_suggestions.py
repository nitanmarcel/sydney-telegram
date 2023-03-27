import aiohttp
import bot_config
import uuid

async def get_suggestions(query):
    if not bot_config.SUGGESTIONS_API_KEY:
        return None
    suggestions = []
    headers = {
        'Accept-Language': 'en-US,en;q=1',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/111.0 BingSapphire/24.1.410310303'
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(f'https://www.bingapis.com/api/v7/suggestions?appid={bot_config.SUGGESTIONS_API_KEY}&etmkt=en-US&q={query}&lang=en-US,en;q=0.9') as response:
            if response.status != 200:
                return None
            js = await response.json()
            for suggestionGroups in js['suggestionGroups']:
                for searchSuggestion in suggestionGroups['searchSuggestions']:
                    if 'ghostText' in searchSuggestion.keys():
                        suggestions.append({'id': str(uuid.uuid4()), 'query': searchSuggestion['ghostText']})
                    else:
                        suggestion = query + ' ' + searchSuggestion['query'].split(maxsplit=1)[-1]
                        suggestions.append({'id': str(uuid.uuid4()), 'query': suggestion})
    return suggestions