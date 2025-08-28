from yattag import indent

import markdown
from markdown import Extension
from markdown.preprocessors import Preprocessor
from markdown.treeprocessors import Treeprocessor

import pdfkit

import re
import os

class ResumePreprocessor(Preprocessor):
    def run(self, lines):
        new_lines = []
        ended_header = False
        for line in lines:
            # sections
            if line.startswith('# '):
                new_lines.append('<header markdown="block">')
                new_lines.append(line)
            elif line.startswith('## '):
                if ended_header: new_lines.append('</section>')
                else: new_lines.append('</header>')
                ended_header = True

                html_class = re.match('\\s*##\\s*([A-Za-z]+)', line).group(1)
                html_class = html_class.lower()
                html_class = html_class.replace('\\s', '-')

                new_lines.append(f'<section class="{html_class}" markdown="block">')
                new_lines.append(line)
            # titles
            elif '&#124;' in line:
                html_class = 'title' if line.startswith('**') else 'sub-title'
                groups = line.split('&#124;')
                new_lines.append(f'<figure class="{html_class}" markdown="block">')
                new_lines.append(groups[0])
                new_lines.append(' ')
                new_lines.append(groups[1])
                new_lines.append('</figure>')
            else: 
                new_lines.append(line)

        return new_lines

class ResumeExtension(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(ResumePreprocessor(), 'resume-pre', 9999)

prelude = '''
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <title>Resume</title>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap" rel="stylesheet">

    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/gh/bitmaks/cm-web-fonts@latest/fonts.css">

    <link rel="stylesheet" href="./css/normalize.css">
    <link rel="stylesheet" href="./css/style.css">
    
</head>

<body>
    <div class="container">'''

conclusion = '''
    </div>
</body>

</html>'''


if __name__ == '__main__':
    print('Reading markdown')
    with open('resume.md', 'r') as f:
        text = f.read()
        html = prelude
        html += markdown.markdown(text, extensions=['toc', 'md_in_html', ResumeExtension()])
        html += conclusion

    print('Writing html')
    with open('resume.html', 'w') as f:
        html = indent(
            html,
            indentation = '    ',
            newline = '\r\n',
            indent_text = True
        )
        f.write(html)

    print('Writing pdf')
    pdf_options = {
        'margin-top': '0',
        'margin-right': '0',
        'margin-bottom': '0',
        'margin-left': '0',
        'page-size' : 'Letter',
        'enable-local-file-access': True
    }
    pdfkit.from_file("resume.html", "resume.pdf", verbose=True, options=pdf_options)
    
