import codecs
import re
import sys

#########################
## Variables and flags ##
#########################

# Global controllers
bookregex = None                        # Regex - tagging Books
breakonp = False                        # Flag - break on paragraphs
chconst = False                         # Flag - chnums across books and parts
chregex = None                          # Regex - tag Chapters
debug = False                           # Flag - debugging
filename = ''                           # File name for all output files
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

# File holders
breaks = None                           # File for breaks info 
elasticsearchlines = None               # File for elasticsearch lines (excl html)
fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace')
fout = sys.stdout                       # Default to stdout
fullbook = None                         # Full book holder
mysqllines = None                       # File for mysql lines (incl html)

# Constants
bible_book_regex = '(^(The Gospel According|The Lamentations|The Acts|The Revelation)|^(The Revelation|Ezra|The Proverbs|Ecclesiastes|The Song of Solomon|The Acts|Hosea|Joel|Obadiah|Jonah|Micah|Amos|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi)$|(Book|Epistle))'
bible_testament_regex = 'Testament'
ellreg = re.compile('[a-zA-Z]+[!,:;&?]?\.{3,5}[!,:;&?]?[a-zA-Z]+')
emreg = re.compile('[A-Za-z]+[.,;:!?&]?—[.,;:!?&]?[A-Za-z]+')

# Help menu
if '-h' in sys.argv:
    h = []
    h.append('Program reads form stdin and outputs to stdout by default. More than likely')
    h.append("you're going to want to specify some special output files. More than likely")
    h.append("you're going to want to specify all the special output files. Use -n for that")
    h.append("but don't include a file extension.")
    h.append('-_                              Process underscores as italics')
    h.append('-b <regex>                      Regex for Books (Heierarchical chapters lvl 1)')
    h.append('-c <regex>                      Regex for Chapters (Heierarchical Chapters lvl 3')
    h.append('-d                              Debug Mode')
    h.append('-h                              Help')
    h.append('-i <inputfile>')
    h.append('-l <lines per page>             (Default = 30)')
    h.append('-m <min lines>                  Minimum # of ll before chapter break (Default = 5)')
    h.append('-n <filename>                   File name for all files (do not include extension)')
    h.append('-o <outputfile>')
    h.append('-p                              Break on p')
    h.append('-r                              Enable ragged right')
    h.append('-s <regex>                      Regex for Stage Directions')
    h.append('--aggchapters                   Aggregate chapters, do not reset')
    h.append('--aggparts                      Aggregate parts, do not reset')
    h.append('--bible                         Enable bible chapter detection mode')
    h.append('--breaks <outfile>              Write breaksdata to a breaks file')
    h.append('--elasticsearch <outfile>       Output elasticsearch file')
    h.append('--fullbook <outfile>            Write the full book to a book file')
    h.append('--hr <regex>                    Regex for horizontal rule breaks')
    h.append('--mysql <outfile>               Output mysql lines file')
    h.append('--part <regex>                  Regex for Parts (Heierarchical chapters lvl 2)')
    h.append('--pre <regex>                   Enable pre on <regex>')
    h.append('--recordch                      Record titles for chapters (e.g., if distinct)')
    for l in h:
        print(l)
    sys.exit()

# Flag processing (I seriously need to think about using getopts
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
if '-n' in sys.argv:
    breaks = open(sys.argv[sys.argv.index('-n')+1] + '.breaks', 'wt')
    elasticsearchlines = open(sys.argv[sys.argv.index('-n')+1] + '.es', 'wt')
    fout = open(sys.argv[sys.argv.index('-n')+1] + '.icc', 'wt')
    fullbook = open(sys.argv[sys.argv.index('-n')+1] + '.book', 'wt')
    mysqllines = open(sys.argv[sys.argv.index('-n')+1] + '.mysql', 'wt')
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
if '--elasticsearch' in sys.argv:
    elasticsearchlines = open(sys.argv[sys.argv.index('--elasticsearch') + 1], 'wt')
if '--fullbook' in sys.argv:
    fullbook = open(sys.argv[sys.argv.index('--fullbook')+1], 'wt')
if '--hr' in sys.argv:
    hr_regex = re.compile(sys.argv[sys.argv.index('--hr')+1])
if '--mysql' in sys.argv:
    mysqllines = open(sys.argv[sys.argv.index('--mysql')+1], 'wt')
if '--part' in sys.argv:
    partregex = re.compile(sys.argv[sys.argv.index('--part')+1])
if '--pre' in sys.argv:
    preline = re.compile(sys.argv[sys.argv.index('--pre')+1])
if '--recordch' in sys.argv:
    recordch = True






###############
## Functions ##
###############

# Stamper for words
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

lines.append(['last', 'last']) # Append a final value to avoid out of bounds








###################
## The Main Loop ##
###################


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
        if fullbook:
            fullbook.write('\n\n')

        # Breakonp
        if linesonpage >= linesperpage and breakonp and lines[i+1][0] != 'stage':
            procpage()



    # horizontal rule printer
    elif lines[i][0] == 'hr':
        # We only need to write it to the pages and to
        # files meant to be displayed in full
        fout.write('<hr class="bookseparator">')
        if fullbook:
            fullbook.write(f'<hr class="bookseparator">')



    # Handling for ch, includes writing of open/close paragraphs
    elif lines[i][0] == 'ch':

        chnum += 1
        if linesonpage >= minchlines:
            procpage()

        # Process breaks file
        if breaks:
            if recordch:
                breaks.write(f'{booknum}@{partnum}@{chnum}@{page + 1}@{lines[i][1]}')
            else:
                breaks.write(f'{booknum}@{partnum}@{chnum}@{page + 1}\n')

        textlines += 1

        # Process everything
        fout.write(f'<ch id="{lhash()}">{stampline(lines[i][1], preline = False)}</ch>')
        if elasticsearchlines:
            elasticsearchlines.write(lines[i][1])
        if fullbook:
            fullbook.write(f'<ch id="{lhash()}">\n{stampline(lines[i][1], preline = False)}</ch>')
        if mysqllines:
            mysqllines.write(f'<ch id="{lhash()}">{stampline(lines[i][1], preline = False)}</ch>')
        linesonpage += 1


    # Handling for part
    elif lines[i][0] == 'part':
        
        partnum += 1
        if not chconst:
            chnum = 0
        if linesonpage >= minchlines:
            procpage()

        # Process breaks file
        if breaks:
            if recordch:
                breaks.write(f'{booknum}@{partnum}@0@{page + 1}@{lines[i][1]}')
            else:
                breaks.write(f'{booknum}@{partnum}@0@{page + 1}\n')
                
        textlines += 1

        # Process everything
        fout.write(f'<part id="{lhash()}">{stampline(lines[i][1], preline = False)}</part>')
        if elasticsearchlines:
            elasticsearchlines.write(lines[i][1])
        if fullbook:
            fullbook.write(f'<part id="{lhash()}">\n{stampline(lines[i][1], preline = False)}</part>')
        if mysqllines:
            mysqllines.write(f'<part id="{lhash()}">{stampline(lines[i][1], preline = False)}</part>')
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
        fout.write(f'<book id="{lhash()}">{stampline(lines[i][1], preline = False)}</book>')
        if elasticsearchlines:
            elasticsearchlines.write(lines[i][1])
        if fullbook:
            fullbook.write(f'<book id="{lhash()}">\n{stampline(lines[i][1], preline = False)}</book>')
        if mysqllines:
            mysqllines.write(f'<book id="{lhash()}">{stampline(lines[i][1], preline = False)}</book>')
        linesonpage += 1

    
    # Handling for stage directions (if that's a thing)
    elif lines[i][0] == 'stage':
        textlines += 1
        fout.write(f'<stage id="{lhash()}">{stampline(lines[i][1], preline = False)}</stage>')
        if elasticsearchlines:
            elasticsearchlines.write(lines[i][1])
        if fullbook:
            fullbook.write(f'<stage id="{lhash()}">\n{stampline(lines[i][1], preline = False)}</stage>')
        if mysqllines:
            mysqllines.write(f'<stage id="{lhash()}">{stampline(lines[i][1], preline = False)}</stage>')
        linesonpage += 1

    elif lines[i][0] == 'pre':
        textlines += 1
        fout.write(stampline(lines[i][1], preline = True))
        if elasticsearchlines:
            elasticsearchlines.write(lines[i][1])
        if fullbook:
            fullbook.write(stampline(lines[i][1], preline = True))
        if mysqllines:
            mysqlllines.write(stampline(lines[i][1], preline = True))
        linesonpage += 1
    

    # Handling for everything else
    elif lines[i][0] == 'text':

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
                # p opener
                fout.write('\n<paragraph class="raggedright">\n')
                if fullbook:
                    fullbook.write('\n<paragraph class="raggedright">\n')

                # line
                fout.write(f'<line class="rrsingleline" id="{lhash()}">\n{stampline(lines[i][1], preline = False)}</line>\n')
                if elasticsearchlines:
                    elasticsearchlines.write(lines[i][1])
                if fullbook:
                    fullbook.write(stampline(lines[i][1], preline = False))
                if mysqllines:
                    mysqllines.write(f'<line class="rrsingleline" id="{lhash()}">{stampline(lines[i][1], preline = False)}</line>\n')
                
                # p closer
                fout.write('</paragraph>\n')
                if fullbook:
                    fullbook.write('</paragraph>\n')


            # last line in a p
            elif lines[i+1][0] != 'text':
                # line
                fout.write(f'<line class="rrlastline" id="{lhash()}">\n{stampline(lines[i][1], preline = False)}</line>\n')
                if elasticsearchlines:
                    elasticsearchlines.write(lines[i][1])
                if fullbook:
                    fullbook.write(stampline(lines[i][1], preline = False))
                if mysqllines:
                    mysqllines.write(f'<line class="rrlastline" id="{lhash()}">{stampline(lines[i][1], preline = False)}</line>\n')

                # p closer
                fout.write('</paragraph>\n')
                if fullbook:
                    fullbook.write('</paragraph>\n')

                popen = False


            # first line in a p
            elif lines[i-1][0] != 'text':
                # p opener
                fout.write(f'\n<paragraph class="raggedright">\n')
                if fullbook:
                    fullbook.write(f'\n<paragraph class="raggedright">\n')
                
                # line
                fout.write(f'<line class="rrfirstline" id="{lhash()}">\n{stampline(lines[i][1], preline = False)}</line>\n')
                if elasticsearchlines:
                    elasticsearchlines.write(lines[i][1])
                if fullbook:
                    fullbook.write(stampline(lines[i][1], preline = False))
                if mysqllines:
                    mysqllines.write(f'<line class="rrfirstline" id="{lhash()}">{stampline(lines[i][1], preline = False)}</line>\n')

                popen = True


            # regular line in middle of a p
            else:
                fout.write(f'<line class="rrline" id="{lhash()}">\n{stampline(lines[i][1], preline = False)}</line>\n')
                if elasticsearchlines:
                    elasticsearchlines.write(lines[i][1])
                if fullbook:
                    fullbook.write(stampline(lines[i][1], preline = False))
                if mysqllines:
                    mysqllines.write(f'<line class="rrline" id="{lhash()}">{stampline(lines[i][1], preline = False)}</line>\n')

        else:
            # single line
            if lines[i+1][0] != 'text' and lines[i-1][0] != 'text':
                # p opener
                fout.write('\n<paragraph class="justified">\n')
                if fullbook:
                    fullbook.write('\n<paragraph class="justified">\n')

                # line
                fout.write(f'<line class="singleline" id="{lhash()}">\n{stampline(lines[i][1], preline = False)}</line>\n')
                if elasticsearchlines:
                    elasticsearchlines.write(lines[i][1])
                if fullbook:
                    fullbook.write(stampline(lines[i][1], preline = False))
                if mysqllines:
                    mysqllines.write(f'<line class="singleline" id="{lhash()}">{stampline(lines[i][1], preline = False)}</line>\n')
                
                # p closer
                fout.write('</paragraph>\n')
                if fullbook:
                    fullbook.write('</paragraph>\n')


            # last line in a p
            elif lines[i+1][0] != 'text':
                # line
                fout.write(f'<line class="lastline" id="{lhash()}">\n{stampline(lines[i][1], preline = False)}</line>\n')
                if elasticsearchlines:
                    elasticsearchlines.write(lines[i][1])
                if fullbook:
                    fullbook.write(stampline(lines[i][1], preline = False))
                if mysqllines:
                    mysqllines.write(f'<line class="lastline" id="{lhash()}">{stampline(lines[i][1], preline = False)}</line>\n')

                # p closer
                fout.write('</paragraph>\n')
                if fullbook:
                    fullbook.write('</paragraph>\n')

                popen = False


            # first line in a p
            elif lines[i-1][0] != 'text':
                # p opener
                fout.write(f'\n<paragraph class="justified">\n')
                if fullbook:
                    fullbook.write(f'\n<paragraph class="justified">\n')
                
                # line
                fout.write(f'<line class="firstline" id="{lhash()}">\n{stampline(lines[i][1], preline = False)}</line>\n')
                if elasticsearchlines:
                    elasticsearchlines.write(lines[i][1])
                if fullbook:
                    fullbook.write(stampline(lines[i][1], preline = False))
                if mysqllines:
                    mysqllines.write(f'<line class="firstline" id="{lhash()}">{stampline(lines[i][1], preline = False)}</line>\n')

                popen = True


            else:
                fout.write(f'<line class="line" id="{lhash()}">\n{stampline(lines[i][1], preline = False)}</line>\n')
                if elasticsearchlines:
                    elasticsearchlines.write(lines[i][1])
                if fullbook:
                    fullbook.write(stampline(lines[i][1], preline = False))
                if mysqllines:
                    mysqllines.write(f'<line class="line" id="{lhash()}">{stampline(lines[i][1], preline = False)}</line>\n')

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
