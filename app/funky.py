from app import app, db
from app.models import Tag
# This method is used to run through all the lines for a read view and convert/
# prep them to be shown: it (a) adds the annotations as [n] superscript links,
# (b) converts underscores to <em>/</em> tags, and (c) opens and closes
# surrounding <em></em> tags on lines that need it so that the tags don's span
# multiple levels in the DOM and throw everything into a tizzy. It also allows
# me to display an arbitrary number of lines perfectly.
def preplines(lines, annos):
    us = False

    for i, line in enumerate(lines):

        if line.l_num in annos:
            for a in annos[line.l_num]:
                a.HEAD.anno_id = a.id

                if a.HEAD.first_char_idx == 0 and a.HEAD.last_char_idx == -1:
                    lines[i].line = lines[i].line + \
                        f'<sup class="anno"><a href="#a{a.id}">[{a.HEAD.anno_id}]</a></sup>' 
                else:
                    lines[i].line = lines[i].line[:a.HEAD.last_char_idx] + \
                        f'<sup class="anno"><a href="#a{a.HEAD.id}">'\
                        f'[{a.HEAD.anno_id}]</a></sup>' + \
                        lines[i].line[a.HEAD.last_char_idx:]

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

def is_empty(data):
   if data == None:
      return True
   if data == '':
      return True
   if data == []:
      return True
   return False

def proc_tag(tag):
    t = Tag.query.filter_by(tag = tag).first()
    if is_empty(t):
        t = Tag(tag = tag)
        db.session.add(t)
        db.session.commit()
        t = Tag.query.filter_by(tag = t.tag).first()
    return t

