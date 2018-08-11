 Key:
    + Not relevant yet
    - Relevant
    x No longer relevant

 x Alright, we solved the basic problem in the javascript: we only need the
   first and last id's from a highlight block. Really elementary solution to the
   whole problem.
 + Still need to implement incremental search on the texts. So my theory is that
   I need to index the books on a line by line basis. Then when I get the result
   from the line, I also pull the previous and next like 3 lines. This allows me
   to have incremental search and get surrounding text in a simple way. This
   would also eliminate need for beautifulsoup.
 - My annotation loop in /read/ routes.py is incredibly slow. It's mostly
   because it's a naive string concatenation loop. It results in a ≈20s load
   time on Heart of Darkness. ((Now that I think about it, I don't actually know
   that that's the case. In fact, it seems silly to think the string
   concatenation is the cause. It only has to perform it for 7-8 annotations so
   far. I need to profile that fucker and figure out exactly what's causing the
   slow down.
    - One possible solution is to implement the /bk/, /pt/, /ch/ read views
      which would limit the amount of lines for processing but this still runs
      into the problem on especially long chapters such as in Ulysses (plus bk's
      in War and Peace are loooonggggg...)
    - Another possible solution is to investigate optimizations. Barring one for
      python I could implement the method in C. May do it anyway.
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
