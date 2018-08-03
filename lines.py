import codecs
import re
import sys

book_id = None


#########################
## Variables and flags ##
#########################

######################
# Global controllers #
######################

# Regex identifiers
bkreg = None        # Regex - tagging Books
chreg = None        # Regex - tag Chapters
ptreg = None        # Regex - tag Parts
hrreg = None        # Regex - hr
prereg = None       # Regex - tag <pre>'s
stgreg = None       # Regex - tagg Stage Directions

# Constant regexes
bible_book_regex = '(^(The Gospel According|The Lamentations|The Acts|The Revelation)|^(The Revelation|Ezra|The Proverbs|Ecclesiastes|The Song of Solomon|The Acts|Hosea|Joel|Obadiah|Jonah|Micah|Amos|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi)$|(Book|Epistle))'
bible_testament_regex = 'Testament'
ellreg = re.compile('[a-zA-Z]+[!,:;&?]?\.{3,5}[!,:;&?]?[a-zA-Z]+')
emreg = re.compile('[A-Za-z]+[.,;:!?&]?—[.,;:!?&]?[A-Za-z]+')
wordboundary = re.compile('\w+|\W')     # Word boundary break for split

# Flags
aggch = False                           # Flag - chnums across books and parts
aggpt = False                           # Flag - preserving ptnum across bks
proc_ = False                           # Flag - process underscores
raggedright = False                     # Flag - raggedright

# Files
fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')
fout = sys.stdout

# Help menu
def printhelp():
    h = []
    h.append(f'Usage: python {sys.argv[0]} -b <book_id> [options] [-i <input file>] [-o <output file>]')
    h.append(f'The output is formatted as @ separated values of the order:')
    h.append(f'book_id   l_num   l_class   bk_num   pt_num   ch_num   line')

    h.append('')
    h.append('Defaults to stdin and stdout. To specify an input or output file')
    h.append('use one or both of the following flags')
    h.append('-i <input file>')
    h.append('-o <output file>')

    h.append('')
    h.append('      Flags')
    h.append('-_                    Process underscores as italics')
    h.append('-b <book_id>          Book id *required*')
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
    h.append('--ch <regex>          Regex for Chapters (Heierarchical Chapters lvl 3)')
    h.append('--hr <regex>          Regex for horizontal rule breaks')
    h.append('--stg <regex>         Regex for Stage Directions')
    h.append('--pre <regex>         Regex for pre lines')

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
    ptreg = re.compile(bible_book_regex)
    bkreg = re.compile(bible_testament_regex)
if '--bk' in sys.argv:
    bkreg = re.compile(sys.argv[sys.argv.index('--bk')+1])
if '--pt' in sys.argv:
    ptreg = re.compile(sys.argv[sys.argv.index('--pt')+1])
if '--ch' in sys.argv:
    chreg = re.compile(sys.argv[sys.argv.index('--ch')+1])
if '--hr' in sys.argv:
    hrreg = re.compile(sys.argv[sys.argv.index('--hr')+1])
if '--stg' in sys.argv:
    stgreg = re.compile(sys.argv[sys.argv.index('--stg')+1])
if '--pre' in sys.argv:
    prereg = re.compile(sys.argv[sys.argv.index('--pre')+1])

if '-b' not in sys.argv:
    sys.exit('-b <book_id> flag required')
else:
    book_id = int(sys.argv[sys.argv.index('-b') + 1])


###############
## Functions ##
###############

def lout(cls, l):
    fout.write(f'{book_id}@{txtlines}@{cls}@{bknum}@{ptnum}@{chnum}@{l}')


#######################
## Initial file read ##
#######################

lines = [['beginning', 'beginning']] # Prepend initial value
i = 1   # Must index from one to avoid out of bounds for checking previous

# In order to accomplish contextual tagging (i.e., based on previous 
# and next lines) we have to read the whole file into memory.
for line in fin:

    # Blank lines
    if re.match(r'^$', line):
        lines.append(['blank', 'blank'])

    # All special lines
    elif bkreg and re.search(bkreg, line):
        lines.append(['book', line])
    elif ptreg and re.search(ptreg, line):
        lines.append(['part', line])
    elif chreg and re.search(chreg, line):
        lines.append(['ch', line])
    elif stgreg and re.search(stgreg, line):
        lines.append(['stage', line])
    elif prereg and re.search(prereg, line):
        lines.append(['pre', line])
    elif hrreg and re.search(hrreg, line):
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
txtlines = 0                   # Count number of lines printed in toto

# Heierarchical chapter numbers
chnum = 0
ptnum = 0
bknum = 0



for line in lines:

    # Necessary for last case to avoid out of bounds error
    if i >= len(lines):
        break

    # horizontal rule printer
    elif lines[i][0] == 'hr':
        # We only need to write it to the pages and to
        # files meant to be displayed in full
        txtlines += 1
        lout('hr', '')

    # Handling for ch, includes writing of open/close paragraphs
    elif lines[i][0] == 'ch':
        chnum += 1
        txtlines += 1
        lout('ch', lines[i][1])

    # Handling for part
    elif lines[i][0] == 'part':
        ptnum += 1
        txtlines += 1
        if not aggch:
            chnum = 0
        lout('pt', lines[i][1])

    # Handling for book
    elif lines[i][0] == 'book':
        bknum += 1
        txtlines += 1
        if not aggpt:
            ptnum = 0
        if not aggch:
            chnum = 0
        lout('bk', lines[i][1])

    # Handling for stage directions (if that's a thing)
    elif lines[i][0] == 'stage':
        txtlines += 1
        lout('stg', lines[i][1])

    # Handling for pre lines
    elif lines[i][0] == 'pre':
        txtlines += 1
        lout('pre', lines[i][1])
    
    # Handling for everything else
    elif lines[i][0] == 'text':
        txtlines += 1

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
