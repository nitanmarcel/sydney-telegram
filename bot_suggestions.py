import aiohttp
import bot_config
import uuid

async def get_suggestions(query):
    if not bot_config.SUGGESTIONS_API_KEY:
        return None
    suggestions = []
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://www.bingapis.com/api/v7/suggestions?appid={bot_config.SUGGESTIONS_API_KEY}&q={query}') as response:
            if response.status != 200:
                return None
            js = await response.json()
            for suggestionGroups in js['suggestionGroups']:
                for searchSuggestion in suggestionGroups['searchSuggestions']:
                    suggestions.append({'id': str(uuid.uuid4()), 'query': searchSuggestion['query']})
    return suggestions