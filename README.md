# ICC

The ICC (Intertextual Canon Cloud) is a web app designed for a collaborative annotations wiki of public domain literature.

It is currently in development.

Primary files consist of:

1. `insertlines.py`: a script to process `.icc` files output by `processor.py` into the icc database
2. `insertannotations.py`: a script to process `.anno` files output by `preprocessor.py` into the icc database
3. `app/routes.py`: the main application view logic of the app
4. `app/models.py`: the main data logic of the app
5. `app/search.py`: some logic related to elasticsearch
6. `app/funky.py`: some modularized functions for use in `app/routes.py`
7. `app/templates/*`: the templating logic of the app

# ICC Processor

The ICC processor consists of two scripts designed to process Project Gutenberg texts into an ICC readable format.

1. `preprocessor.py`, which performs the following actions:
    - Process double dashes (`--`) into em dashes (— `U+2014`)
    - Process dumb quotes (' and ") into smart quotes (‘ ’ “ ” `U+2018`, `U+2019`, `U+201C`, `U+201D`); 
      still requires manual intervention, especially for single quotes
    - Process footnotes within the text, based on regex, into csv format such that the `icc.insertannotations.py`
      script can process them into the icc system.
2. `processor.py`, which performs the following actions:
    - Process markdown style underscores into icc storable attributes
    - Process markdown style preformatted code marks (triple backticks) into icc storable attributes
    - Process markdown style block quotation code marks (`>`) into icc storable attributes
    - Process lines into general icc storable csv format
