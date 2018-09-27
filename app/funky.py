from app import app, db
from app.models import Tag

# This method is used to run through all the lines for a read view and convert/
# prep them to be shown: (a) converts underscores to <em>/</em> tags, and (b)
# opens and closes surrounding <em></em> tags on lines that need it so that the
# tags don's span multiple levels in the DOM and throw everything into a tizzy.
# It also allows me to display an arbitrary number of lines perfectly.
def preplines(lines):
    us = False

    for i, line in enumerate(lines):

        if '_' in lines[i].line:
            newline = []
            for c in lines[i].line:
                if c == '_':
                    if us:
                        newline.append('</em>')
                        us = False
                    else:
                        newline.append('<em>')
                        us = True
                else:
                    newline.append(c)
            lines[i].line = ''.join(newline)

        if line.em_status.kind == 'oem':
            lines[i].line = lines[i].line + '</em>'
        elif line.em_status.kind == 'cem':
            lines[i].line = '<em>' + lines[i].line
        elif line.em_status.kind == 'em':
            lines[i].line = '<em>' + lines[i].line + '</em>'
