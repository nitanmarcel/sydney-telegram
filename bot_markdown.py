from telethon.extensions import markdown
from telethon import types
import re

def extract_code(text):
    md_languages = ['actionscript3', 'apache', 'applescript', 'asp', 'brainfuck', 'c', 'cfm', 'clojure', 'cmake', 'coffee-script', 'coffeescript', 'coffee', 'cpp', 'c++', 'cs', 'csharp', 'css', 'csv', 'bash', 'diff', 'elixir', 'erb', 'html', 'embedded', 'ruby', 'go', 'haml', 'http', 'java', 'javascript', 'json', 'jsx', 'less', 'lolcode', 'make', 'makefile', 'markdown', 'matlab', 'nginx', 'objectivec', 'pascal', 'php', 'perl', 'python', 'profile', 'python', 'profiler', 'output', 'rust', 'salt', 'saltstate', 'salt', 'shell', 'sh', 'zsh', 'bash', 'shell', 'scripting', 'scss', 'sql', 'svg', 'swift', 'rb', 'jruby', 'ruby', 'ruby', 'smalltalk', 'vim', 'viml', 'vim', 'script', 'volt', 'vhdl', 'vue', 'xml', 'xml', 'and', 'also', 'used', 'for', 'html', 'with', 'inline', 'css', 'and', 'javascript', 'yaml']
    pattern = r'```([\w+#]*)\n(.+?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    languages = []
    for match in matches:
        language = match[0]
        code = match[1]
        if language.lower() in md_languages:
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