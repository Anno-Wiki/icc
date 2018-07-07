import sys

book = sys.argv[3]

with open(sys.argv[1], 'rt') as fin, open(sys.argv[2], 'wt') as fout:
    i = 0
    for line in fin:
        if '@' in line:
            fout.write(f'{str(i)}@{book}@{line}')
        else:
            fout.write(f'{str(i)}@{book}@{line}@0')
        i += 1
