# Implementation of regex-based and newline-based flags for chapter processing.

import sys
import re

if len(sys.argv) < 3: 
    sys.exit('Usage:    python book.[v#].py infile outfile [-r /ch/ #][-l # #]')

with open(sys.argv[1], 'rt') as fin, open(sys.argv[2], 'wt') as fout:
    
    # Controller vars
    newline = 0             # Number of new lines since last text
    chapter = False         # Flag for chapter tags
    chnum = 1               # Chapter counter                 
    prevwrite = 'begin'     # holder for previous fout.write()



    ########################################
    ## Parsing chapter processing options ##
    ########################################

    # Flags for chapter processing modes
    regexbased = False      # Flag for regex mode
    linebased = False       # Flag for newline mode

    # regex mode flag activation
    if len(sys.argv) > 3 and sys.argv[3] == '-r':
        regexbased = True
        chkey = re.compile(sys.argv[4])
        chlinestoread = int(sys.argv[5])
        chlinesread = 0

    # newline mode flag activation
    elif len(sys.argv) > 3 and sys.argv[3] == '-l':
        linebased = True
        leader = int(sys.argv[4])
        chlinestoread = int(sys.argv[5])
        chlinesread = 0



    ##############
    ## THE LOOP ##
    ##############

    for line in fin:
        
        ###############################
        ## Print </p> first new line ##
        ##  if prevwrite != chapter  ##
        ###############################

        # process paragraph end 
        if line == '\n' and prevwrite == 'text': 
            newline +=1
            prevwrite = '\n</p>\n'
            fout.write(prevwrite)
            continue


            
        ####################################
        ## Regex based chapter processing ##
        ####################################
        
        # Process new lines, activate chapter flag
        elif regexbased and not chapter and re.match(chkey, line):
            prevwrite = 'chapter'
            chapter = True
            chlinesread += 1
            fout.write('\n' + '<ch>@' + str(chnum) + '\n')
            fout.write('\n' + line[:-1] + '\n')
            if chlinesread >= chlinestoread:
                fout.write('\n</ch>\n')
                chlinesread == 0
                chapter = False
                chnum += 1
                newline = 0
            continue

        elif regexbased and chapter and line != '\n':
            prevwrite = 'chapter'
            chlinesread +=1
            fout.write('\n' + line[:-1] + '\n')
            if chlinesread >= chlinestoread:
                fout.write('\n</ch>\n')
                chlinesread == 0
                chapter = False
                chnum += 1
                newline = 0
            continue
            

        
        ######################################
        ## Newline-based chapter processing ##
        ######################################

        # Process new lines, activate chapter flag
        elif linebased and not chapter and line == '\n':
            newline += 1
            if newline == leader:
                chapter = True
            continue

        # Process a chapter heading
        elif linebased and chapter == True and line != '\n':
            prevwrite = 'chapter'
            if chlinesread == 0:
                fout.write('\n<ch>@' + str(chnum) + '\n')
            fout.write('\n' + line[:-1] + '\n')
            chlinesread += 1
            if chlinesread >= chlinestoread:
                fout.write('\n</ch>\n')
                chapter = False
                chlinesread = 0
                chnum += 1
            newline = 0
            continue

        elif line == '\n':
            newline += 1
            prevwrite = 'newline'
        
        # Catch '\n' if chapter is true to avoid activating the 'else' clause
        elif linebased and chapter == True:
            continue


        ############## 
        ## THE BEEF ##
        ############## 

        elif line != '\n':

            prevwrite = 'text'
            
            # First text after newlines is start of paragraph
            if newline > 0:
                fout.write('\n<p>\n')
                newline = 0
                
            # Split the lines on space
            words = line.split()

            # Process each word before printing
            for word in words:
                
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
                word = re.sub(r"(^'|‘)", '\n<opensingle>\n', word)
                # close single quote
                word = re.sub(r"(’|'$)", '\n<closesingle>\n', word)
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
