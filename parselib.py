import re
def parse(word):
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

    return word
