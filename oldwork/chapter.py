# Modularization of chapter/part processing

import re, sys


if len(sys.argv) < 3: 
    sys.exit('Usage:    python book.[v#].py infile outfile [-r /ch/ #][-l # #]')

with open(sys.argv[1], 'rt') as fin, open(sys.argv[2], 'wt') as fout:


    # Controller vars
    newline = 0             # Number of new lines since last text
    chapter = False         # Flag for chapter tags
    chnum = 1               # Chapter counter                 
    prevwrite = 'begin'     # holder for previous fout.write()
    chlinestoread = 1


    # Flags for chapter processing modes
    regexbased = False      # Flag for regex mode
    linebased = False       # Flag for newline mode


    # regex mode flag activation
    if len(sys.argv) > 3 and sys.argv[3] == '-r':
        regexbased = True
        chkey = re.compile(sys.argv[4])
        if len(sys.argv) > 5:
            chlinestoread = int(sys.argv[5])
        chlinesread = 0


    # newline mode flag activation
    elif len(sys.argv) > 3 and sys.argv[3] == '-l':
        linebased = True
        leader = int(sys.argv[4])
        if len(sys.argv) > 5:
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
        elif regexbased and not chapter and re.search(chkey, line):
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
            fout.write('\n')
            newline += 1
            prevwrite = 'newline'
        
        # Catch '\n' if chapter is true to avoid activating the 'else' clause
        elif linebased and chapter == True:
            continue


        ############## 
        ## THE BEEF ##
        ############## 

        elif line != '\n':

            fout.write(line)
