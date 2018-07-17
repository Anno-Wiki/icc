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
for line in fin:

    # Blank lines
    if re.match(r'^$', line):
        if lines[i-1][0] == 'ch':
            lines.append(['blank', '<p>'])
        elif lines[i-1][0] == 'text':
            lines.append(['blank', '</p>'])

    # if it's a chapter line
    elif '<ch' in line:
        lines.append(['ch', line])
    
    # For everything else
    elif line != '':        # I may consider converting this to re.match or else
        if lines[i-1][0] == 'blank':
            lines.append(['blank', '<p>'])
        lines.append(['text', line])
    i += 1


lines.append(['last', 'last'])  # Have to append a last to avoid out of bounds
i = 1                           # Reset i to 0
textlines = 0                   # Count number of lines printed in toto
page = 0                        # Keep track of page number
wordcount = 0                   # Keep track of words
linesonpage = 0                 # Keep track of lines per page
for line in lines:

    if line[i][0] == 'blank':
        fout.write(line[i][1])

        # Breakonp
        if breakonp and line[i][1] == '</p>' and linesonpage >= linesperpage:
            page += 1
            fout.write(f'@{page}{{}}')
            linesonpage = 0


    elif line[i][0] == 'ch':
        if linesonpage >= minchlines:
            page += 1
            fout.write(f'@{page}{{}}')
            linesonpage = 0

        textlines += 1
        fout.write(line[i][1])
        linesonpage += 1


    elif line[i][0] == 'text':

        words = line[i][1].split()
        for j, word in enumerate(words):
                wordcount += 1
                words[j] = f'<word id="{wordcount}">{word}</word>'
        line[i][1] = ' '.join(words)

        out = ''
        if line[i+1][0] != 'text':
            out = f'<span id="{textlines}" class="lastline">{line[i][1]}</span>\n'
        else:
            out = f'<span id="{textlines}" class="line">{line[i][1]}</span>\n'

        if raggedright:
            out += '<br>\n'
        else:
            out += '<span class="break"></span>\n'

        textlines += 1
        fout.write(out)
        linesonpage += 1

    if linesonpage >= linesperpage:
        page += 1
        fout.write(f'@{page}{{}}')
        linesonpage = 0

    i += 1

page += 1
fout.write(f'@{page}{{}}')




if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()

