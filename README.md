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
