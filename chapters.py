import re
import sys

fin = sys.stdin
fout = sys.stdout
linepreservation = False
chnum =1


# Flag processing
if '-h' in sys.argv:
    h = []
    h.append('-h                        Help')
    h.append('-i <inputfile>')
    h.append('-o <outputfile>')
    h.append('-r <regex to match chapter>')
    for l in h:
        print(l)
    sys.exit()
if '-i' in sys.argv:
    fin = open(sys.argv[sys.argv.index('-i')+1], 'rt')
if '-o' in sys.argv:
    fout = open(sys.argv[sys.argv.index('-o')+1], 'wt')
if not '-r' in sys.argv:
    sys.exit('Need regex to compile')
else:
    regex = re.compile(sys.argv[sys.argv.index('-r')+1])


def stamp(word, chnum):
    word = f'<ch id="ch{chnum}">{word}</ch>'
    return word



for line in fin:

    if re.match(regex, line):
        fout.write(f'{stamp(line[:-1], chnum)}\n')
        chnum +=1
    else:
        fout.write(line)

    

if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()

