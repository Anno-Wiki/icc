import re
import sys

# Global controllers
fin = sys.stdin     # Default to stdin
fout = sys.stdout   # Default to stdout
linesperpage = 30   # Default min lines before pgbreak (if no breakonp then max)
minchlines = 0      # Minimum lines before a chapter can pagebreak
breakonp = False    # Flag for break on paragraphs
debug = False       # Flag for debugging
raggedright = False # Flag for default to ragged right (e.g. for poetry, etc)
emreg = re.compile('[A-Za-z]+[.,;:!?&]?—[.,;:!?&]?[A-Za-z]+')
ellreg = re.compile('[a-zA-Z]+[!,:;&?]?\.{3,5}[!,:;&?]?[a-zA-Z]+')

# Flag processing
if '-h' in sys.argv:
    h = []
    h.append('-h                                            Help')
    h.append('-i <inputfile>')
    h.append('-o <outputfile>')
    h.append('-l <lines per page>                           (Default = 30)')
    h.append('-m <min lines before new page for ch>         (Default = 0)')
    h.append('-p                                            Break on p')
    h.append('-r                                            Enable ragged right')
    h.append('-d                                            Debug Mode')
    for l in h:
        print(l)
    sys.exit()
if '-i' in sys.argv:
    fin = open(sys.argv[sys.argv.index('-i')+1], 'rt')
if '-o' in sys.argv:
    fout = open(sys.argv[sys.argv.index('-o')+1], 'wt')
if '-l' in sys.argv:
    linesperpage = int(sys.argv[sys.argv.index('-l')+1])
if '-m' in sys.argv:
    minchlines = int(sys.argv[sys.argv.index('-m')+1])
if '-p'in sys.argv:
    breakonp = True
if '-r' in sys.argv:
    raggedright = True
if '-d' in sys.argv:
    debug = True


# Stamper for words
def stamp(word, wordcounter):
    if not debug:
        word = f'<word id="{wordcounter}">{word}</word>'
    return word


lines = [['beginning', 'beginning']] # Prepend initial value
i = 1   # Must index from one to avoid out of bounds for checking previous
popen = False
for line in fin:

    # Blank lines
    if re.match(r'^$', line):
        if not popen:
            lines.append(['popen', '<div class="paragraph">'])
            popen = True
        else:
            lines.append(['pclose', '</div>'])
            popen = False

    # if it's a chapter line or stage line
    elif '<div class="chapter"' in line:
        lines.append(['ch', line])
    elif '<div class="stage"' in line:
        lines.append(['stage', line])
    
    # For everything else
    elif line != '':        # I may consider converting this to re.match or else
        if not popen:
            lines.append(['blank', '<div class="paragraph">'])
            popen = True
            i += 1
        lines.append(['text', line])
    i += 1
    


lines.append(['last', 'last'])
i = 1                           # Reset i to 0
textlines = 0                   # Count number of lines printed in toto
page = 0                        # Keep track of page number
wordcount = 0                   # Keep track of words
linesonpage = 0                 # Keep track of lines per page
popen = False                   # paragraph open flag
for line in lines:

    if i >= len(lines):
        break

    if lines[i][0] == 'popen':
        fout.write(lines[i][1])
        popen = True
    elif lines[i][0] == 'pclose':
        fout.write(lines[i][1])
        popen = False

        # Breakonp
        if breakonp and lines[i][0] == 'pclose' and linesonpage >= linesperpage:
            page += 1
            fout.write(f'@{page}{{}}')
            linesonpage = 0
            popen = False


    elif lines[i][0] == 'ch':
        if linesonpage >= minchlines:
            page += 1
            linesonpage = 0
            if popen:
                fout.write('</div>')
                fout.write(f'@{page}{{}}')
                fout.write('<div class="paragraph">')
            else:
                fout.write(f'@{page}{{}}')

        textlines += 1
        fout.write(lines[i][1])
        linesonpage += 1
    elif lines[i][0] == 'stage':
        textlines += 1
        fout.write(lines[i][1])
        linesonpage += 1

    elif lines[i][0] == 'text':

        words = lines[i][1].split()
        for j, word in enumerate(words):
                wordcount += 1
                words[j] = f'<word id="{wordcount}">{word}</word>'
        lines[i][1] = ' '.join(words)

        out = ''
        if raggedright:
            if lines[i+1][0] != 'text' and lines[i-1][0] != 'text':
                out = f'<div id="{textlines}" class="rrsingleline">{lines[i][1]}<br></div>\n'
            elif lines[i+1][0] != 'text':
                out = f'<div id="{textlines}" class="rrlastline">{lines[i][1]}<br></div>\n'
            elif lines[i-1][0] != 'text':
                out = f'<div id="{textlines}" class="rrfirstline">{lines[i][1]}<br></div>\n'
            else:
                out = f'<div id="{textlines}" class="rrline">{lines[i][1]}<br></div>\n'
        else:
            if lines[i+1][0] != 'text' and lines[i-1][0] != 'text':
                out = f'<div id="{textlines}" class="singleline">{lines[i][1]}<br></div>\n'
            elif lines[i+1][0] != 'text':
                out = f'<div id="{textlines}" class="lastline">{lines[i][1]}</div>\n'
            elif lines[i-1][0] != 'text':
                out = f'<div id="{textlines}" class="firstline">{lines[i][1]}</div>\n'
            else:
                out = f'<div id="{textlines}" class="line">{lines[i][1]}</div>\n'

        textlines += 1
        fout.write(out)
        linesonpage += 1

    if linesonpage >= linesperpage and not breakonp:
        page += 1
        linesonpage = 0
        if popen:
            fout.write('<div class="paragraph">')
            fout.write(f'@{page}{{}}')
            fout.write('</div>')
        else:
            fout.write(f'@{page}{{}}')

    i += 1

page += 1
fout.write(f'@{page}{{}}')




if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()
