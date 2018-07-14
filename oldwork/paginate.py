import sys
from parselib import isword

with open(sys.argv[1], 'rt') as fin:

    pos = 0
    wordcount = 0
    prevpagepos = 0
    pages = 0
    chproc = False

    if '-b' not in sys.argv:
        sys.exit("Need book_id set by -b")

    if '-c' in sys.argv:
        cpos = sys.argv.index('-c')
        chproc = True

    bpos = sys.argv.index("-b")
    book_id = sys.argv[bpos+1]


    for line in fin:
        if isword(line):
            wordcount += 1
        

        if wordcount >= 500 and '<p>' in line: 
            pages += 1
            # order: identifier@ident_num@book_id@startpos@endpos@page_num
            print(f'<page>@0@{book_id}@{prevpagepos}@{pos-1}@{str(pages)}')
            prevpagepos = pos
            wordcount = 0

        if wordcount >= 650 and '<period>' in line:
            pages += 1
            # order: identifier@ident_num@book_id@startpos@endpos@page_num
            print(f'<page>@0@{book_id}@{prevpagepos}@{pos}@{str(pages)}')
            prevpagepos = pos + 1
            wordcount = 0

        if chproc and '<ch>' in line:
            ch = line[line.find('@')+1:-1]
            # order: identifier@ident_num@book_id@startpos@endpos@page_num
            print(f'<ch>@{ch}@{book_id}@0@0@{str(pages+1)}')


        pos += 1 

