Key:
   + Not relevant yet
   - Relevant
   x No longer relevant

Definitions
===========

- body (of annotation): the text which is being annotated by the annotation
- text (of annotation): the text which describes and annotates the body of the
  annotation

- x Alright, we solved the basic problem in the javascript: we only need the
  first and last id's from a highlight block. Really elementary solution to the
  whole problem.
+ Still need to implement incremental search on the texts. So my theory is that
  I need to index the books on a line by line basis. Then when I get the result
  from the line, I also pull the previous and next like 3 lines. This allows me
  to have incremental search and get surrounding text in a simple way. This
  would also eliminate need for beautifulsoup.
- x My annotation loop in /read/ routes.py is incredibly slow. It's mostly
  because it's a naive string concatenation loop. It results in a ≈20s load
  time on Heart of Darkness. ((Now that I think about it, I don't actually know
  that that's the case. In fact, it seems silly to think the string
  concatenation is the cause. It only has to perform it for 7-8 annotations so
  far. I need to profile that fucker and figure out exactly what's causing the
  slow down.
   - x I _have_ discovered the problem. It is excessive mysql calls. The actual
     query wasn't executed until I reached the for-each loop on the results of
     an `Annotation.query.filter...order_by()` call. By trying to manually
     index the `basequery` object I discovered I had to call `.all()` which
     ended up being just as slow explicitly as it was implicitly in the
     for-each loop.
       - x I need to somehow access a list of `Annotation`'s on an indexed basis.
         That is I need to be able to say `WHERE last_line = i` so that I can
         access those specific items. Then I have one mysql call and it will be
         a ton faster. It looks like it _is_ possible per
         [this SO question/answer](https://stackoverflow.com/questions/28620389/accessing-list-of-python-objects-by-object-attribute).
       - x Okay: so iterating through every annotation for every line (with the
         slightly non-naive modification of breaking when I get to the first
         annotation with a last_line_id greater than the current line) is
         decidedly faster than the previous implementations.
       - x The next implementation (because the current one won't scale at all)
         will be to iterate through all the annotators once before the
         line-by-line iteration and index them in a dictionary. Until I come up
         with a reproducible and slicable hash to do that, this will work for
         now.
       - x Solution: dictionary whereby key is a hash of important attributes and
         value is list of all annotators with those values.
   - x One possible solution is to implement the /bk/, /pt/, /ch/ read views
     which would limit the amount of lines for processing but this still runs
     into the problem on especially long chapters such as in Ulysses (plus bk's
     in War and Peace are loooonggggg...)
   - x Another possible solution is to investigate optimizations. Barring one for
     python I could implement the method in C. May do it anyway.
   - The solution implemented was the indexing method mentioned earlier. I used
     a defaultdict and indexted by line_id. It worked.
- For scripters the edit and create views need to have a way to display the
  lines in question with arrows on the top and bottom to extend the view to
  lines above and below and show a js overlay highlight and even possibly have
  arrows for the highlight overlay so an exact highlight is easy.
- For scripters I also want the ability to display annotations inline in the
  read view.
- For scripters (and everyone, really) there should be an option to display the
  lines purely (as in broken at <line>'s), or loosely. linenums could
  _theoretically_ be computed to still display at the lines where the line
  begins in loose breaking.
- The current styles for setting the line numbers are totally deficient and need
  to be fixed. They don't port to other screen sizes (for the obvious reason
  that I'm doing it with absolute positioning). What should I expect when I
  steal it from MIT?
- Line numbers ought to be unhighlightable like github's. I'll have to
  investigate that.
- I not at all sure that I like the current method of voting. I think I need to
  make user power growth logarithmic rather than linear. I am not sure where I
  would like a user's power to more or less top off, but I am thinking around
  25 points for an upvote (250 personal karma). That said, I would rather
  someone with 250 personal karma didn't have 25 points. I'd rather they had
  maybe 10. All voting power should be int(p)
```
k(arma)     p(ower)     f(actor)
1-10        1           p = 1
20          2           p = k / 10
30          3           p = k / 10
...         ...         ...
100         10          p = k / 10
110         11          p = k / 100 + 10
...         ...         ...
200         12          p = k / 100 + 10
300         13          p = k / 100 + 10
...         ...         ...
900         19          p = k / 100 + 10 
1000        20          p = k / 100 + 10
1100        21          p = k / 1000 + 20
...         ...         ...
10000       30          p = k / 1000 + 20
11000       31          p = k / 10000 + 30
...         ...         ...
k           p           p = k / 10^log(k) + 10log(k)
```
- I'm pretty sure that's what it is. I'm defining the function in python right
  now:
```
def v(a):
    if a <= 10:
        return 1
    log = round(math.log(a,10))
    return int(a / (10 ** log + 1)) + (10 * log - 10)
```
which seems to maintain its accuracy up to 100 quadrillion more testing is
necessary, but it seems to work. The issue without the round() is that every
couple of magnitudes the accuracy of `log(a, 10)` is not quite a whole number. I
don't at all get why, but it is the case. So if I don't add the 1, the evens
(e.g., 10000) come to `10log - 10 + 1` (e.g., 21 instead of 20 for `v(1000)`. If
I add 1 to 10^log, the cases where it doesn't come out even on `log(a,10)` turn
into `10log - 10 - 1`. I just can't freaking win. However, by rounding, the
cases where `log(a,10)` have a decimal expansion of .9999997 or so are
immediately rounded up to the even equivalency for the good cases, and so we can
just add the 1 and it comes out good.
- That function didn't work for anything _except_ the case where a = 10^n. I
  believe I have a function that will do it, though.
- I believe i got it:
```
def vote_power(reputation):
    if reputation <= 10:
        return 1
    log = int(math.log10(reputation) - (math.log10(11) - int(math.log10(11))))
    return int(reputation / 10**log) + 10*log - 10
```
- That actually seems to do exactly the trick. I don't fully get why. There's an
  extra `0.004139268...` in `log(10^n + 10^(n-1))` for `n >= 1`. By subtracting 
  it from the calculated log we get the chart above. _I really don't understand
  why it isn't transparent_. That said, I am also unsure if this is the result
  of floating-point arithmetic or the actual nature of the math.
- No, crap. This is stupid. Now, it does follow my chart, but my chart is
  stupid! How does this make sense? For every step, it jumps 1 based on one
  10^n-1, and then only one for every subsequent 10^n! We end up with this:
```
k(arma)     p(ower)
100         10
110         11
120         11
130         11
...         ...
190         11
200         12
250         12
300         13
400         14
...         ...
1000        20
1100        21
1200        21
...         ...
2000        22
...         ...
```
You see! But in reality, the math without that little
`math.log10(11) - int(math.log10(11))` hack doesn't really make sense either.
Then I have
```
k(arma)     p(ower)
99          9
100         11
110         11
...         ...
190         11
200         12
300         13
...         ...
999         19
1000        21
...         ...
```
Which doesn't make sense either! You jump two and never have a 10n voting power?
I think I need to just establish every 10n based on 10^n and then every 
`(10^n) + 1` is immediately incremented 1. I think that actually makes the most
logical sense. Back to the drawing board. It's Sun Sep  2 23:14:35 EDT 2018 and
I think I'm goint to go to sleep.
- I got it.
```
import math
def u(k):
    if k <= 10:
        return 1
    elif k == 10**int(math.log10(k)):
        log = int(math.log10(k) - (math.log10(11) - int(math.log10(11))))
        return int(k / 10**log) + 10*log - 10
    log = int(math.log10(k))
    return int(k / 10**log) + 10*log - 10
```
---
Sun Sep  9 21:12:20 EDT 2018
- For linking I don't _need_ any kind of special tag or system. Sure, I can't
  get the users to specially select individual characters, but just linking to a
  particular line on a page (describing how to do it to them) allows the user to
  build context. For an example.

Hamlet here references `[John 10:29](https://icc.com/read/the_bible/john#23)`.

would take you to the twenty-third line of the book of john (speaking of this,
I'll have to do something about handling the Bible in particular; I also still
have to implement separate things for act/scene).
- TLD's:
    1. .org
    2. .info
    3. .io
- The processor is now capable of doing line printing in the format I need for
  entering into mysql.
- I need to get argparse working.
- In order to realign all the lines in a text we need the following code snippet
  for vim:

```
G:a

.
:g/^./ .,/^$/-1 join
```
- The highlighted (linked) text will need to be displayed in an AJAX-based
  window. I _will_ need AJAX.
    - Actually, if I load all the data right away, I don't need it. So perhaps
      not. However, generating new link targets will need AJAX.  (see next
      note).
- To allow a user to search a new piece of text I will need AJAX.
    - The user will have to be presented with a browsing method and a searching
      method. The searching method will probably be the best.  However, real
      links are not 1:1's. So simply searching will not always be effective.
      Furthermore, it would require a user to know what is _worth_ searching
      for. Algorithmically searching for cross-text would generate a wealth of
      false positive 1:1's (e.g.  the:the).
- It would be highly useful for there to be a 'link' style page. That is, a page
  that can be used to show text from two works laid side by side to show the
  link. As in:
```
    Not a whit, we defy augury: there's a special
    providence in the fall of a sparro. If it be now,
    'tis not to come; if it be not to come, it will be
    now; if it be not now, yet it will come: the
    readiness is all: since no man has aught of what he
    leaves, what is't to leave betimes?
```
  on the left and 
  
  >[29] Are not two sparrows sold for a farthing? and one of
  them shall not fall on the ground without your Father. [30] But the very hairs
  on your head are all numbered. [31] Fear ye not therefore, ye are of more
  value than many sparrows.

  on the right.
- I like Wikipedia's idea of limiting advertising to search pages. But I am
  leary about seeming commercial. Fuck. I'm getting infected by GNU-syndrome.
- Apparently I should avoid natural joins.
- Handler for parsing data. Needs to read pos and next pos and determine whether
  to add a space afterwards or not. This could become more complicated down the
  road when considering idiosycratic writers (The different uses of ellipses,
  for instance). Caveat: normalizing styles across authors might not be a
  terrible idea, though I could theoretically handle different uses of ellipses
  through specifying ellipses.
- Epigraph indicators
- python book.??.py infile outfile [first]
- Body indicators
- Bracketted numbers for citations
- \>4 .'s for separation - They're called dotleaders
- line preservation for poetry.
- space preservation for based on >1 leading spaces
- regular brackets (i.e. not containing number)
- put a pass:# print for the first freaking line. That way we can activate and
  deactivate various features (like number reading). This would decomplexify a
  ton of tasks.
- Create a tag data input for chapter/part headings. This would allow you to
  parse the chapter heads on the first run through and then they don't matter
  anymore
- Test for actual em dash in utf8-encoding U+2014 —
- Ensure <emdash> can handle space pre <emdash>
- Questionable combinations:
    - :—
    - " —Text.
- It might behoove me to create chapter links in lengthy texts. I can do this
  with a slight modification to the <ch> tags, that is, keep a running count and
  include an identifier. I have a number column now, this could work.
- Alice in Wonderland has a very peculiar asterisk pattern
- I'm going to have to opt for curly's. This is going to be difficult. For the
  records:
    - ‘ Curly single open U+2018
    - ’ Curly single close U+2019
    - “ Curly double open U+201c
    - ” Curly double close U+201d
    - This is going to be eminently difficult for ellided words as the
      apostrophe's preferred rendering is a closed single.
- Our biggest problem seems to be irregular line breaking. We may be able to
  overcome this through notes on lines 8 and 12.
- Meta data table should include strict pagination
- Pagination should be optional.
- The Meta Table is going to have to be pretty fucking sophisticated. We're
  going to have to have a 'genre' system: fiction, nonfiction, drama, and
  poetry. This way we can include meta information pertaining to each category
  in the meta table. The DP for instance, will have to be in the meta table.
- It seems that surrounding _ are used for some purpose around latin/foreign
  text
- Need to run at least two passes due to the regex matching
- There are edge cases for single quotes: 'im, 'em, etc. Elision. It fucks it
  up.
- I think that one method to track edge cases is to run the resulting dictionary
  through an actual dictionary and print any words not in it.  Then eliminate
  hyphenated words. That should result in a list of the edge cases to be
  investigated. If there are too many I can worry about it then.
- Next question to ask on stackoverflow is how to process a list into mysql such
  that the list matches a pre-existing dictionary (you know what the fuck you
  mean). ((Actually, as of Mon Aug 13 09:03:38 EDT 2018 I already forgot.))
- The Psalms pose a serious issue for chapter headings.
