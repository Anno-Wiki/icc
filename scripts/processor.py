#!/bin/sh
if 'true' : '''\'
then
exec '$VENV' '$0' '$@'
exit 127
fi
'''
import codecs, re, sys, argparse, json

parser = argparse.ArgumentParser("Parses text files into icc csv files.")

# input and out put files
parser.add_argument('-i', '--input', action='store', type=str, default=None,
        help="Specify input file")
parser.add_argument('-o', '--output', action='store', type=str, default=None,
        help="Specify output file")

# level and stage regex
parser.add_argument('-1', '--level1', action='store', type=str, default=None,
        help="The 1st level of the hierarchical chapter system")
parser.add_argument('--level1label', action='store', type=str,
        default="Level 1 Marker", help="Optional label for level 1")

parser.add_argument('-2', '--level2', action='store', type=str, default=None,
        help="The 2nd level")
parser.add_argument('--level2label', action='store', type=str,
        default="Level 2 Marker", help="Optional label for level 2")

parser.add_argument('-3', '--level3', action='store', type=str, default=None,
        help="The 3rd level")
parser.add_argument('--level3label', action='store', type=str,
        default="Level 3 Marker", help="Optional label for level 3")

parser.add_argument('-4', '--level4', action='store', type=str, default=None,
        help="The 4th level")
parser.add_argument('--level4label', action='store', type=str,
        default="Level 4 Marker", help="Optional label for level 4")

parser.add_argument('-s', '--stage', action='store', type=str, default=None,
        help="Stage directions")

# parse the bible
parser.add_argument('-b', '--bible', action='store_true',
        help="Option designed for parsing the Bible")

# aggregate level numbers flags
parser.add_argument('--agg2', action='store_true', help="Aggregate level 2")
parser.add_argument('--agg3', action='store_true', help="Aggregate level 3")
parser.add_argument('--agg4', action='store_true', help="Aggregate level 4")

args = parser.parse_args()
args.pre = True
args.quo = True
args.hr = True

#########################
## Variables and flags ##
#########################

# Files
fin = codecs.getreader('utf_8_sig')(sys.stdin.buffer, errors='replace') \
        if not args.input else open(path, 'rt', encoding='UTF-8-SIG')
fout = sys.stdout if not args.output else open(path, 'wt', encoding='UTF-8-SIG')

######################
# Global controllers #
######################

# Regex identifiers

# The levels form a heierarchy up to four levels deep. Level 1 is the topmost
# level, level 4 is the lowest level. Treat the levels like a stack, i.e., if
# there are only chapters, they are level 1, if there are books and chapters,
# level 1 is books, level 2 is chapters; this is actually dependent on the user,
# not the program.
lvl1reg = re.compile(args.level1) if args.level1 else None
lvl2reg = re.compile(args.level2) if args.level2 else None
lvl3reg = re.compile(args.level3) if args.level3 else None
lvl4reg = re.compile(args.level4) if args.level4 else None
stgreg = re.compile(args.stage) if args.stage else None


######################
## Constant regexes ##
######################

bible_book_regex = re.compile(r"(^(The Gospel According|The Lamentations"
        "|The Acts|The Revelation)|^(The Revelation|Ezra|The Proverbs"
        "|Ecclesiastes|The Song of Solomon|The Acts|Hosea|Joel|Obadiah|Jonah"
        "|Micah|Amos|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi)$"
        "|(Book|Epistle))")
bible_testament_regex = re.compile(r"Testament")

# regex for identifying ellipses and — em dashes
ellreg = re.compile(r"[a-zA-Z]+[!,:;&?]?\.{3,5}[!,:;&?]?[a-zA-Z]+")
emreg = re.compile("[A-Za-z]+[.,;:!?&]?—[.,;:!?&]?[A-Za-z]+")

# markdown like flags for horizontal rules, preformatted text, and quotations
hrreg = re.compile(r"^\*\*\*$")         # Regex - hr
prereg = re.compile(r"```")             # Regex - tag <pre>"s
quoreg = re.compile(r"^>")              # Regex - tag quote

wordboundary = re.compile("\w+|\W")     # Word boundary break for split

###############
## Functions ##
###############

data_array = []

def append(func):
    def call(*args, **kwargs):
        result = func(*args, **kwargs)
        data_array.append(result)
        return result
    return call

@append
def lout(cls, l):
    # l is an array of the form ['line-type', 'line', 'emphasis-status']
    # The form of the outpt csv is:
    # line-number, line-type, emphasis-status,
    # level-1-number through level-4-number,
    # line
    # We use @ signs because actual commas are a headache and a half
    return { 'num': txtlines, 'label': cls, 'em_status': l[2],
            'l1': lvl1num, 'l2': lvl2num, 'l3': lvl3num, 'l4': lvl4num,
            'line': l[1].strip() }

def oc(line):
    o = line.count('<em>')
    c = line.count('</em>')
    return o - c

#######################
## Initial file read ##
#######################

lines = [['beginning', 'beginning']] # Prepend initial value
i = 1   # Must index from one to avoid out of bounds for checking previous
us = False # Underscore open flag
lem = False # Line-by-line emphasis flag
pre = False # pre flag

# In order to accomplish contextual tagging (i.e., based on previous
# and next lines) we have to read the whole file into memory.
for line in fin:

    # Blank lines
    if re.match(r"^$", line):
        lines.append(['blank', 'blank'])

    # All special lines
    elif args.pre and re.search(prereg, line):
        pre = not pre
        continue
    elif args.pre and pre:
        lines.append(['pre', line])
    elif lvl1reg and re.search(lvl1reg, line):
        lines.append(['lvl1', line])
    elif lvl2reg and re.search(lvl2reg, line):
        lines.append(['lvl2', line])
    elif lvl3reg and re.search(lvl3reg, line):
        lines.append(['lvl3', line])
    elif lvl4reg and re.search(lvl4reg, line):
        lines.append(['lvl4', line])
    elif stgreg and re.search(stgreg, line):
        lines.append(['stg', line])
    elif args.hr and re.search(hrreg, line):
        lines.append(['hr', '<hr class='book_separator'>'])
    elif args.quo and re.search(quoreg, line):
        lines.append(['quo', line[1:]])

    # For everything else
    elif line != '':        # Possibly convert to `re.match` or `else`
        lines.append(['text', line])

    converted = []
    if '_' in line:
        for c in line:
            if c == '_':
                if us:
                    converted.append('</em>')
                    us = False
                else:
                    converted.append('<em>')
                    us = True

    converted = ''.join(converted)
    if oc(converted) > 0:
        lines[i].append('oem>Line with Open Emphasis')
        lem = True
    elif oc(converted) < 0:
        lines[i].append('cem>Line with Closed Emphasis')
        lem = False
    elif lem:
        lines[i].append('em>Line with Emphasis')
    else:
        lines[i].append('nem>Line with No Emphasis')


    i += 1

lines.append(['last', 'last']) # Append a final value to avoid out of bounds



###################
## The Main Loop ##
###################

i = 1                           # Reset i to 1 to avoid first case of out of bounds
wordcount = 0                   # Keep track of words
txtlines = 0                   # Count number of lines printed in toto

# Heierarchical chapter numbers
lvl1num = 0
lvl2num = 0
lvl3num = 0
lvl4num = 0


for line in lines:

    # Necessary for last case to avoid out of bounds error
    if i >= len(lines):
        break

    # horizontal rule printer
    elif lines[i][0] == 'hr':
        # We only need to write it to the pages and to
        # files meant to be displayed in full
        txtlines += 1
        lout('hr>Horizontal Rule', '', 'nem')

    # handling for level 1
    elif lines[i][0] == 'lvl1':
        lvl1num += 1
        txtlines += 1
        if not args.agg2:
            lvl2num = 0
        if not args.agg3:
            lvl3num = 0
        if not args.agg4:
            lvl4num = 0
        lout(f'lvl1>{args.level1label}', lines[i])

    # Handling for level 2
    elif lines[i][0] == 'lvl2':
        lvl2num += 1
        txtlines += 1
        if not args.agg3:
            lvl3num = 0
        if not args.agg4:
            lvl4num = 0
        lout(f'lvl2>{args.level2label}', lines[i])

    # Handling for level 3
    elif lines[i][0] == 'lvl3':
        lvl3numnum += 1
        txtlines += 1
        if not args.agg4:
            lvl4num = 0
        lout(f'lvl3>{args.level3label}', lines[i])

    # Handling for level 4
    elif lines[i][0] == 'lvl4':
        lvl4numnum += 1
        txtlines += 1
        lout(f'lvl4>{args.level4label}', lines[i])

    # Handling for stage directions (if that's a thing)
    elif lines[i][0] == 'stg':
        txtlines += 1
        lout('stg>Stage Direction', lines[i])

    # Handling for quoted lines
    elif lines[i][0] == 'quo':
        txtlines += 1
        lines[i][1] = re.sub(r'>', r'', lines[i][1])
        lout('quo>Block Quotation', lines[i])

    # Handling for pre lines
    elif lines[i][0] == 'pre':
        txtlines += 1
        # single line
        if lines[i+1][0] != 'pre' and lines[i-1][0] != 'pre':
            lout('spre>Single Preformatted Line', lines[i])

        # last line in a p
        elif lines[i+1][0] != 'pre':
            lout('lpre>Last Preformatted Line', lines[i])

        # first line in a p
        elif lines[i-1][0] != 'pre':
            lout('fpre>First Preformatted Line', lines[i])

        # regular line in middle of a p
        else:
            lout('pre>Preformatted Line', lines[i])

    # Handling for everything else
    elif lines[i][0] == 'text':
        txtlines += 1

        # single line
        if lines[i+1][0] != 'text' and lines[i-1][0] != 'text':
            lout('sl>Single Line', lines[i])

        # last line in a p
        elif lines[i+1][0] != 'text':
            lout('ll>Last Line', lines[i])

        # first line in a p
        elif lines[i-1][0] != 'text':
            lout('fl>First Line', lines[i])

        # regular line in middle of a p
        else:
            lout('l>Line', lines[i])

    i += 1

fout.write(json.dumps(data_array))

# cleanup
if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()
