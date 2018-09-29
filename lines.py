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
bkreg = None                            # Regex - tagging Books
chreg = None                            # Regex - tag Chapters
ptreg = None                            # Regex - tag Parts
stgreg = None                           # Regex - tag Stage Directions


# Constant regexes
bible_book_regex = re.compile(r"(^(The Gospel According|The Lamentations|The Acts|The Revelation)|^(The Revelation|Ezra|The Proverbs|Ecclesiastes|The Song of Solomon|The Acts|Hosea|Joel|Obadiah|Jonah|Micah|Amos|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi)$|(Book|Epistle))")
bible_testament_regex = re.compile(r"Testament")
ellreg = re.compile(r"[a-zA-Z]+[!,:;&?]?\.{3,5}[!,:;&?]?[a-zA-Z]+")
emreg = re.compile("[A-Za-z]+[.,;:!?&]?—[.,;:!?&]?[A-Za-z]+")
wordboundary = re.compile("\w+|\W")     # Word boundary break for split
hrreg = re.compile(r"^\*\*\*$")         # Regex - hr
prereg = re.compile(r"```")             # Regex - tag <pre>'s
quoreg = re.compile(r"^>")              # Regex - tag quote 

# Flags
aggch = False                           # Flag - chnums across books and parts
aggpt = False                           # Flag - preserving ptnum across bks
raggedright = False                     # Flag - raggedright
procpre = False                         # Flag - process pre
procquo = False                         # Flag - process quotes
prochr = False                          # Flag - process hr's

# Files
fin = codecs.getreader("utf_8_sig")(sys.stdin.buffer, errors="replace")
fout = sys.stdout

# Help menu
def printhelp():
    h = []
    h.append(f"Usage: python {sys.argv[0]} -b <book_id> [options] [-i <input file>] [-o <output file>]")
    h.append(f"The output is formatted as @ separated values of the order:")
    h.append(f"book_id   l_num   kind   bk_num   pt_num   ch_num   emstatus line")

    h.append("")
    h.append("Defaults to stdin and stdout. To specify an input or output file")
    h.append("use one or both of the following flags")
    h.append("-i <input file>")
    h.append("-o <output file>")

    h.append("")
    h.append("      Flags")
    h.append("-b <book_id>          Book id *required*")
    h.append("-h                    Help")
    h.append("-r                    Enable ragged right")

    h.append("")
    h.append("      Flags to prevent reset of ch and pt numbers in heierarchical")
    h.append("      text organization processing")
    h.append("--aggch               Aggregate chapters, do not reset")
    h.append("--aggpt               Aggregate parts, do not reset")

    
    h.append("")
    h.append("      Regexes for identifying subtitles")
    h.append("--bible               Enable bible chapter detection mode")
    h.append("--bk <regex>          Regex for Books (Heierarchical chapters lvl 1)")
    h.append("--pt <regex>          Regex for Parts (Heierarchical chapters lvl 2)")
    h.append("--ch <regex>          Regex for Chapters (Heierarchical Chapters lvl 3)")
    h.append("--stg <regex>         Regex for Stage Directions")

    h.append("--hr                  Process horizontal rule breaks")
    h.append("--pre                 Process pre lines")
    h.append("--quo                 Process quoted lines")

    for l in h:
        print(l)
    sys.exit()

# Input file override
if "-i" in sys.argv:
    fin = open(path, "rt", encoding="UTF-8-SIG")
if "-o" in sys.argv:
    fout = open(path, "wt", encoding="UTF-8-SIG")

# Flags
if "-h" in sys.argv:
    printhelp()
if "-r" in sys.argv:
    raggedright = True

# Aggregation flags
if "--aggch" in sys.argv:
    aggch = True
if "--aggpt" in sys.argv:
    aggpt = True

# Regex
if "--bible" in sys.argv:
    ptreg = bible_book_regex
    bkreg = bible_testament_regex
if "--bk" in sys.argv:
    bkreg = re.compile(sys.argv[sys.argv.index("--bk")+1])
if "--pt" in sys.argv:
    ptreg = re.compile(sys.argv[sys.argv.index("--pt")+1])
if "--ch" in sys.argv:
    chreg = re.compile(sys.argv[sys.argv.index("--ch")+1])
if "--hr" in sys.argv:
    prochr = True
if "--stg" in sys.argv:
    stgreg = re.compile(sys.argv[sys.argv.index("--stg")+1])
if "--pre" in sys.argv:
    procpre = True
if "--quo" in sys.argv:
    procquo = True
if "-b" not in sys.argv:
    sys.exit("-b <book_id> flag required")
else:
    book_id = int(sys.argv[sys.argv.index("-b") + 1])


###############
## Functions ##
###############

def lout(cls, l):
    fout.write(f"{book_id}@{txtlines}@{cls}@{bknum}@{ptnum}@{chnum}@{l[2]}@{l[1]}")


def oc(line):
    o = line.count("<em>")
    c = line.count("</em>")
    return o - c

#######################
## Initial file read ##
#######################

lines = [["beginning", "beginning"]] # Prepend initial value
i = 1   # Must index from one to avoid out of bounds for checking previous
us = False
lem = False
pre = False

# In order to accomplish contextual tagging (i.e., based on previous 
# and next lines) we have to read the whole file into memory.
for line in fin:

    # Blank lines
    if re.match(r"^$", line):
        lines.append(["blank", "blank"])

    # All special lines
    elif procpre and re.search(prereg, line):
        pre = not pre
        continue
    elif procpre and pre:
        lines.append(["pre", line])
    elif bkreg and re.search(bkreg, line):
        lines.append(["bk", line])
    elif ptreg and re.search(ptreg, line):
        lines.append(["pt", line])
    elif chreg and re.search(chreg, line):
        lines.append(["ch", line])
    elif stgreg and re.search(stgreg, line):
        lines.append(["stg", line])
    elif prochr and re.search(hrreg, line):
        lines.append(["hr", '<hr class="book_separator">'])
    elif procquo and re.search(quoreg, line):
        lines.append(["quo", line[1:]])
    
    # For everything else
    elif line != "":        # Possibly convert to `re.match` or `else`
        lines.append(["text", line])

    converted = []
    if "_" in line:
        for c in line:
            if c == "_":
                if us:
                    converted.append("</em>")
                    us = False
                else:
                    converted.append("<em>")
                    us = True

    converted = "".join(converted)
    if oc(converted) > 0:
        lines[i].append("oem")
        lem = True
    elif oc(converted) < 0:
        lines[i].append("cem")
        lem = False
    elif lem:
        lines[i].append("em")
    else:
        lines[i].append("nem")


    i += 1

lines.append(["last", "last"]) # Append a final value to avoid out of bounds



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
    elif lines[i][0] == "hr":
        # We only need to write it to the pages and to
        # files meant to be displayed in full
        txtlines += 1
        lout("hr", "", "nem")

    # Handling for ch, includes writing of open/close paragraphs
    elif lines[i][0] == "ch":
        chnum += 1
        txtlines += 1
        lout("ch", lines[i])

    # Handling for part
    elif lines[i][0] == "pt":
        ptnum += 1
        txtlines += 1
        if not aggch:
            chnum = 0
        lout("pt", lines[i])

    # Handling for book
    elif lines[i][0] == "bk":
        bknum += 1
        txtlines += 1
        if not aggpt:
            ptnum = 0
        if not aggch:
            chnum = 0
        lout("bk", lines[i])

    # Handling for stage directions (if that"s a thing)
    elif lines[i][0] == "stg":
        txtlines += 1
        lout("stg", lines[i])

    # Handling for quoted lines
    elif lines[i][0] == "quo":
        txtlines += 1
        lines[i][1] = re.sub(r">", r"", lines[i][1])
        lout("quo", lines[i])

    # Handling for pre lines
    elif lines[i][0] == "pre":
        txtlines += 1
        # single line
        if lines[i+1][0] != "pre" and lines[i-1][0] != "pre":
            lout("spre", lines[i])

        # last line in a p
        elif lines[i+1][0] != "pre":
            lout("lpre", lines[i])
            
        # first line in a p
        elif lines[i-1][0] != "pre":
            lout("fpre", lines[i])

        # regular line in middle of a p
        else:
            lout("pre", lines[i])
    
    # Handling for everything else
    elif lines[i][0] == "text":
        txtlines += 1

        if raggedright:

            # single line
            if lines[i+1][0] != "text" and lines[i-1][0] != "text":
                lout("rsl", lines[i])

            # last line in a p
            elif lines[i+1][0] != "text":
                lout("rll", lines[i])

            # first line in a p
            elif lines[i-1][0] != "text":
                lout("rfl", lines[i])

            # regular line in middle of a p
            else:
                lout("rl", lines[i])
                        
        else:
            # single line
            if lines[i+1][0] != "text" and lines[i-1][0] != "text":
                lout("sl", lines[i])

            # last line in a p
            elif lines[i+1][0] != "text":
                lout("ll", lines[i])
                
            # first line in a p
            elif lines[i-1][0] != "text":
                lout("fl", lines[i])

            # regular line in middle of a p
            else:
                lout("l", lines[i])

    i += 1


# cleanup
if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()
