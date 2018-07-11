# Implementation of regex-based and newline-based flags for chapter processing.

import sys
import re
from parselib import parse

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

                word = parse(word)

                # write word to file
                fout.write(word + '\n')

            if linepreservation:
                fout.write('<br>\n')
