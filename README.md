# icc

The ICC (Intertextual Canon Cloud) is a web app designed for a collaborative annotations wiki of public domain literature.

It is currently in development.

Primary files consist of:

1. `insertlines.py`: a script to process `.icc` files output by `processor.py` into the icc database
2. `insertannotations.py`: a script to process `.anno` files output by `preprocessor.py` into the icc database
3. `app/routes.py`: the main application view logic of the app
4. `app/models.py`: the main data logic of the app
5. `app/templates/*`: the templating logic of the app
