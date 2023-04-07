from telethon.extensions import markdown
from telethon import types
import re

def extract_code(text):
    pattern = r'```([\w+#]*)\n(.+?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    languages = []
    for match in matches:
        language = match[0]
        code = match[1]
        if language and language[0].islower():
            code = code.replace(language, '', 1).lstrip()
            languages.append(language.lower())
            text = text.replace(f'```{language}\n{code}```', f'```{code}```')
        else:
            languages.append('')
    pattern = r'```(.+?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    languages.extend('' for _ in matches)
    return text, languages

def parse_footnotes(text):
    table = str.maketrans("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", 
                          "⁰¹²³⁴⁵⁶⁷⁸⁹ᵃᵇᶜᵈᵉᶠᵍʰᶦʲᵏˡᵐⁿᵒᵖᵠʳˢᵗᵘᵛʷˣʸᶻᴬᴮᶜᴰᴱᶠᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᵠᴿˢᵀᵁⱽᵂˣʸᶻ")
    return re.sub(r"\[\^(\w+)\^\]", lambda match: f" {match.group(1).translate(table)}", text)
    
    return pattern.sub(replace, text)
class SydMarkdown:
    @staticmethod
    def parse(text):
        text = parse_footnotes(text)
        text, languages = extract_code(text)
        index = 0
        text, entities = markdown.parse(text)
        for i, e in enumerate(entities):
            if isinstance(e, types.MessageEntityPre):
                if language := languages[index]:
                    entities[i] = types.MessageEntityPre(e.offset, e.length, language)
                index += 1
        return text, entities
    @staticmethod
    def unparse(text, entities):
        return markdown.unparse(text, entities)