import re
import sys

fin = sys.stdin
fout = sys.stdout
linepreservation = False
wordcounter = 0;
linesperpage = 30
linesonpage = 0
last = 'beginning'


# Flag processing
if '-i' in sys.argv:
    fin = open(sys.argv[sys.argv.index('-i')+1], 'rt')
if '-o' in sys.argv:
    fout = open(sys.argv[sys.argv.index('-o')+1], 'wt')
if '-p' in sys.argv:
    linepreservation = True
if '-l' in sys.argv:
    linesperpage = int(sys.argv[sys.argv.index('-l')+1])


def stamp(word, wordcounter):
    # em dash
    word = re.sub(r'(--|—)', '&mdash;', word) 
    # open single quote
    #word = re.sub(r"^'", '&lsquo;', word)
    ## close single quote
    #word = re.sub(r"'$", '&rsquo;', word)
    ## open double quote
    #word = re.sub(r'^"', '&ldquo;', word)
    ## close double quote
    #word = re.sub(r'"$', '&rdquo;', word)
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
    elif '<ch' in line:
        if last != 'beginning':
            fout.write(f'\n@{page}{{}}\n')
            linesonpage = 0
            page += 1
        fout.write(line + ' ')
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
        fout.write(newline + ' ')
        if linepreservation:
            fout.write('\n<br>\n')
        linecounter += 1
        linesonpage += 1
        last = 'text'

        if linesonpage >= linesperpage and last != 'beginning':
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

