# Modularized dramatis personae processor

import sys

with open(sys.argv[1], 'rt') as fin, open(sys.argv[2], 'wt') as fout:
    dp = False
    misc = False
    desc = False
    charnum = 1
    chars = {}

    for line in fin:
        
        # Turn on dp processing 
        if line == '<dp>':
            dp = True
            fout.write(line)

        # Turn off dp processsing 
        elif line == '</dp>':
            dp = False
            fout.write(line)

        # Process character and add it to the dictionary
        elif '<char>' in line:
            a = line.find('>')
            b = line.find('|')

            fout.write('<char>@' + str(charnum))
            fout.write(line[a+1:b])
            fout.write('</char>')

            fout.write('<chardesc>@' + str(charnum))
            fout.write(line[b+1:])
            fout.write('</chardesc>')

            chars[line[a+1:b]] = charnum

            charnum += 1

        elif
