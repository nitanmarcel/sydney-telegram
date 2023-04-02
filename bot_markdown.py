from telethon.extensions import markdown
from telethon import types
import re

def extract_code(text):
    md_languages = ['actionscript3', 'apache', 'applescript', 'asp', 'brainfuck', 'c', 'cfm', 'clojure', 'cmake', 'coffee-script', 'coffeescript', 'coffee', 'cpp', 'C++', 'cs', 'csharp', 'css', 'csv', 'bash', 'diff', 'elixir', 'erb', 'HTML', 'Embedded', 'Ruby', 'go', 'haml', 'http', 'java', 'javascript', 'json', 'jsx', 'less', 'lolcode', 'make', 'Makefile', 'markdown', 'matlab', 'nginx', 'objectivec', 'pascal', 'PHP', 'Perl', 'python', 'profile', 'python', 'profiler', 'output', 'rust', 'salt', 'saltstate', 'Salt', 'shell', 'sh', 'zsh', 'bash', 'Shell', 'scripting', 'scss', 'sql', 'svg', 'swift', 'rb', 'jruby', 'ruby', 'Ruby', 'smalltalk', 'vim', 'viml', 'Vim', 'Script', 'volt', 'vhdl', 'vue', 'xml', 'XML', 'and', 'also', 'used', 'for', 'HTML', 'with', 'inline', 'CSS', 'and', 'Javascript', 'yaml']
    pattern = r'```([\w+#]*)\n(.+?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    languages = []
    for match in matches:
        language = match[0]
        code = match[1]
        if language in md_languages:
            code = code.replace(language, '', 1).lstrip()
            languages.append(language)
            text = text.replace(f'```{language}\n{code}```', f'```{code}```')
        else:
            languages.append('')
    pattern = r'```(.+?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    languages.extend('' for _ in matches)
    return text, languages

def parse_footnotes(text):
    table = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    return re.sub(r"\[\^(\d+)\^\]", lambda match: f" {match.group(1).translate(table)}", text)

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