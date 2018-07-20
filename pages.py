import re
import sys

# Global controllers
fin = sys.stdin     # Default to stdin
fout = sys.stdout   # Default to stdout
linesperpage = 30   # Default min lines before pgbreak (if no breakonp then max)
minchlines = 5      # Minimum lines before a chapter can pagebreak
breakonp = False    # Flag for break on paragraphs
debug = False       # Flag for debugging
raggedright = False # Flag for default to ragged right (e.g. for poetry, etc)
bookregex = None    # Regex for tagging Books
partregex = None    # Regex for tagging Parts
chregex = None      # Regex for tagging Chapters
stageregex = None   # Regex for tagging Stage Directions
meta = None         # File holder to which one should write meta information
recordch = False    # Record chapter title
wordboundary = re.compile('\w+|\W')          # Word boundary break for split
pre = None

# Constants
emreg = re.compile('[A-Za-z]+[.,;:!?&]?—[.,;:!?&]?[A-Za-z]+')
ellreg = re.compile('[a-zA-Z]+[!,:;&?]?\.{3,5}[!,:;&?]?[a-zA-Z]+')
bible_regex = '(^(The Gospel According|The Revelation|Ezra|The Proverbs|Ecclesiastes|The Song of Solomon|The Lamentations|The Acts|Hosea|Joel|Obadiah|Jonah|Micah|Amos|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi)|(Book|Epistle))'

# Flag processing
if '-h' in sys.argv:
    h = []
    h.append('-h                    Help')
    h.append('-i <inputfile>')
    h.append('-o <outputfile>')
    h.append('-meta <outfile>       Write metadata to a metafile')
    h.append('-l <lines per page>   (Default = 30)')
    h.append('-m <min lines>        Minimum # of ll before chapter break (Default = 5)')
    h.append('-b <regex>            Regex for Books (Heierarchical chapters lvl 1)')
    h.append('--part <regex>        Regex for Parts (Heierarchical chapters lvl 2)')
    h.append('-c <regex>            Regex for Chapters (Heierarchical Chapters lvl 3')
    h.append('-s <regex>            Regex for Stage Directions')
    h.append('--recordch            Record titles for chapters (e.g., if distinct')
    h.append('-p                    Break on p')
    h.append('--pre <regex>         Enable pre on <regex>')
    h.append('-r                    Enable ragged right')
    h.append('--bible               Enable bible chapter detection mode')
    h.append('-d                    Debug Mode')

    for l in h:
        print(l)
    sys.exit()
if '-i' in sys.argv:
    fin = open(sys.argv[sys.argv.index('-i')+1], 'rt')
if '-o' in sys.argv:
    fout = open(sys.argv[sys.argv.index('-o')+1], 'wt')
if '-l' in sys.argv:
    linesperpage = int(sys.argv[sys.argv.index('-l')+1])
if '-m' in sys.argv:
    minchlines = int(sys.argv[sys.argv.index('-m')+1])
if '-p'in sys.argv:
    breakonp = True
if '-r' in sys.argv:
    raggedright = True
if '-d' in sys.argv:
    debug = True
if '-c' in sys.argv:
    chregex = re.compile(sys.argv[sys.argv.index('-c')+1])
if '--bible' in sys.argv:
    chregex = re.compile(bible_regex)
if '-s' in sys.argv:
    stageregex = re.compile(sys.argv[sys.argv.index('-c')+1])
if '-b' in sys.argv:
    bookregex = re.compile(sys.argv[sys.argv.index('-b')+1])
if '--part' in sys.argv:
    partregex = re.compile(sys.argv[sys.argv.index('--part')+1])
if '--pre' in sys.argv:
    pre = re.compile(sys.argv[sys.argv.index('--pre')+1])
if '-meta' in sys.argv:
    meta = open(sys.argv[sys.argv.index('-meta')+1], 'wt')
if '--recordch' in sys.argv:
    recordch = True


lines = [['beginning', 'beginning']] # Prepend initial value
i = 1   # Must index from one to avoid out of bounds for checking previous

# In order to accomplish contextual tagging (i.e., based on previous and next
# lines) we have to read the whole file into memory.
for line in fin:

    # Blank lines
    if re.match(r'^$', line):
        lines.append(['blank', 'blank'])

    # if it's a heierarchical chapter line or stage line
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
    
    # For everything else
    elif line != '':        # I may consider converting this to re.match or else
        lines.append(['text', line])
    i += 1
    


# Stamper for words
def stamp(word, wordcounter):
    if not debug:
        word = f'<word id="{wordcounter}">{word}</word>'
    return word

# Wrapper for stamp
def stampline(line):
    global wordcount
    words = line.split()
    for j, word in enumerate(words):
        wordcount += 1
        words[j] = stamp(word, wordcount)
    line = ' '.join(words)
    return line

def stamppreline(line):
    global wordcount
    words = re.findall(wordboundary, line)
    for j, word in enumerate(words):
        if re.search('[A-Za-z]+', word):
            wordcount += 1
            words[j] = stamp(word, wordcount)
    line = ''.join(words)
    return f'<pre>{line}</pre>'



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
    if lines[i][0] == 'blank':
        fout.write('\n\n')
        # Breakonp
        if linesonpage >= linesperpage and breakonp and \
                lines[i][0] == 'blank' and lines[i+1][0] != 'stage':
            page += 1
            fout.write(f'@{page}{{}}')
            linesonpage = 0


    # Handling for ch, includes writing of open/close paragraphs
    elif lines[i][0] == 'ch':
        chnum += 1

        if linesonpage >= minchlines:
            page += 1
            linesonpage = 0
            if popen:
                fout.write('\n</paragraph>\n')
            fout.write(f'@{page}{{}}')
            if popen:
                fout.write('\n<paragraph>\n')

        if meta:
            if recordch:
                meta.write(f'{booknum}@{partnum}@{chnum}@{page}@{lines[i][1]}\n')
            else:
                meta.write(f'{booknum}@{partnum}@{chnum}@{page}\n')

        textlines += 1
        fout.write(f'<ch>{stampline(lines[i][1])}</ch>')
        linesonpage += 1


    # Handling for part
    elif lines[i][0] == 'part':
        partnum += 1
        if linesonpage >= minchlines:
            page += 1
            linesonpage = 0
            if popen:
                fout.write('\n</paragraph>\n')
            fout.write(f'@{page}{{}}')
            if popen:
                fout.write('\n<paragraph>\n')

        if meta:
            if recordch:
                meta.write(f'{booknum}@{partnum}@0@{page}@{lines[i][1]}\n')
            else:
                meta.write(f'{booknum}@{partnum}@0@{page}\n')

        textlines += 1
        fout.write(f'<part>{stampline(lines[i][1])}</part>')

    # Handling for book
    elif lines[i][0] == 'book':
        booknum += 1
        if linesonpage >= minchlines:
            page += 1
            linesonpage = 0
            if popen:
                fout.write('\n</paragraph>\n')
            fout.write(f'@{page}{{}}')
            if popen:
                fout.write('\n<paragraph>\n')

        if meta:
            if recordch:
                meta.write(f'{booknum}@0@0@{page}@{lines[i][1]}\n')
            else:
                meta.write(f'{booknum}@0@0@{page}\n')

        textlines += 1
        fout.write(f'<book>{stampline(lines[i][1])}</book>')

    
    # Handling for stage directions (if that's a thing)
    elif lines[i][0] == 'stage':
        textlines += 1
        fout.write(f'<stage>{stampline(lines[i][1])}</stage>')
        linesonpage += 1

    elif lines[i][0] == 'pre':
        lines[i][1] = stamppreline(lines[i][1])
        fout.write(lines[i][1])
        textlines += 1
        linesonpage += 1

    # Handling for everything else
    elif lines[i][0] == 'text' or lines[i][0] == 'pre':

        # Break up the line and stamp each word, rejoin them together on space
        lines[i][1] = stampline(lines[i][1])


        # Really long multi-branch statement. This provides two four-way
        # branches, the first to handle ragged right, the second to handle
        # normal justify cases. The inner parts of the branches are broken out in
        # the following way:
        # branch 1: a single line paragraph case, to handle indent and justify
        # branch 2: the last line of a paragraph
        # branch 3: the first line of a paragraph
        # branch 4: a normal line
        if raggedright:
            if lines[i+1][0] != 'text' and lines[i-1][0] != 'text':
                fout.write('\n<paragraph class="paragraph">\n')
                fout.write(f'\n<line class="rrsingleline">{lines[i][1]}<br></line>\n')
                fout.write('\n</paragraph>\n')
            elif lines[i+1][0] != 'text':
                fout.write(f'\n<line class="rrlastline">{lines[i][1]}<br></line>\n')
                fout.write('\n</paragraph>\n')
                popen = False
            elif lines[i-1][0] != 'text':
                fout.write(f'\n<paragraph class="paragraph">\n')
                popen = True
                fout.write(f'\n<line class="rrfirstline">{lines[i][1]}<br></line>\n')
            else:
                fout.write(f'\n<line class="rrline">{lines[i][1]}<br></line>\n')
        else:
            if lines[i+1][0] != 'text' and lines[i-1][0] != 'text':
                fout.write('\n<paragraph class="paragraph">\n')
                fout.write(f'\n<line class="singleline">{lines[i][1]}</line>\n')
                fout.write('\n</paragraph>\n')
            elif lines[i+1][0] != 'text':
                fout.write(f'\n<line class="lastline">{lines[i][1]}</line>\n')
                fout.write('\n</paragraph>\n')
                popen = False
            elif lines[i-1][0] != 'text':
                fout.write('\n<paragraph class="paragraph">\n')
                fout.write(f'\n<line class="firstline">{lines[i][1]}</line>\n')
                popen = True
            else:
                fout.write(f'\n<line class="line">{lines[i][1]}</line>\n')

        textlines += 1
        linesonpage += 1

    if linesonpage >= linesperpage and not breakonp:
        page += 1
        linesonpage = 0
        if popen:
            fout.write('\n</paragraph>\n')
        fout.write(f'\n@{page}{{}}\n')
        if popen:
            fout.write('\n<paragraph class="paragraph">\n')

    i += 1

page += 1
fout.write(f'\n@{page}\n')

# cleanup
if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()
if meta:
    meta.close()
