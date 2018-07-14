import re
import sys

fin = sys.stdin
fout = sys.stdout
linepreservation = False
wordcounter = 0;
linesperpage = 30
linesonpage = 0


# Flag processing
if '-i' in sys.argv:
    fin = open(sys.argv[sys.argv.index('-i')+1], 'rt')
if '-o' in sys.argv:
    fout = open(sys.argv[sys.argv.index('-o')+1], 'wt')
if '-p' in sys.argv:
    linepreservation = True
if '-l' in sys.argv:
    linesperpage = sys.argv[sys.argv.index('-l')+1]


def stamp(word, wordcounter):
    word = f'<word id="{wordcounter}">{word}</word>'
    return word

linecounter = 0
page = 1

for line in fin:

    if re.match(r'^$', line):
        fout.write('\n</p>\n<p>\n')
        continue

    if '<ch' in line:
        fout.write(f'@{page}{{}}')
        linesonpage = 0
        page += 1
        fout.write(line)
        continue
    else:
        words = line.split()
        newline = []
        for word in words:
            wordcounter += 1
            word = stamp(word, wordcounter)
            newline.append(word)
        newline = ' '.join(newline)
        fout.write(newline)
        if linepreservation:
            fout.write('<br>')
        linecounter += 1
        linesonpage += 1

    if linesonpage >= linesperpage:
        fout.write(f'@{page}{{}}')
        linesonpage = 0
        page += 1

fout.write(f'@{page}{{}}')

if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()

