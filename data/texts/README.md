Text Collection for the ICC
===========================
This is the collection of processed texts for the ICC. The current directory
structure is thus:

    /
    /text_template.yml
    /<acronym_of_text_title>/
    /<acronym_of_text_title>/<TitleOfTextbyNameOfAuthor>.icc
    /<acronym_of_text_title>/<TitleOfTextbyNameOfAuthor>.ano
    /<acronym_of_text_title>/<acronym_of_text_title>.yml
    /<acronym_of_text_title>/prep/

The reason for the camelcase in the main data files is because it is inherited
from Project Gutenberg. The reason for the acronyms is for convenience. Both of
these customs may change in time.

Eventually, when additional editions are added to the base texts, these will be
subdirectories within each directory. This specification is not established yet.

The file `text_template.yml` is a template for how to specify a base text
configuration file. Eventually, an `edition_template.yml` file will be added for
further editions. The edition defined in `text_template.yml` is the base primary
edition.

Eventually I will add a specification for the structure of `prep/`. It is
currently a hodgepodge based on the history of how I've processed the `.icc`
files.
