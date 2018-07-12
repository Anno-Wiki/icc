# Implementation of regex-based and newline-based flags for chapter processing.

import sys
import re

with open(sys.argv[1], 'rt') as fin, open(sys.argv[2], 'wt') as fout:
    
    # Controller vars
    newline = 0             # Number of new lines since last text
    prevwrite = 'begin'     # holder for previous fout.write()
    linepreservation = False


    if '-l' in sys.argv:
        linepreservation = True


    ##############
    ## THE LOOP ##
    ##############

    for line in fin:
        

        # process paragraph end 
        if line == '\n' and prevwrite == 'text': 
            newline +=1
            prevwrite = '\n</p>\n'
            fout.write(prevwrite)
            continue

            
        # process all other new lines
        elif line == '\n':
            newline += 1
            prevwrite = 'newline'




        ############## 
        ## THE BEEF ##
        ############## 

        elif line != '\n':


            prevwrite = 'text'
            
            # First text after newlines is start of paragraph
            if newline > 0:
                fout.write('\n<p>\n')
                newline = 0

            if line.startswith('  '):
                stretch = re.match('^ [ _]+', line)
                fout.write('<indent>@' + str(stretch.end()) + '\n')
                
            # Split the lines on space
            words = line.split()

            # Process each word before printing
            for word in words:

                # Process chapter:verse numbers
                if re.search(r'(^[0-9][0-9]?[0-9]?):([0-9][0-9]?[0-9]?)', word):
                    word = '<book>@' + str(chnum - 1) + re.sub(r'(^[0-9][0-9]?[0-9]?):([0-9][0-9]?[0-9]?)', r'\n<chapter>@\1\n<verse>@\2\n', word)
                
                # Punctuation handlers

                # emdash
                word = re.sub(r' (--|—)', '\n<emattrib>\n', word)
                word = re.sub(r'(--|—)', '\n<emdash>\n', word) 
                # 5+dots are a dotleader
                word = re.sub(r'\.\.\.\.\.+', '\n<dotleader>\n', word)
                # 4 or 3-dot ellipsis 
                word =  re.sub(r'[^\.]\.\.\.\.?[^\.]', '\n<ellipsis>\n', word)

                # period
                word = word.replace('.', '\n<period>\n')
                # bang point
                word = word.replace('!', '\n<bang>\n')
                # query
                word = word.replace('?', '\n<query>\n')
                
                # comma
                word = word.replace(',', '\n<comma>\n')
                # semicolon
                word = word.replace(';', '\n<semicolon>\n')
                # colon
                word = word.replace(':', '\n<colon>\n')
                
                # open bracket
                word = word.replace('[', '\n<openbracket>\n')
                # close bracket
                word = word.replace(']', '\n<closebracket>\n')
                # open siingle quote
                word = re.sub(r"^('|‘)", '\n<opensingle>\n', word)
                # close single quote
                word = re.sub(r"(’|')$", '\n<closesingle>\n', word)
                # open double quote
                word = re.sub(r'(^"|“)', '\n<opendouble>\n', word)
                # close double quote
                word = re.sub(r'(”|"$)', '\n<closedouble>\n', word)
                # open parenthese
                word = word.replace('(','\n<openparen>\n')
                # close parenthese
                word = word.replace(')','\n<closeparen>\n')
                # open italic
                word = re.sub(r"^_", '\n<ital>\n', word)
                # close italic
                word = re.sub(r"_$", '\n</ital>\n', word)

                # enclose number in tags
                if '<' not in word:
                    word = re.sub(r"([0-9]+)", r"\n<number>@\1\n", word)

                # write word to file
                fout.write(word + '\n')

            if linepreservation:
                fout.write('<br>\n')
