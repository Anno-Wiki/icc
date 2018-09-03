Key:
   + Not relevant yet
   - Relevant
   x No longer relevant

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
- That actually seems to do exactly the trick. I don't fully get why.
