import sys
from textlib import isword

with open(sys.argv[1], 'rt') as fin:

    pos = 1
    wordcount = 0
    pages = 1

    print('<page>@1@1')

    for line in fin:
        if isword(line):
            wordcount += 1
        

        if wordcount >= 500 and '<p>' in line:
            pages += 1
            print('<page>@'+str(pages)+'@'+str(pos))
        pos += 1 
