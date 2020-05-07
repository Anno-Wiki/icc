# ICC

The ICC (Intertextual Canon Cloud) is a web app designed for a collaborative
annotations wiki of public domain literature. The only current instance of this
app can be found at [anno.wiki](https://anno.wiki)

It is currently in development. Documentation will be radically expanded closer
to completion.

Primary files consist of:

## Scripts
1. `preprocessor.py`, designed for preprocessing text/markdown files, originally
   from Project Gutenberg, but hopefully from other sources as well (untested in
   that regard) which performs the following actions:
    - Process double dashes (`--`) into em dashes (— `U+2014`)
    - Process dumb quotes (`'` and `"`) into smart quotes (`‘ ’` and `“ ”`:
      `U+2018`, `U+2019`, `U+201C`, `U+201D`); still requires manual
      intervention, especially for single quotes - Process footnotes within the
      text, based on regex, into csv format such that the
      `icc.insertannotations.py` script can process them into the icc system.
2. `processor.py`, designed for _processing_ the same files into an `*.icc`
   format that I can use the next few scripts to insert in the database. It
   performs the following actions:
    - Process markdown style underscores into icc storable attributes
    - Process markdown style preformatted code marks (triple backticks) into icc
      storable attributes
    - Process markdown style block quotation code marks (`>`) into icc storable
      attributes
    - Process lines into general icc storable csv format
3. `insertlines.py`: a script to process `.icc` files output by `processor.py`
   into the icc database. It ***requires*** a yaml configuration file, so see
   the `-h` flag and the template yaml file for more information.
4. `insertannotations.py`: a script to process `.ano` files output by
   `preprocessor.py` into the icc database. It _also_ ***requires*** some flags.
   See `-h` for more information.
5. `inserttags.py`: a script to process yaml files following a tag yaml file
   template into the system.
6. `insertusers.py`: a script to process yaml files following a user yaml file
   template into the system.
7. `scripts/populate.sh`: a script to automate population of the database using
   the previously enumerated scripts and pregenerated files.
8. `scripts/recreate.sh`: a script to automate recreation of the database using
   `flask db` commands and the `scripts/populate.sh` script.
9. `scripts/repopulate.sh`: a script to automate repopulation of the database
   using `mysql` commands, `flask db upgrade`, and the `scripts/populate.sh`
   script.

## Main application
1. `app/routes.py`: the main application view logic of the app
2. `app/models.py`: the main data logic of the app
3. `app/search.py`: some logic related to elasticsearch
4. `app/funky.py`: some modularized functions for use in `app/routes.py`
5. `app/templates/*`: the templating logic of the app

## The sub applications
1. `app/admin/*`: all admin routes and systems
2. `app/ajax/*`: all ajax routes
3. `app/email/*`: all email routes and systems
4. `app/requests/*`: all routes and templates concerned with the `BookRequest`
   and `TagRequest` systems
5. `app/user/*`: all routes and templates concerned with general user systems.
