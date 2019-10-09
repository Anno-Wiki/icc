"""Populate the text, authors, edition, writer connections, and lines for a
text. Requires a `meta.yml` file.
"""
import pdb
import sys
import os
import io
import argparse
import yaml
import json

iccvenv = os.environ['ICCVENV']
idx = iccvenv.rfind('/')
sys.path.append(os.environ['ICCVENV'][:idx])

from icc import db, create_app
from icc.models.content import (Text, Edition, Line, TOC, WriterConnection,
                                Writer, WRITERS_REVERSE)


def get_text(meta):
    """Create the text, add the authors, and return the text object added the
    database.
    """
    text = Text.query.filter_by(title=meta['title']).first()
    if text:
        print(f"Found {text.title} in the database.")
        if meta['edition']['primary']:
            print("Deactivating previous primary {text.primary}.")
            deactivate_previous_primary(text)
    else:
        text = Text(title=meta['title'], sort_title=meta['sort_title'],
                    published=meta['publication_date'],
                    description=meta['description'])
        db.session.add(text)
        print(f"Created text {text.title}.")
    return text


def deactivate_previous_primary(text):
    """If this isn't the initial text creation and we're changing the primary
    edition, call this method to deactivate the previous primary.
    """
    if __name__ == '__main__':
        print(f"Deactivated primary designation on edition #{text.primary.num} "
              f"of {text.title}.")
    text.primary.primary = False


def get_edition(meta, text):
    """Create the new edition, add it to the databsae, and return it."""
    # this method is ridiculous and I need to work on making it just
    # dereferencing meta. Don't know why it didn't work.
    edition = Edition(num=meta['num'],
                      verse=meta.get('verse', False),
                      tochide=meta.get('tochide', True),
                      _title=meta.get('title', None), text=text,
                      primary=meta['primary'],
                      description=meta['description'],
                      published=meta['published'])
    db.session.add(edition)
    if __name__ == '__main__':
        if edition._title:
            print(f"Created {edition._title} for {text.title}.")
        else:
            print(f"Created edition number {edition.num} for {text.title}.")
    return edition


def add_writer_connections(meta, edition):
    """Add all of the writer connections to the edition."""
    # For all the connection types we have, we go look in the edition dictionary
    # for those connection types, and then loop through the writers in those
    # dictionaries to create those connections.
    for value, enum in WRITERS_REVERSE.items():
        for writer in meta['edition'][value]:
            writer_obj = Writer.query.filter_by(name=writer['name']).first()
            if not writer_obj:
                writer_obj = Writer(**writer)
                db.session.add(writer_obj)
                if __name__ == '__main__':
                    print(f"Created writer {writer_obj.name}.")

            conn = WriterConnection(writer=writer_obj, edition=edition,
                                           enum_id=enum)
            db.session.add(conn)
            if __name__ == '__main__':
                print(f"Added {writer_obj.name} as {value}.")


def addtoc(line, lasttoc, tocenums, edition):
    """Process a toc."""
    enum = line.pop('enum')
    enum = tocenums[enum] if enum in tocenums else TOC.enum_cls(enum=enum)

    if lasttoc:
        if line['precedence'] == lasttoc.precedence:
            # the new toc is the same level as the lasttoc
            parent = lasttoc.parent
        elif line['precedence'] > lasttoc.precedence:
            # the new toc is deeper in precedence than the lasttoc
            parent = lasttoc
        else:
            # the new toc is higher than the lasttoc
            while lasttoc.precedence > line['precedence']:
                lasttoc = lasttoc.parent
            parent = None if lasttoc.precedence == 1 else lasttoc.parent
    else:
        parent = None
    toc = TOC(**line, enum=enum, edition=edition, parent=parent)
    return toc


def populate_lines(lines, edition):
    """Populate the database with the lines and their attributes. Return the
    count of lines added to the database.
    """
    lineenums = {enum.enum: enum for enum in Line.enum_cls.query.all()}
    tocenums = {enum.enum: enum for enum in TOC.enum_cls.query.all()}
    lasttoc = None
    tocs = []

    for i, line in enumerate(lines):
        if 'precedence' in line:
            lasttoc = addtoc(line, lasttoc, tocenums, edition)
            db.session.add(lasttoc)
        else:
            enum = line.pop('enum')
            enum = (lineenums[enum] if enum in lineenums else
                    Line.enum_cls(enum=enum))
            if not lasttoc.haslines:
                lasttoc.haslines = True
            lineobj = Line(**line, enum=enum, toc=lasttoc, edition=edition)
            db.session.add(lineobj)

        if lasttoc.haslines and not lasttoc.prev:
            if tocs and lasttoc is not tocs[-1]:
                lasttoc.prev = tocs[-1]
            tocs.append(lasttoc)

        if i % 1000 == 0:
            print(i)

    return i


def parse_files(path):
    path = path.rstrip('/')
    meta = yaml.load(open(f'{path}/meta.yml', 'rt'), Loader=yaml.FullLoader)
    fin = io.open(f'{path}/lines.json', 'r', encoding='utf-8-sig')
    lines = json.load(fin)
    return meta, lines


def main(path, dryrun=False, noindex=False):
    meta, lines = parse_files(path)
    text = get_text(meta)
    edition = get_edition(meta['edition'], text)
    add_writer_connections(meta, edition)
    i = populate_lines(lines, edition)
    print(f"After an arduous {i} lines, we are done.")

    if dryrun:
        db.session.rollback()
        print("Nothing committed.")
    else:
        print("Now committing...")
        db.session.commit()
        print(f"Done.")
        if not args.noindex:
            print("Reindexing...")
            Line.reindex(edition=edition)
            print("Done.")
        else:
            print("Skipping indexing.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Insert lines into icc database.")
    parser.add_argument('path', action='store', type=str,
                        help="The input directory. Must contain lines.json and "
                        "meta.yml in the proper format.")
    parser.add_argument('-d', '--dryrun', action='store_true', default=False,
                        help="Flag for a dry run test.")
    parser.add_argument('--noindex', action='store_true', default=False,
                        help="Don't index the lines.")

    args = parser.parse_args()


    app = create_app()

    with app.app_context():
        main(args.path, args.dryrun, args.noindex)
