import re
import sys

fin = sys.stdin
fout = sys.stdout
linepreservation = False
wordcounter = 0;
linesperpage = 30
linesonpage = 0
last = 'beginning'
minchlines = 0
breakonp = False

# Flag processing
if '-h' in sys.argv:
    h = []
    h.append('-h                                            Help')
    h.append('-i <inputfile>')
    h.append('-o <outputfile>')
    h.append('-pl                                           Activate line preservation')
    h.append('-l <lines per page>                           (Default = 30)')
    h.append('-m <min lines before new page for ch>         (Default = 0')
    h.append('-bp                                           Break on p')
    for l in h:
        print(l)
    sys.exit()
if '-i' in sys.argv:
    fin = open(sys.argv[sys.argv.index('-i')+1], 'rt')
if '-o' in sys.argv:
    fout = open(sys.argv[sys.argv.index('-o')+1], 'wt')
if '-pl' in sys.argv:
    linepreservation = True
if '-l' in sys.argv:
    linesperpage = int(sys.argv[sys.argv.index('-l')+1])
if '-m' in sys.argv:
    minchlines = int(sys.argv[sys.argv.index('-m')+1])
if '-bp'in sys.argv:
    breakonp = True



def stamp(word, wordcounter):
    # em dash
    word = re.sub(r'(--|—)', '&mdash;', word) 
    word = f'<word id="{wordcounter}">{word}</word>'
    return word

linecounter = 0
page = 1

for line in fin:

    if re.match(r'^$', line):
        if last == 'ch':
            fout.write('\n<p>\n')
            last = 'p'
        elif last == 'text':
            fout.write('\n</p>\n')
            last = '/p'
            if breakonp and linesonpage >= linesperpage and last != 'beginning':
                fout.write(f'\n@{page}{{}}\n')
                linesonpage = 0
                page += 1
    elif '<ch' in line:
        if last != 'beginning' and linesonpage >= minchlines:
            fout.write(f'\n@{page}{{}}\n')
            linesonpage = 0
            page += 1
        fout.write(line + '\n')
        linesonpage += 1
        last = 'ch'
    elif line != '':
        if last == '/p':
            fout.write('\n<p>\n')
        words = line.split()
        newline = []
        for word in words:
            wordcounter += 1
            word = stamp(word, wordcounter)
            newline.append(word)
        newline = ' '.join(newline)
        fout.write(newline + '\n')
        if linepreservation:
            fout.write('\n<br>\n')
        linecounter += 1
        linesonpage += 1
        last = 'text'

        if not breakonp and linesonpage >= linesperpage and last != 'beginning':
            fout.write(f'\n@{page}{{}}\n')
            linesonpage = 0
            page += 1

fout.write(f'@{page}{{}}')

if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()

