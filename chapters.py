import re
import sys

fin = sys.stdin
fout = sys.stdout
linepreservation = False
chnum =1
bible_regex = '(^(The Gospel According|The Revelation|Ezra|The Proverbs|Ecclesiastes|The Song of Solomon|The Lamentations|The Acts|Hosea|Joel|Obadiah|Jonah|Micah|Amos|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi)|(Book|Epistle))'


# Flag processing
if '-h' in sys.argv:
    h = []
    h.append('-h                                            Help')
    h.append('-i <inputfile>')
    h.append('-o <outputfile>')
    h.append('-c <regex to match chapter>')
    h.append('-d <regex to match stage direction>>')
    h.append('--bible                                       Bible mode')
    for l in h:
        print(l)
    sys.exit()
if '-i' in sys.argv:
    fin = open(sys.argv[sys.argv.index('-i')+1], 'rt')
if '-o' in sys.argv:
    fout = open(sys.argv[sys.argv.index('-o')+1], 'wt')
if '-c' in sys.argv:
    regex = re.compile(sys.argv[sys.argv.index('-c')+1])
if '--bible' in sys.argv:
    regex = re.compile(bible_regex)
if '-d' in sys.argv:
    stagereg = re.compile(sys.argv[sys.argv.index('-d')+1])


def stamp(word, st, chnum):
    if st == 'chapter':
        word = f'<ch id="ch{chnum}">{word}</ch>'
    elif st == 'stage':
        word = f'<stage>{word}</stage>'
    return word



for line in fin:

    if re.search(regex, line):
        fout.write(f'{stamp(line[:-1], "chapter", chnum)}\n')
        chnum +=1
    elif re.search(stagereg, line):
        fout.write(f'{stamp(line[:-1], "stage", 0)}\n')
    else:
        fout.write(line)

    

if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()

