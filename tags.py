import re
import sys

fin = sys.stdin
fout = sys.stdout
underscore = False
emdash = False
quotes = False
spacepreservation = False
wordboundary = re.compile(r'\w+|\W')


# Flag processing
if '-h' in sys.argv:
    h = []
    h.append('-h                    Help')
    h.append('-i <inputfile>')
    h.append('-o <outputfile>')
    h.append('-r <regex>            (does nothing yet)')
    h.append('-_                    Process underscores')
    h.append('-e                    Process em dashes')
    h.append('-q                    Process quote marks (still needs manual intervention')
    h.append('-s                    Space preservation')
    for l in h:
        print(l)
    sys.exit()
if '-i' in sys.argv:
    fin = open(sys.argv[sys.argv.index('-i')+1], 'rt')
if '-o' in sys.argv:
    fout = open(sys.argv[sys.argv.index('-o')+1], 'wt')
if '-r' in sys.argv:
    regex = re.compile(sys.argv[sys.argv.index('-r')+1])
if '-_' in sys.argv:
    underscore = True
if '-e' in sys.argv:
    emdash = True
if '-q' in sys.argv:
    quotes = True
if '-s' in sys.argv:
    spacepreservation = True


def stamp(word, chnum):
    word = f'<ch id="ch{chnum}">{word}</ch>'
    return word


us = False
doubleopen = False

for line in fin:
    newline = line
    if spacepreservation:
        newline = re.sub(r"^      ", r'&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;', newline)
        newline = re.sub(r"^     ", r'&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;', newline)
        newline = re.sub(r"^    ", r'&nbsp;&nbsp;&nbsp;&nbsp;', newline)
        newline = re.sub(r"^   ", r'&nbsp;&nbsp;&nbsp;', newline)
        newline = re.sub(r"^  ", r'&nbsp;&nbsp;', newline)
        newline = re.sub(r"^ ", r'&nbsp;', newline)

    if emdash:
        # em dash
        newline = re.sub(r'(--)', r'—', newline) 

    if quotes:
        re.sub(r"'([a-zA-Z—])", r"‘\1", newline)
        re.sub(r"([a-zA-Z—])'", r"\1’", newline)


    words = re.findall(wordboundary, newline)

    for i, word in enumerate(words):
        if quotes:
            if doubleopen:
                words[i] = re.sub(r'"', r'”', words[i])
                doubleopen = False
            else:
                words[i] = re.sub(r'"', r'“', words[i])
                doubleopen = True
        # underscore processing
        if underscore and '_' in words[i]:
            t = []
            for c in word:
                if c == '_' and us:
                    t.append('</i>')
                    us = False
                elif c == '_' and not us:
                    t.append('<i>')
                    us = True
                else:
                    t.append(c)
            words[i] = ''.join(t)
        words[i] = re.sub(r'&', r'&amp;', words[i])
    newline = ''.join(words)

    fout.write(newline)

    

if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()

