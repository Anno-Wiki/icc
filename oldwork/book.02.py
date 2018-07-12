# Version 01 rearranged
import sys
import re

with open(sys.argv[1], 'rt') as fin, open(sys.argv[2], 'wt') as fout:
    
    # Controller vars
    newline = 0                             # Number of new lines since last text
    chapter = False                         # Flag for chapter tags
    apo = re.compile("[A-Za-z]'[A-Za-z]")   # re to match apostrophes

    for line in fin:

        ##############################################################
        # First 3 elifs handle new line / chapter heading processing #
        ##############################################################

        # The third newline in a series indicates the next is a chapter heading
        if line == '\n' and newline == 1:
            chapter = not chapter
            newline += 1
            continue

        # Process a chapter heading
        elif chapter == True and line != '\n':
            fout.write('<ch>\n' + line[:-1] + '\n</ch>\n')
            newline = 0
            continue

        # Process newlines
        elif line == '\n':
            if newline == 0 and chapter == False:
                fout.write('</p>\n')
            newline += 1
            continue
        
        # The beef of text handling
        else:

            # First text after newlines is start of paragraph
            if newline > 0:
                fout.write('<p>\n')
                newline = 0
                
            # Split the lines on space
            words = line.split()

            # Process each word before printing
            for word in words:
                
                # Punctuation handlers
                # open single quote
                word = re.sub(r"^'", '\n<opensingle>\n', word)
                # close single quote
                word = re.sub(r"'$", '\n<closesingle>\n', word)
                # open double quote
                word = re.sub(r'^"', '\n<opendouble>\n', word)
                # close double quote
                word = re.sub(r'"$', '\n<closedouble>', word)
                # emdash
                word = word.replace('--','\n<em>\n')
                # 4-dot ellipsis catcher
                word = word.replace('....','\n<ellipsis>\n')
                # 3-dot ellipsis
                word = word.replace('...','\n<ellipsis>\n')
                # comma
                word = word.replace(',','\n<comma>\n')
                # semicolon
                word = word.replace(';','\n<semicolon>\n')
                # colon
                word = word.replace(':','\n<colon>\n')
                # period
                word = word.replace('.','\n<period>\n')
                # close quote
                word = word.replace('”','\n<closedouble>\n')
                # open quote
                word = word.replace('“','\n<opendouble>\n')
                # bang point
                word = word.replace('!','\n<bang>\n')
                # query
                word = word.replace('?','\n<query>\n')
                # open parenthese
                word = word.replace('(','\n<openparen>\n')
                # close parenthese
                word = word.replace(')','\n<closeparen>\n')
                # open italic
                word = re.sub(r"^_", '\n<ital>\n', word)
                # close italic
                word = re.sub(r"_$", '\n</ital>\n', word)
                # enclose number in tags
                if '<number>@' not in word: 
                    word = re.sub(r"([0-9]+)", r"\n<number>@\1\n", word)

                # write word to file
                fout.write(word + '\n')
