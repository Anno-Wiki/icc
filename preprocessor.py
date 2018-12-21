#!/home/malan/projects/icc/icc/venv/bin/python
import re, sys, argparse, codecs, json

parser = argparse.ArgumentParser("Preprocess raw text files for lines.py.")
parser.add_argument("-i", "--input", action="store", type=str, default=None,
        help="Specify input file")
parser.add_argument("-o", "--output", action="store", type=str, default=None,
        help="Specify output file")
parser.add_argument("--aout", action="store", type=str, default=None,
        help="Specify annotation output file.")
parser.add_argument("-a", "--annotated", action="store", type=str, default=None,
        help="Specify regex to recognize when a line is annotated.")
parser.add_argument("-e", "--emdash", action="store_true",
        help="Normalize em dashes.")
parser.add_argument("-q", "--quotes", action="store_true",
        help="Convert dumb quotes to smart quotes (needs manual intervention)")

args = parser.parse_args()

# files
fin = codecs.getreader("utf_8_sig")(sys.stdin.buffer, errors="replace") \
        if not args.input else open(args.input, "rt")
fout = sys.stdout if not args.output else open(args.output, "wt")

# File to output annotation json
aout = open("a.out", "wt") if not args.aout else open(args.aout, "wt")

wordboundary = re.compile(r'\w+|\W|_')  # Wordboundary regex
annotated_regex = re.compile(args.annotated) if args.annotated else None

astack = {}         # Dictionary stack for recording annotated lines

# context flags
us = False
doubleopen = False
skip = False

annotations = []
for line in fin:
    newline = line
    if newline == '\n':
        doubleopen = False

    if annotated_regex:
        if re.search(annotated_regex, newline):
            for m in re.finditer(annotated_regex, newline):
                if m.group() in astack:
                    tmp = newline.replace(m.group(), "", 1)[:-1].strip()
                    amatch = astack.pop(m.group())
                    amatch = amatch.strip(">")
                    amatch = amatch.strip()
                    annotations.append({ "annotation": tmp, "line": amatch })
                    skip = True
                    continue
                else:
                    newline = re.sub(annotated_regex, r'', newline)
                    astack[m.group()] = newline

    if skip:
        skip = False
        continue

    if args.emdash:
        newline = re.sub(r'(--)', r'—', newline) 

    if args.quotes:
        newline = re.sub(r"([^a-zA-Z])'([a-zA-Z—])", r"\1‘\2", newline)
        newline = re.sub(r"'", r"’", newline)

    words = re.findall(wordboundary, newline)

    for i, word in enumerate(words):
        if args.quotes and '"' in word:
            if doubleopen:
                words[i] = re.sub(r'"', r'”', words[i])
                doubleopen = False
            else:
                words[i] = re.sub(r'"', r'“', words[i])
                doubleopen = True

    newline = ''.join(words)

    fout.write(newline)

aout.write(json.dumps(annotations))

if fin is not sys.stdin:
    fin.close()
else:
    fout.flush()
if fout is not sys.stdout:
    fout.close()
aout.close()
