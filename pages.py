import re
import sys

# Global controllers
fin = sys.stdin     # Default to stdin
fout = sys.stdout   # Default to stdout
linesperpage = 30   # Default min lines before pgbreak (if no breakonp then max)
minchlines = 0      # Minimum lines before a chapter can pagebreak
breakonp = False    # Flag for break on paragraphs
debug = False       # Flag for debugging
raggedright = False # Flag for default to ragged right (e.g. for poetry, etc)
emreg = re.compile('[A-Za-z]+[.,;:!?&]?—[.,;:!?&]?[A-Za-z]+')
ellreg = re.compile('[a-zA-Z]+[!,:;&?]?\.{3,5}[!,:;&?]?[a-zA-Z]+')

# Flag processing
if '-h' in sys.argv:
    h = []
    h.append('-h                                            Help')
    h.append('-i <inputfile>')
    h.append('-o <outputfile>')
    h.append('-l <lines per page>                           (Default = 30)')
    h.append('-m <min lines before new page for ch>         (Default = 0)')
    h.append('-p                                            Break on p')
    h.append('-r                                            Enable ragged right')
    h.append('-d                                            Debug Mode')
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


# Stamper for words
def stamp(word, wordcounter):
    if not debug:
        word = f'<word id="{wordcounter}">{word}</word>'
    return word


lines = [['beginning', 'beginning']] # Prepend initial value
i = 1   # Must index from one to avoid out of bounds for checking previous
for line in fin:

    # Blank lines
    if re.match(r'^$', line):
        lines.append(['blank', 'blank'])

    # if it's a chapter line or stage line
    elif '<div class="chapter"' in line:
        lines.append(['ch', line])
    elif '<div class="stage"' in line:
        lines.append(['stage', line])
    
    # For everything else
    elif line != '':        # I may consider converting this to re.match or else
        lines.append(['text', line])
    i += 1
    


lines.append(['last', 'last'])
i = 1                           # Reset i to 0
wordcount = 0                   # Keep track of words
textlines = 0                   # Count number of lines printed in toto
linesonpage = 0                 # Keep track of lines per page
page = 0                        # Keep track of page number
popen = False                   # paragraph open flag
for line in lines:

    # Necessary for last case to avoid out of bounds error
    if i >= len(lines):
        break

    # Blank lines should be preserved, and handling for breakonp
    if lines[i][0] == 'blank':
        fout.write('\n\n')
        # Breakonp
        if linesonpage >= linesperpage and breakonp and lines[i][0] == 'blank':
            page += 1
            fout.write(f'@{page}{{}}')
            linesonpage = 0

    # Handling for ch, includes writing of open/close paragraphs
    elif lines[i][0] == 'ch':
        if linesonpage >= minchlines:
            page += 1
            linesonpage = 0
            if popen:
                fout.write('\n</paragraph>\n')
            fout.write(f'@{page}{{}}')
            if popen:
                fout.write('\n<paragraph class="paragraph">\n')
        textlines += 1
        fout.write(lines[i][1])
        linesonpage += 1
    
    # Handling for stage directions (if that's a thing)
    elif lines[i][0] == 'stage':
        textlines += 1
        fout.write(lines[i][1])
        linesonpage += 1

    # Handling for everything else
    elif lines[i][0] == 'text':

        # Break up the line and stamp each word, rejoin them together on space
        words = lines[i][1].split()
        for j, word in enumerate(words):
                wordcount += 1
                words[j] = stamp(word, wordcount)
        lines[i][1] = ' '.join(words)

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
                fout.write(f'\n<div class="rrsingleline">{lines[i][1]}<br></div>\n')
                fout.write('\n</paragraph>\n')
            elif lines[i+1][0] != 'text':
                fout.write(f'\n<div class="rrlastline">{lines[i][1]}<br></div>\n')
                fout.write('\n</paragraph>\n')
                popen = False
            elif lines[i-1][0] != 'text':
                fout.write(f'\n<paragraph class="paragraph">\n')
                popen = True
                fout.write(f'\n<div class="rrfirstline">{lines[i][1]}<br></div>\n')
            else:
                fout.write(f'\n<div class="rrline">{lines[i][1]}<br></div>\n')
        else:
            if lines[i+1][0] != 'text' and lines[i-1][0] != 'text':
                fout.write('\n<paragraph class="paragraph">\n')
                fout.write(f'\n<div class="singleline">{lines[i][1]}</div>\n')
                fout.write('\n</paragraph>\n')
            elif lines[i+1][0] != 'text':
                fout.write(f'\n<div class="lastline">{lines[i][1]}</div>\n')
                fout.write('\n</paragraph>\n')
                popen = False
            elif lines[i-1][0] != 'text':
                fout.write('\n<paragraph class="paragraph">\n')
                fout.write(f'\n<div class="firstline">{lines[i][1]}</div>\n')
                popen = True
            else:
                fout.write(f'\n<div class="line">{lines[i][1]}</div>\n')

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
fout.write(f'\n@{page}{{}}\n')

# cleanup
if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()
