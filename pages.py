import codecs
import re
import sys

# Global controllers
bookregex = None                        # Regex - tagging Books
breakonp = False                        # Flag - break on paragraphs
breaks = None                           # File for breaks info 
chconst = False                         # Flag - chnums across books and parts
chregex = None                          # Regex - tag Chapters
debug = False                           # Flag - debugging
fout = sys.stdout                       # Default to stdout
fullbook = None                         # Full book holder
hr_regex = None                         # Regex - hr
linesperpage = 30                       # Min ll before pgbrk (if !breakonp, max)
minchlines = 5                          # Min ll before chapter can pgbrk
partconst = False                       # Flag for preserving partnum across bks
partregex = None                        # Regex - tag Parts
pre = None                              # Regex - tag <pre>'s
proc_ = False                           # Process underscores
raggedright = False                     # Flag - raggedright
recordch = False                        # Record chapter title
stageregex = None                       # Regex - tagg Stage Directions
us = False                              # Flag - italicising lines
wordboundary = re.compile('\w+|\W')     # Word boundary break for split

# Default to stdin but make sure you ignore BOM
fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')

# Constants
bible_book_regex = '(^(The Gospel According|The Lamentations|The Acts|The Revelation)|^(The Revelation|Ezra|The Proverbs|Ecclesiastes|The Song of Solomon|The Acts|Hosea|Joel|Obadiah|Jonah|Micah|Amos|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi)$|(Book|Epistle))'
bible_testament_regex = 'Testament'
ellreg = re.compile('[a-zA-Z]+[!,:;&?]?\.{3,5}[!,:;&?]?[a-zA-Z]+')
emreg = re.compile('[A-Za-z]+[.,;:!?&]?—[.,;:!?&]?[A-Za-z]+')

# Flag processing
if '-h' in sys.argv:
    h = []
    h.append('-_                    Process underscores as italics')
    h.append('-b <regex>            Regex for Books (Heierarchical chapters lvl 1)')
    h.append('-c <regex>            Regex for Chapters (Heierarchical Chapters lvl 3')
    h.append('-d                    Debug Mode')
    h.append('-h                    Help')
    h.append('-i <inputfile>')
    h.append('-l <lines per page>   (Default = 30)')
    h.append('-m <min lines>        Minimum # of ll before chapter break (Default = 5)')
    h.append('-o <outputfile>')
    h.append('-p                    Break on p')
    h.append('-r                    Enable ragged right')
    h.append('-s <regex>            Regex for Stage Directions')
    h.append('--aggchapters         Aggregate chapters, do not reset')
    h.append('--aggparts            Aggregate parts, do not reset')
    h.append('--bible               Enable bible chapter detection mode')
    h.append('--breaks <outfile>    Write breaksdata to a breaks file')
    h.append('--fullbook <outfile>  Write the full book to a book file')
    h.append('--hr <regex>          Regex for horizontal rule breaks')
    h.append('--part <regex>        Regex for Parts (Heierarchical chapters lvl 2)')
    h.append('--pre <regex>         Enable pre on <regex>')
    h.append('--recordch            Record titles for chapters (e.g., if distinct)')
    for l in h:
        print(l)
    sys.exit()

if '-_' in sys.argv:
    proc_ = True
if '-b' in sys.argv:
    bookregex = re.compile(sys.argv[sys.argv.index('-b')+1])
if '-c' in sys.argv:
    chregex = re.compile(sys.argv[sys.argv.index('-c')+1])
if '-d' in sys.argv:
    debug = True
if '-i' in sys.argv:
    fin = open(path, 'rt', encoding="UTF-8-SIG")
if '-l' in sys.argv:
    linesperpage = int(sys.argv[sys.argv.index('-l')+1])
if '-m' in sys.argv:
    minchlines = int(sys.argv[sys.argv.index('-m')+1])
if '-o' in sys.argv:
    fout = open(sys.argv[sys.argv.index('-o')+1], 'wt')
if '-p'in sys.argv:
    breakonp = True
if '-r' in sys.argv:
    raggedright = True
if '-s' in sys.argv:
    stageregex = re.compile(sys.argv[sys.argv.index('-s')+1])
if '--aggchapters' in sys.argv:
    chconst = True
if '--aggparts' in sys.argv:
    partconst = True
if '--bible' in sys.argv:
    partregex = re.compile(bible_book_regex)
    bookregex = re.compile(bible_testament_regex)
if '--breaks' in sys.argv:
    breaks = open(sys.argv[sys.argv.index('--breaks')+1], 'wt')
if '--fullbook' in sys.argv:
    fullbook = open(sys.argv[sys.argv.index('--fullbook')+1], 'wt')
if '--hr' in sys.argv:
    hr_regex = re.compile(sys.argv[sys.argv.index('--hr')+1])
if '--part' in sys.argv:
    partregex = re.compile(sys.argv[sys.argv.index('--part')+1])
if '--pre' in sys.argv:
    pre = re.compile(sys.argv[sys.argv.index('--pre')+1])
if '--recordch' in sys.argv:
    recordch = True


lines = [['beginning', 'beginning']] # Prepend initial value
i = 1   # Must index from one to avoid out of bounds for checking previous

# In order to accomplish contextual tagging (i.e., based on previous and next
# lines) we have to read the whole file into memory.
for inline in fin:
    line = re.sub('_', '|', inline)

    # Blank lines
    if re.match(r'^$', line):
        lines.append(['blank', 'blank'])

    # All special lines
    elif bookregex and re.search(bookregex, line):
        lines.append(['book', line])
    elif partregex and re.search(partregex, line):
        lines.append(['part', line])
    elif chregex and re.search(chregex, line):
        lines.append(['ch', line])
    elif stageregex and re.search(stageregex, line):
        lines.append(['stage', line])
    elif pre and re.search(pre, line):
        lines.append(['pre', line])
    elif hr_regex and re.search(hr_regex, line):
        lines.append(['hr', '<hr class="book_separator">'])
    
    # For everything else
    elif line != '':        # Possibly convert to `re.match` or `else`
        lines.append(['text', line])
    i += 1
    

# Stamper for words
def stamp(word, wordcounter):
    if debug:
        return word
    if us:
        word = f'<word id="{wordcounter}"><i>{word}</i></word>'
    else:
        word = f'<word id="{wordcounter}">{word}</word>'
    return word

def stampline(line, preline):
    global wordcount
    global us
    words = re.findall(wordboundary, line)
    for j, word in enumerate(words):
        if '|' in word:
            words[j] = ''
            us = not us
        if '\n' not in word:
            wordcount += 1
            words[j] = stamp(word, wordcount)
    line = ''.join(words)
    if preline:
        return f'<pre>\n{line}</pre>\n'
    else:
        return line

def procpage():
    global page
    global linesonpage
    page += 1
    linesonpage = 0
    if popen:
        fout.write('\n</paragraph>\n')
    fout.write(f'@{page}{{}}')
    if popen:
        fout.write('\n<paragraph>\n')


lines.append(['last', 'last'])
i = 1                           # Reset i to 1 to avoid first case of out of bounds
wordcount = 0                   # Keep track of words
textlines = 0                   # Count number of lines printed in toto
linesonpage = 0                 # Keep track of lines per page
page = 0                        # Keep track of page number
popen = False                   # paragraph open flag

# Heierarchical chapter numbers
chnum = 0
partnum = 0
booknum = 0


for line in lines:

    # Necessary for last case to avoid out of bounds error
    if i >= len(lines):
        break


    # Blank lines should be preserved, and handling for breakonp
    elif lines[i][0] == 'blank':
        fout.write('\n\n')
        # Breakonp
        if linesonpage >= linesperpage and breakonp and lines[i+1][0] != 'stage':
            procpage()


    elif lines[i][0] == 'hr':
        fout.write('<hr class="bookseparator">')


    # Handling for ch, includes writing of open/close paragraphs
    elif lines[i][0] == 'ch':
        chnum += 1
        if linesonpage >= minchlines:
            procpage()
        if breaks:
            if recordch:
                breaks.write(f'{booknum}@{partnum}@{chnum}@{page + 1}@{lines[i][1]}')
            else:
                breaks.write(f'{booknum}@{partnum}@{chnum}@{page + 1}\n')
        textlines += 1
        fout.write(f'<ch>{stampline(lines[i][1], preline = False)}</ch>',)
        if fullbook:
            fullbook.write(f'<ch>\n{stampline(lines[i][1], preline = False)}</ch>',)
        linesonpage += 1


    # Handling for part
    elif lines[i][0] == 'part':
        partnum += 1
        if not chconst:
            chnum = 0
        if linesonpage >= minchlines:
            procpage()
        if breaks:
            if recordch:
                breaks.write(f'{booknum}@{partnum}@0@{page + 1}@{lines[i][1]}')
            else:
                breaks.write(f'{booknum}@{partnum}@0@{page + 1}\n')
        textlines += 1
        fout.write(f'<part>{stampline(lines[i][1], preline = False)}</part>')
        if fullbook:
            fullbook.write(f'<part>\n{stampline(lines[i][1], preline = False)}</part>')
        linesonpage += 1


    # Handling for book
    elif lines[i][0] == 'book':
        booknum += 1
        if not partconst:
            partnum = 0
        if not chconst:
            chnum = 0
        if linesonpage >= minchlines:
            procpage()
        if breaks:
            if recordch:
                breaks.write(f'{booknum}@0@0@{page + 1}@{lines[i][1]}')
            else:
                breaks.write(f'{booknum}@0@0@{page + 1}\n')
        textlines += 1
        fout.write(f'<book>{stampline(lines[i][1], preline = False)}</book>')
        if fullbook:
            fullbook.write(f'<book>\n{stampline(lines[i][1], preline = False)}</book>')
        linesonpage += 1

    
    # Handling for stage directions (if that's a thing)
    elif lines[i][0] == 'stage':
        textlines += 1
        fout.write(f'<stage>{stampline(lines[i][1], preline = False)}</stage>')
        if fullbook:
            fullbook.write(f'<stage>\n{stampline(lines[i][1], preline = False)}</stage>')
        linesonpage += 1

    elif lines[i][0] == 'pre':
        lines[i][1] = stampline(lines[i][1], preline = True)
        textlines += 1
        fout.write(lines[i][1])
        if fullbook:
            fullbook.write(lines[i][1])
        linesonpage += 1
    

    # Handling for everything else
    elif lines[i][0] == 'text' or lines[i][0] == 'pre':

        # Stamp the line
        lines[i][1] = stampline(lines[i][1], preline = False)

        # Really long multi-branch statement. This provides two four-way
        # branches, the first to handle ragged right, the second to handle
        # normal justify cases. The inner parts of the branches are broken out in
        # the following way:
        # branch 1: a single line paragraph case, to handle indent and justify
        # branch 2: the last line of a paragraph
        # branch 3: the first line of a paragraph
        # branch 4: a normal line
        if raggedright:
            # single line
            if lines[i+1][0] != 'text' and lines[i-1][0] != 'text':
                if fullbook:
                    fullbook.write('\n<paragraph class="raggedright">\n')
                    fullbook.write(lines[i][1])
                    fullbook.write('</paragraph>\n')
                fout.write('\n<paragraph class="raggedright">\n')
                fout.write(f'<line class="rrsingleline">\n{lines[i][1]}</line>\n')
                fout.write('</paragraph>\n')
            # last line in a p
            elif lines[i+1][0] != 'text':
                if fullbook:
                    fullbook.write(lines[i][1])
                    fullbook.write('</paragraph>\n')
                fout.write(f'<line class="rrlastline">\n{lines[i][1]}</line>\n')
                fout.write('</paragraph>\n')
                popen = False
            # first line in a p
            elif lines[i-1][0] != 'text':
                if fullbook:
                    fullbook.write(f'\n<paragraph class="raggedright">\n')
                    fullbook.write(lines[i][1])
                fout.write(f'\n<paragraph class="raggedright">\n')
                fout.write(f'<line class="rrfirstline">\n{lines[i][1]}</line>\n')
                popen = True
            # regular line in middle of a p
            else:
                if fullbook:
                    fullbook.write(f'{lines[i][1]}')
                fout.write(f'<line class="rrline">\n{lines[i][1]}</line>\n')

        else:
            # single line
            if lines[i+1][0] != 'text' and lines[i-1][0] != 'text':
                if fullbook:
                    fullbook.write('\n<paragraph class="justified">\n')
                    fullbook.write(lines[i][1])
                    fullbook.write('</paragraph>\n')
                fout.write('\n<paragraph class="justified">\n')
                fout.write(f'<line class="singleline">\n{lines[i][1]}</line>\n')
                fout.write('</paragraph>\n')
            # last line in a p
            elif lines[i+1][0] != 'text':
                if fullbook:
                    fullbook.write(lines[i][1])
                    fullbook.write('</paragraph>\n')
                fout.write(f'<line class="lastline">\n{lines[i][1]}</line>\n')
                fout.write('</paragraph>\n')
                popen = False
            # first line in a p
            elif lines[i-1][0] != 'text':
                if fullbook:
                    fullbook.write('\n<paragraph class="justified">\n')
                    fullbook.write(lines[i][1])
                fout.write('\n<paragraph class="justified">\n')
                fout.write(f'<line class="firstline">\n{lines[i][1]}</line>\n')
                popen = True
            # regular line
            else:
                fout.write(f'<line class="line">\n{lines[i][1]}</line>\n')
                if fullbook:
                    fullbook.write(lines[i][1])

        textlines += 1
        linesonpage += 1

    if linesonpage >= linesperpage and not breakonp:
        procpage()

    i += 1

page += 1
fout.write(f'\n@{page}\n')

page = 0

# cleanup
if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()
if breaks:
    breaks.close()
