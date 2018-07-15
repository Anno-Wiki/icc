import re
import sys

fin = sys.stdin
fout = sys.stdout
underscore = False
emdash = False
quotes = False


# Flag processing
if '-h' in sys.argv:
    h = []
    h.append('-h                    Help')
    h.append('-i <inputfile>')
    h.append('-o <outputfile>')
    h.append('-r <regex>            (does nothing yet)')
    h.append('-_                    Process underscores')
    h.append('-e                    Process em dashes')
    h.append('-_                    Process quote marks (still needs manual intervention')
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


def stamp(word, chnum):
    word = f'<ch id="ch{chnum}">{word}</ch>'
    return word


us = False

for line in fin:

    words = line.split()

    for i, word in enumerate(words):
        if emdash:
            # em dash
            words[i] = re.sub(r'(--)', '—', words[i]) 

        if quotes:
            # open single quote
            words[i] = re.sub(r"(^|\")'", r'\1‘', words[i])
            # close single quote
            words[i] = re.sub(r"'", '’', words[i])
            # open double quote
            words[i] = re.sub(r'^"', r'“', words[i])
            # close double quote
            words[i] = re.sub(r'"$', r'”', words[i])
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



    fout.write(' '.join(words) + '\n')

    

if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()

