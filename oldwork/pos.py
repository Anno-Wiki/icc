import sys

if '-b' in sys.argv:
    flag = sys.argv.index('-b')
    book = sys.argv[flag + 1]

with open(sys.argv[1], 'rt') as fin, open(sys.argv[2], 'wt') as fout:
    i = 0
    for line in fin:
        if '@' in line:
            fout.write(str(book) + '@' + str(i) + '@' + line[:-1] + '\n')
        else:
            fout.write(str(book) + '@' + str(i) + '@' + line[:-1] + '@0' + '\n')
        i += 1
