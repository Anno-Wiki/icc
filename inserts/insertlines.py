"""Populate the text, authors, edition, writer connections, and lines for a
text. Requires a `meta.yml` file.
"""
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
    _title = meta.get('title', None)
    edition = Edition(num=meta['number'], verse=meta.get('verse', False),
                      _title=_title, text=text, primary=meta['primary'],
                      description=meta['description'],
                      published=meta['publication_date'])
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


def addtoc(line, prevtoc, tocenums, edition):
    """Process a toc."""
    enum = line.pop('enum')
    enum = tocenums[enum] if enum in tocenums else TOC.enum_cls(enum=enum)

    if prevtoc:
        if line['precedence'] == prevtoc.precedence:
            # the new toc is the same level as the prevtoc
            parent = prevtoc.parent
        elif line['precedence'] > prevtoc.precedence:
            # the new toc is deeper in precedence than the prevtoc
            parent = prevtoc
        else:
            # the new toc is higher than the prevtoc
            while prevtoc.precedence > line['precedence']:
                prevtoc = prevtoc.parent
            parent = None if prevtoc.precedence == 1 else prevtoc.parent
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
    prevtoc = None

    for i, line in enumerate(lines):
        if 'precedence' in line:
            prevtoc = addtoc(line, prevtoc, tocenums, edition)
            db.session.add(prevtoc)
        else:
            enum = line.pop('enum')
            enum = (lineenums[enum] if enum in lineenums else
                    Line.enum_cls(enum=enum))
            db.session.add(Line(**line, enum=enum, toc=prevtoc,
                                edition=edition))

        if i % 1000 == 0:
            print(i)

    return i


def parse_files(path):
    path = path.rstrip('/')
    meta = yaml.load(open(f'{path}/meta.yml', 'rt'), Loader=yaml.FullLoader)
    FIN = io.open(f'{path}/lines.json', 'r', encoding='utf-8-sig')
    lines = json.load(FIN)
    return meta, lines


def main(path, dryrun=False):
    meta, lines = parse_files(path)
    text = get_text(meta)
    edition = get_edition(meta['edition'], text)
    add_writer_connections(meta, edition)
    i = populate_lines(lines, edition)
    print(f"After an arduous {i} lines, we are done.")

    if dryrun:
        db.session.rollback()
        print(f"Nothing committed.")
    else:
        print(f"Now committing...")
        db.session.commit()
        print(f"Done.")
        print(f"Reindexing...")
        Line.reindex(edition=edition)
        print(f"Done.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Insert lines into icc database.")
    parser.add_argument('path', action='store', type=str,
                        help="The input directory. Must contain lines.json and "
                        "meta.yml in the proper format.")
    parser.add_argument('-d', '--dryrun', action='store_true', default=False,
                        help="Flag for a dry run test.")

    args = parser.parse_args()


    app = create_app()

    with app.app_context():
        main(args.path, args.dryrun)
