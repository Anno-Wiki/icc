# The simplest version thus far, parses chapters and words and not even very
# well.
import sys
import re

punct = re.compile('[:punct:]')
with open(sys.argv[1], 'rt') as fin, open(sys.argv[2], 'wt') as fout:
    newline = 0
    chapter = False
    chapterdone = False
    for line in fin:
        if line == '\n' and newline == 2:
            chapter = True
            newline += 1
        elif chapter == True:
            fout.write('<ch>' + line[:-1] + '</ch>\n')
            chapter = False
            newline += 1
        elif line == '\n':
            newline += 1
            continue
        else:
            if newline > 0:
                fout.write('<p>\n')
                newline = 0
            words = line.split()
            for word in words:
                fout.write(word + '\n')
