import re
import sys

fin = sys.stdin
fout = sys.stdout
aout = open("a.out", "wt")
emdash = False
quotes = False
wordboundary = re.compile(r'\w+|\W|_')
a = None
astack = {}


# Flag processing
if '-h' in sys.argv:
    h = []
    h.append('-h                    Help')
    h.append('-i <inputfile>')
    h.append('-o <outputfile>')
    h.append('-e                    Process em dashes')
    h.append('-q                    Process quote marks (still needs manual intervention')
    h.append('-a <regex>            Regex to recognize line annotated')
    for l in h:
        print(l)
    sys.exit()
if '-i' in sys.argv:
    fin = open(sys.argv[sys.argv.index('-i')+1], 'rt')
if '-o' in sys.argv:
    fout = open(sys.argv[sys.argv.index('-o')+1], 'wt')
if '-e' in sys.argv:
    emdash = True
if '-q' in sys.argv:
    quotes = True
elif '-a' in sys.argv:
    a = re.compile(sys.argv[sys.argv.index('-a')+1])


us = False
doubleopen = False
br = False

for line in fin:
    newline = line
    if newline == '\n':
        doubleopen = False

    if a:
        if re.search(a, newline):
            matches = a.findall(newline)
            for m in matches:
                if m in astack:
                    amatch = astack.pop(m)
                    aout.write(f"{newline[len(m):-1].strip()}@{amatch}")
                    br = True
                    continue
                else:
                    newline = re.sub(a, r'', newline)
                    astack[m] = newline

    if br:
        br = False
        continue

    if emdash:
        newline = re.sub(r'(--)', r'—', newline) 

    if quotes:
        newline = re.sub(r"([^a-zA-Z])'([a-zA-Z—])", r"\1‘\2", newline)
        newline = re.sub(r"'", r"’", newline)

    words = re.findall(wordboundary, newline)

    for i, word in enumerate(words):
        if quotes and '"' in word:
            if doubleopen:
                words[i] = re.sub(r'"', r'”', words[i])
                doubleopen = False
            else:
                words[i] = re.sub(r'"', r'“', words[i])
                doubleopen = True

    newline = ''.join(words)

    fout.write(newline)

if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()

