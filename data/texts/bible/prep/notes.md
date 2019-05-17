1. lvl1: Testament
    - regex is just `/Testament/`
2. lvl2: Book
    - regex is complex
        1.  `/Book/`
        2.  `/^Ezra$/`
        3.  `/Ecclesiastes/`
        4.  `/Song/`
        5.  `/Lamentations/`
        6.  `/^Hosea$/`
        7.  `/^Joel$/`
        8.  `/^Amos$/`
        9.  `/^Obadiah$/`
        10. `/^Jonah$/`
        11. `/^Micah$/`
        12. `/^Nahum$/`
        13. `/^Habakkuk$/`
        14. `/^Zephaniah$/`
        15. `/^Haggai$/`
        16. `/^Zechariah$/`
        17. `/^Malachi$/`
        18. `/Gospel/`
        19. `/Acts/`
        20. `/Epistle/`
        21. `/Devine/`
3. lvl3: Chapter // I am not going to do these
    - This one will take special work. I think I have to either write a special
      script to process it or just do it manually. I have to add lines for each
      chapter.
4. lvl4: Verse
    - Now this is the final question. Do I keep the chapter:verse numbers for
      each line? Does each verse get it's own section? I'm beginning to think
      not. This will affect highlights/annotations but IDK that I care. This
      also makes me question sectionizing chapters. I might skip it. TBD later.
      Perhaps discuss with Ethan first. As a result I am pausing this process on
      the Bible.

The book regex is:
```
/
    (
        (Book|Ecclesiastes|Song|Lamentations|Gospel|Acts|Epistle|Devine)
        |
        (
            ^(
                Ezra|
                Hosea|
                Joel|
                Amos|
                Obadiah|
                Jonah|
                Micah|
                Nahum|
                Habakkuk|
                Zephaniah|
                Malachi
            )$
        )
    )
/
```

on one line for copy-pasta:
```
/((Book|Ecclesiastes|Song|Lamentations|Gospel|Acts|Epistle|Devine)|(^(Ezra|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Malachi)$))/
```
