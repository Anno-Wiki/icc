import sys
import argparse
import io
import re
import yaml
import json

"""Process the pre-formatted and pre-processed (with preprocessor.py) texts into
a json format for the insert scripts to process into the ICC's database.
"""

# Constants
BLANK = re.compile(r'^ *$')
HR = re.compile(r'^\*\*\*$')
QUOTE = re.compile(r'^>')
PRE = re.compile(r'```')
INDENT = re.compile(r'^#+')
INDENT_ENUM = re.compile(r'ind[0-9]*')

ELLIPSE = re.compile(r'[a-zA-Z]+[!,:;&?]?\.{3,5}[!,:;&?]?[a-zA-Z]+')
EMDASH = re.compile(r'[A-Za-z]+[.,;:!?&]?—[.,;:!?&]?[A-Za-z]+')
WORD_BOUNDARY = re.compile(r'\w+|\W')


def readin(fin, matches):
    """Read the file into the script, use the matches dictionary from the yaml
    templating style to process headings and special cases. Returns a list of
    lines of tuple form:

        (emphasis_status, lineclass, line)

    Where emphasis_status is an enum code for whether a line needs to be
    prefixed or postfixed with an `<em>` or `</em>` tag. These are explained
    below:

    - `nem`: No emphasis, leave these lines alone
    - `oem`: Open emphasis, for lines that have open emphasis that needs to be
      closed by postfixing an `</em>` tag.
    - `em`: Emphasis, for lines that need to be both prefixed with `<em>` and
      postfixed with `</em>`
    - `cem`: Closed emphasis, for lines that need to be prepended with `<em>`
      because they close their own emphasis.

    The purpose of all of this is further explained in the documentation section
    titled "On Emphasis".
    """

    class Switch:
        """A stateful switch-style object for handling all of the possible line
        cases when reading a line into an array with identifying labels.
        """

        lines = []
        pre = False
        # We have to properly output the emphasis status of each line based on
        # the number of underscores. It is highly stateful. It is based on
        # underscores like in markdown, but each line needs a certain data value
        # when we render the html so that we can close and open emphasis tags
        # in cases where the underscore emphasis spans lines. This emswitch
        # method is actually quite elegant. Like a turing machine. The first if
        # statement in the `process_line()` method is where the switch is
        # processed.
        emphasis = 'nem'
        emswitch = {
            'nem': 'oem',
            'oem': 'em',
            'em': 'cem',
            'cem': 'nem',
        }

        def __init__(self, matches):
            """Creates three dictionaries of {<regex>: <lambda>} from:
            - the table of contents headings and levels
            - the special designators (e.g., stage directions)
            - syntax space (e.g., quotes, preformatted lines, etc.
            """
            syntaxspace = {
                BLANK: lambda line: self.lines.append(
                    (self.emphasis, 'blank', line.strip())),
                HR: lambda line: self.lines.append(
                    (self.emphasis, 'hr', '<hr>')),
                QUOTE: lambda line: self.lines.append(
                    (self.emphasis, 'quo', line.strip('>').strip())),
                PRE: lambda line: self.switch_pre(),
                INDENT: lambda line: self.lines.append(
                    (self.emphasis, f'ind{line.count("#")}',
                     line.strip('#').strip()))
            }

            toc = matches.get('toc', {})
            specials = matches.get('specials', {})

            tocspace = {
                re.compile(key):
                lambda line, key=key, value=value: self.lines.append(
                    (self.emphasis,
                     value['precedence'],
                     line.strip())
                )
                for (key, value) in toc.items()
            }

            specialsspace = {
                re.compile(key):
                lambda line, value=value: self.lines.append(
                    (self.emphasis, value['enum'], line.strip())
                )
                for key, value in specials.items()
            }

            self.searchspace = {**syntaxspace, **tocspace, **specialsspace}

        def switch_pre(self):
            self.pre = not self.pre

        def process_line(self, line):
            # if the # of underscores is odd
            if line.count('_') % 2:
                # Process the emphasis turing machine.
                self.emphasis = self.emswitch[self.emphasis]

            if self.pre:
                # check if the line is a pre tag to flip the switch before we
                # print it out by accident.
                if re.search(PRE, line):
                    self.searchspace[PRE](line)     # flip the switch
                else:
                    self.lines.append((self.emphasis, 'pre', line.strip()))
            else:
                triggered = False
                for regex in self.searchspace:
                    if re.search(regex, line):
                        self.searchspace[regex](line)
                        triggered = True
                        break

                # if the regex searchspace never made a match, it's just text.
                if not triggered:
                    self.lines.append((self.emphasis, 'text', line.strip()))

            if self.emphasis == 'oem' or self.emphasis == 'cem':
                # 'cem' and 'oem' are one time codes.
                self.emphasis = self.emswitch[self.emphasis]

    switcher = Switch(matches)
    for line in fin:
        switcher.process_line(line)

    return switcher.lines


def readout(lines, matches):
    """Read the list of tuples output from readin and return a list of
    context-aware dictionaries with the following key, value pairs:

    - `line`: The actual line, stripped of whitespace and unnecessary
      formatting.
    - `emphasis`: A number between 0 and 3 corresponding to the enumerated
      emphasis codes to be translated upon load from the orm.
    - `num`: The line number within the text.
    - `attributes`: A dictionary of attributes that describe the context and
      display patterns of the line. They consist of the following key, value
      pairs:
        - `enum`: the actual enum-like code that will be used to generate css
          classes for displaying the lines
        - `display`: the human-readable (or, prettier) version of `enum`, i.e.,
          if the enum is `hr`, the display is 'Horizontal Rule'. This is
          essential for hierarchy attrs, because they are all simply `lvl<n>` in
          the enum.
        - `num`: the number corresponding to the attribute, i.e., chapter 1,
          book 1, etc. This number is 0 for all non-hierarchy attributes.
        - `precedence`: the precedence value of table-of-contents hierarchies
          (see Table of Contents Hierarchies in the documentation for more
          information). A 0 will be used for attributes which do not have
          precedence.
        - `primary`: The status of the particular attribute being primary or
          not; that is to say: if the particular line is the 'Chapter' heading,
          the `primary` value will be `True`. All else will be `False`. Every
          line has one, and only one, primary. It is the classification of the
          line.
    """

    class Switch:
        """A stateful switch-style object for context-based line-by-line
        processing using the output of `readout()`.
        """
        # The object's attributes are
        #
        # 1. searchspace: a dictionary of lambdas for processing all the special
        #    cases
        # 2. tocnums: a dictionary for processing the toc hierarchy numbers and
        #    attributes
        # 3. maxtoc: a simple int of the highest level of toc hierarchy
        #    precedence for this book.
        #
        # The obvious ones are defined below.

        lines = []
        num = 0
        prevline = ''

        def __init__(self, matches):
            """Create the non-trivial class attributes."""
            # attribute dictionaries for specific enums
            DEFAULT = {'num': 0, 'precedence': 0, 'primary': True }
            HR = {'enum': 'hr', 'display': 'Horizontal Rule', **DEFAULT}
            QUO = {'enum': 'quo', 'display': 'Quote', **DEFAULT}
            PRE = {'enum': 'pre', 'display': 'Preformatted Text', **DEFAULT}
            syntaxspace = {
                'blank': lambda line: None,
                'hr': lambda line: self.lines.append(
                    {'line': line[2], 'emphasis': 'nem', 'num': self.num,
                     'attributes': self.hierarchy(line) + [HR]}),
                'quo': lambda line: self.lines.append(
                    {'line': line[2], 'emphasis': line[0], 'num': self.num,
                     'attributes': self.hierarchy(line) + [QUO]}),
                'pre': lambda line: self.lines.append(
                    {'line': line[2], 'emphasis': line[0], 'num': self.num,
                     'attributes': self.hierarchy(line) + [PRE]}),
                INDENT_ENUM: lambda line: self.lines.append(
                    {'line': line[2], 'emphasis': line[0], 'num': self.num,
                     'attributes': self.hierarchy(line) +
                     [{'enum': line[1], 'display': 'Indent', **DEFAULT}]
                     }
                )
            }

            toc = matches.get('toc', {})
            tocspace = {value['precedence']:
                        lambda line, value=value: self.lines.append(
                            {'line': line[2], 'emphasis': line[0],
                             'num': self.num,
                             'attributes': self.hierarchy(line)})
                        for value in toc.values()}

            specials = matches.get('specials', {})
            specialsspace = {value['enum']:
                             lambda line, value=value: self.lines.append(
                                 {'line': line[2], 'emphasis': line[0],
                                  'num': self.num,
                                  'attributes': self.hierarchy(line) +
                                  [{'enum': value['enum'],
                                    'display': value['display'], 'num': 0,
                                    'precedence': 0, 'primary': True}]})
                             for value in specials.values()}

            self.searchspace = {**syntaxspace, **tocspace, **specialsspace}

            self.tocnums = {value['precedence']:
                            {'num': 0, 'aggregate': value['aggregate'],
                             'display': value['display']}
                            for value in toc.values()}
            self.maxtoc = max(self.tocnums.keys())

        def update_toc_nums(self, line):
            """Update the table of contents numbers. If line[1] is not an
            integer, will cause errors. Not to be suppressed.
            """
            self.tocnums[line[1]]['num'] += 1
            # Reset all numbers of lower precedence to 1 if they are not
            # supposed to aggregate.
            for i in range(line[1]+1, self.maxtoc+1):
                if not self.tocnums[i]['aggregate']:
                    self.tocnums[i]['num'] = 0

        def hierarchy(self, line):
            """This method returns a list of toc hierarchy dictionaries. They
            will be used to process attributes per line.
            """
            attrs = []
            for i in range(1, self.maxtoc+1):
                primary = line[1] == i
                num = self.tocnums[i]['num']
                if num > 0:
                    attrs.append(
                        {'enum': f'lvl{i}',
                        'display': self.tocnums[i]['display'],
                        'num': self.tocnums[i]['num'],
                        'precedence': i,
                        'primary': primary})
            return attrs

        def process_line(self, line):
            """This method process the actual line, using all of the other
            methods to format the line dictionary, and appends it to the list
            `self.lines`.
            """
            if not line[1] == 'blank':
                self.num += 1
            triggered = False
            for enum in self.searchspace:
                match = False
                try:
                    match = re.match(enum, str(line[1]))
                except:
                    match = (str(enum) in str(line[1]))
                if match:
                    if enum in self.tocnums.keys():
                        self.update_toc_nums(line)
                    self.searchspace[enum](line)
                    triggered = True
                    self.prevline = enum
                    break
            if not triggered:
                normal_line =  {'enum': 'l', 'display': 'Text Line',
                                'num': self.num, 'precedence': 0, 'primary': True}
                first_line = {'enum': 'fl',
                              'display': 'First Text Line of Paragraph',
                              'num': self.num, 'precedence': 0, 'primary': True}
                classification = first_line if self.prevline == 'blank' else \
                    normal_line
                self.lines.append(
                    {'line': line[2],
                     'attributes': self.hierarchy(line) + [classification],
                     'emphasis': line[0], 'num': self.num})
                self.prevline = classification['enum']

    switcher = Switch(matches)
    for line in lines:
        switcher.process_line(line)

    return switcher.lines


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        """Process the preformatted and preprocessed
        (with preprocessor.py) texts into a json format for the insert scripts
        to process into the ICC's database.
        """)
    parser.add_argument('-i', '--input', action='store', type=str,
                        help="The input file. Defaults to stdin.")
    parser.add_argument('-o', '--output', action='store', type=str,
                        help="The output file. Defaults to stdout.")
    parser.add_argument('-m', '--matches', action='store', type=str,
                        required=True, help="The regex matches yaml file "
                        "(required). See the documentation on Processing Texts "
                        "for more information.")
    args = parser.parse_args()

    FIN = io.open(args.input, 'r', encoding='utf-8-sig') if args.input\
        else open(args.input, 'rt', encoding='utf-8-sig')
    FOUT = sys.stdout if not args.output else open(args.output, 'wt')
    MATCHES = yaml.load(open(args.matches, 'rt'), Loader=yaml.FullLoader)

    linesin = readin(FIN, MATCHES)
    linesout = readout(linesin, MATCHES)
    FOUT.write(json.dumps(linesout))
