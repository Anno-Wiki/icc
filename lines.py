import codecs
import re
import sys

book_id = None

if '-b' not in sys.argv:
    sys.exit('-b <book_id> flag required')
else:
    book_id = int(sys.argv[sys.argv.index('-b') + 1])


#########################
## Variables and flags ##
#########################

######################
# Global controllers #
######################

# Regex identifiers
bookregex = None                        # Regex - tagging Books
chapterregex = None                     # Regex - tag Chapters
partregex = None                        # Regex - tag Parts
hrregex = None                          # Regex - hr
pre = None                              # Regex - tag <pre>'s
stageregex = None                       # Regex - tagg Stage Directions

# Constant regexes
bible_book_regex = '(^(The Gospel According|The Lamentations|The Acts|The Revelation)|^(The Revelation|Ezra|The Proverbs|Ecclesiastes|The Song of Solomon|The Acts|Hosea|Joel|Obadiah|Jonah|Micah|Amos|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi)$|(Book|Epistle))'
bible_testament_regex = 'Testament'
ellreg = re.compile('[a-zA-Z]+[!,:;&?]?\.{3,5}[!,:;&?]?[a-zA-Z]+')
emreg = re.compile('[A-Za-z]+[.,;:!?&]?—[.,;:!?&]?[A-Za-z]+')
wordboundary = re.compile('\w+|\W')     # Word boundary break for split

# Flags
aggch = False                           # Flag - chnums across books and parts
aggpt = False                           # Flag - preserving ptnum across bks
debug = False                           # Flag - debugging
proc_ = False                           # Flag - process underscores
raggedright = False                     # Flag - raggedright
recordch = False                        # Flag - record chapter title
us = False                              # Flag - italicising lines

# Strings and numbers
filename = ''                           # File name for all output files
linesperpage = 30                       # Min ll before pgbrk (if !breakonp, max)
minchlines = 5                          # Min ll before chapter can pgbrk

# Files
fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')
fout = sys.stdout

# Help menu
def printhelp():
    h = []
    h.append(f'Usage: python {sys.argv[0]} -b <book_id> [options] [-i <input file>] [-o <output file>]')

    h.append('')
    h.append('Defaults to stdin and stdout. To specify an input or output file')
    h.append('use one or both of the following flags')
    h.append('-i <input file>')
    h.append('-o <output file>')

    h.append('')
    h.append('      Flags')
    h.append('-_                    Process underscores as italics')
    h.append('-b <book_id>          Book id (required)')
    h.append('-d                    Debug Mode')
    h.append('-h                    Help')
    h.append('-r                    Enable ragged right')

    h.append('')
    h.append('      Flags to prevent reset of ch and pt numbers in heierarchical')
    h.append('      text organization processing')
    h.append('--aggch               Aggregate chapters, do not reset')
    h.append('--aggpt               Aggregate parts, do not reset')

    
    h.append('')
    h.append('      Regexes for identifying subtitles')
    h.append('--bible               Enable bible chapter detection mode')
    h.append('--bk <regex>          Regex for Books (Heierarchical chapters lvl 1)')
    h.append('--pt <regex>          Regex for Parts (Heierarchical chapters lvl 2)')
    h.append('--ch <regex>          Regex for Chapters (Heierarchical Chapters lvl 3')
    h.append('--hr <regex>          Regex for horizontal rule breaks')
    h.append('--stg <regex>         Regex for Stage Directions')
    h.append('--pre <regex>         Enable pre on <regex>')

    for l in h:
        print(l)
    sys.exit()

# Input file override
if '-i' in sys.argv:
    fin = open(path, 'rt', encoding="UTF-8-SIG")
if '-o' in sys.argv:
    fout = open(path, 'wt', encoding="UTF-8-SIG")

# Flags
if '-_' in sys.argv:
    proc_ = True
if '-d' in sys.argv:
    debug = True
if '-h' in sys.argv:
    printhelp()
if '-r' in sys.argv:
    raggedright = True

# Aggregation flags
if '--aggch' in sys.argv:
    aggch = True
if '--aggpt' in sys.argv:
    aggpt = True

# Regex
if '--bible' in sys.argv:
    partregex = re.compile(bible_book_regex)
    bookregex = re.compile(bible_testament_regex)
if '--bk' in sys.argv:
    bookregex = re.compile(sys.argv[sys.argv.index('--bk')+1])
if '--pt' in sys.argv:
    partregex = re.compile(sys.argv[sys.argv.index('--pt')+1])
if '--ch' in sys.argv:
    chapterregex = re.compile(sys.argv[sys.argv.index('--ch')+1])
if '--hr' in sys.argv:
    hrregex = re.compile(sys.argv[sys.argv.index('--hr')+1])
if '--stg' in sys.argv:
    stageregex = re.compile(sys.argv[sys.argv.index('--stg')+1])
if '--pre' in sys.argv:
    preline = re.compile(sys.argv[sys.argv.index('--pre')+1])



###############
## Functions ##
###############

def stamp(word, wordcounter):
    if debug:
        return word
    if us:
        word = f'<word id="{wordcounter}"><i>{word}</i></word>'
    else:
        word = f'<word id="{wordcounter}">{word}</word>'
    return word

# Iterates through line calling the stamper
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
            words[j] = stamp(words[j], wordcount)

    line = ''.join(words)
    if preline:
        return f'<pre>\n{line}</pre>\n'
    else:
        return line

# Modularized page processor
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

# Line hash
def lhash():
    return f'p{page}l{linesonpage+1}'







#######################
## Initial file read ##
#######################

lines = [['beginning', 'beginning']] # Prepend initial value
i = 1   # Must index from one to avoid out of bounds for checking previous

# In order to accomplish contextual tagging 
# (i.e., based on previous and next lines) 
# we have to read the whole file into memory.
for inline in fin:
    # We replace underscores with bars for italics processing
    # because '\w+|\W' does not break on _
    line = re.sub('_', '|', inline)

    # Blank lines
    if re.match(r'^$', line):
        lines.append(['blank', 'blank'])

    # All special lines
    elif bookregex and re.search(bookregex, line):
        lines.append(['book', line])
    elif partregex and re.search(partregex, line):
        lines.append(['part', line])
    elif chapterregex and re.search(chapterregex, line):
        lines.append(['ch', line])
    elif stageregex and re.search(stageregex, line):
        lines.append(['stage', line])
    elif pre and re.search(pre, line):
        lines.append(['pre', line])
    elif hrregex and re.search(hrregex, line):
        lines.append(['hr', '<hr class="book_separator">'])
    
    # For everything else
    elif line != '':        # Possibly convert to `re.match` or `else`
        lines.append(['text', line])

    i += 1

lines.append(['last', 'last']) # Append a final value to avoid out of bounds








###################
## The Main Loop ##
###################


i = 1                           # Reset i to 1 to avoid first case of out of bounds
wordcount = 0                   # Keep track of words
textlines = 0                   # Count number of lines printed in toto

# Heierarchical chapter numbers
chnum = 0
ptnum = 0
bknum = 0


def lout(cls, l):
    fout.write(f'{book_id}@{textlines}@{cls}@{bknum}@{ptnum}@{chnum}@{l}')


for line in lines:

    # Necessary for last case to avoid out of bounds error
    if i >= len(lines):
        break

    # horizontal rule printer
    elif lines[i][0] == 'hr':
        # We only need to write it to the pages and to
        # files meant to be displayed in full
        textlines += 1
        lout('hr', '')

    # Handling for ch, includes writing of open/close paragraphs
    elif lines[i][0] == 'ch':
        chnum += 1
        textlines += 1
        lout('ch', lines[i][1])

    # Handling for part
    elif lines[i][0] == 'part':
        ptnum += 1
        textlines += 1
        if not aggch:
            chnum = 0
        lout('pt', lines[i][1])

    # Handling for book
    elif lines[i][0] == 'book':
        bknum += 1
        textlines += 1
        if not aggpt:
            ptnum = 0
        if not aggch:
            chnum = 0
        lout('bk', lines[i][1])

    # Handling for stage directions (if that's a thing)
    elif lines[i][0] == 'stage':
        textlines += 1
        lout('stg', lines[i][1])

    # Handling for pre lines
    elif lines[i][0] == 'pre':
        textlines += 1
        lout('pre', lines[i][1])
    
    # Handling for everything else
    elif lines[i][0] == 'text':
        textlines += 1

        if raggedright:

            # single line
            if lines[i+1][0] != 'text' and lines[i-1][0] != 'text':
                lout('rsl', lines[i][1])

            # last line in a p
            elif lines[i+1][0] != 'text':
                lout('rll', lines[i][1])

            # first line in a p
            elif lines[i-1][0] != 'text':
                lout('rfl', lines[i][1])

            # regular line in middle of a p
            else:
                lout('rl', lines[i][1])
                        
        else:
            # single line
            if lines[i+1][0] != 'text' and lines[i-1][0] != 'text':
                lout('sl', lines[i][1])

            # last line in a p
            elif lines[i+1][0] != 'text':
                lout('ll', lines[i][1])
                
            # first line in a p
            elif lines[i-1][0] != 'text':
                lout('fl', lines[i][1])

            # regular line in middle of a p
            else:
                lout('l', lines[i][1])

    i += 1


# cleanup
if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()
