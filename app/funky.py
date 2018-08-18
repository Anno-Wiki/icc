# The line has is dangling with an open <em>, close it.
def opened(line):
    if line.count('<em>') > line.count('</em>'):
        return True
    else:
        return False

# The line has an extra close tag, open it.
def closed(line):
    if line.count('</em>') > line.count('<em>'):
        return True
    else:
        return False

# This method is used to run through all the lines for a read view and convert
# prep them to be shown: it (a) adds the annotations as [n] superscript links
# and (b) converts underscores to <em>/</em> tags. This method will probably
# need to be modified once I implement the dual line representation model that
# stores <em>/</em> versions of the line to expand display capability.
def preplines(lines, annos):
    us = False
    lem = False

    for i, line in enumerate(lines):

        if line.id in annos:
            for a in annos[line.id]:
                a.anno_id = a.id

                if a.first_char_idx == 0 and a.last_char_idx == -1:
                    lines[i].line = lines[i].line + \
                        f'<sup class="anno"><a href="#a{a.id}">[{a.anno_id}]</a></sup>' 
                else:
                    lines[i].line = lines[i].line[:a.last_char_idx] + \
                        f'<sup class="anno"><a href="#a{a.id}">'\
                        f'[{a.anno_id}]</a></sup>' + \
                        lines[i].line[a.last_char_idx:]

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
        
        if opened(lines[i].line):
            lines[i].line = lines[i].line + '</em>'
            lem = True
        elif closed(lines[i].line):
            lines[i].line = '<em>' + lines[i].line
            lem = False
        elif lem:
            lines[i].line = '<em>' + lines[i].line + '</em>'
