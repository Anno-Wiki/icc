import re
import sys

fin = sys.stdin
fout = sys.stdout
underscore = False


# Flag processing
if '-i' in sys.argv:
    fin = open(sys.argv[sys.argv.index('-i')+1], 'rt')
if '-o' in sys.argv:
    fout = open(sys.argv[sys.argv.index('-o')+1], 'wt')
if '-r' in sys.argv:
    regex = re.compile(sys.argv[sys.argv.index('-r')+1])
if '-_' in sys.argv:
    underscore = True


def stamp(word, chnum):
    word = f'<ch id="ch{chnum}">{word}</ch>'
    return word


us = False

for line in fin:

    words = line.split()

    for i, word in enumerate(words):

        # underscore processing
        if underscore and '_' in word:
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

