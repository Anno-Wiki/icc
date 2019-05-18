"""Populate the text, authors, edition, writer connections, and lines for a
text. Requires a `config.yml` file.
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
from icc.models.content import (Text, Edition, Line, LineEnum, LineAttribute,
                                WriterConnection, Writer, EMPHASIS_REVERSE,
                                WRITERS_REVERSE)


def get_text(config):
    """Create the text, add the authors, and return the text object added the
    database.
    """
    text = Text.query.filter_by(title=config['title']).first()
    if text:
        print(f"Found {text.title} in the database.")
        if config['edition']['primary']:
            print("Deactivating previous primary {text.primary}.")
            deactivate_previous_primary(text)
    else:
        text = Text(title=config['title'], sort_title=config['sort_title'],
                    published=config['publication_date'],
                    description=config['description'])
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


def get_edition(config, text):
    """Create the new edition, add it to the databsae, and return it."""
    edition = Edition(num=config['edition']['number'],
                      _title=config['edition']['title'], text=text,
                      primary=config['edition']['primary'],
                      description=config['edition']['description'],
                      published=config['edition']['publication_date'])
    db.session.add(edition)
    if __name__ == '__main__':
        if edition._title:
            print(f"Created {edition._title} for {text.title}.")
        else:
            print(f"Created edition number {edition.num} for {text.title}.")
    return edition


def add_writer_connections(config, edition):
    """Add all of the writer connections to the edition."""
    # For all the connection types we have, we go look in the edition dictionary
    # for those connection types, and then loop through the writers in those
    # dictionaries to create those connections.
    for value, enum in WRITERS_REVERSE.items():
        for writer in config['edition'][value]:
            writer_obj = Writer.query.filter_by(name=writer['name']).first()
            if not writer_obj:
                writer_obj = Writer(**writer)
                db.session.add(writer_obj)
                if __name__ == '__main__':
                    print(f"Writer {writer_obj.name} created.")

            conn = WriterConnection(writer=writer_obj, edition=edition,
                                           enum_id=enum)
            db.session.add(conn)
            if __name__ == '__main__':
                print(f"Writer {writer_obj.name} added as {value}.")


def get_enums_dict():
    enums_list = LineEnum.query.all()
    enums_dict = {f'{e.enum}>{e.display}': e for e in enums_list}
    return enums_dict


def process_attributes(attrs_dict, enums_dict):
    """Process the attribute dictionary from the a line, creating LineEnums as
    we need them, and return both a list of attrs to be applied to the line and
    the updated enums dictionary with the newly created enums.
    """
    attrs = {}
    for attr in attrs_dict:
        enum = enums_dict.get(f"{attr['enum']}>{attr['display']}")
        if not enum:
            enum = LineEnum(enum=attr['enum'], display=attr['display'])
            enums_dict[f'{enum.enum}>{enum.display}'] = enum
        a = LineAttribute(enum_obj=enum, num=attr['num'],
                          precedence=attr['precedence'],
                          primary=attr['primary'])
        attrs[a.precedence] = a
    return attrs, enums_dict


def populate_lines(lines, edition):
    """Populate the database with the lines and their attributes. Return the
    count of lines added to the database.
    """

    enums = get_enums_dict()
    i = 0
    for line in lines:
        attrs, enums = process_attributes(line['attributes'], enums)
        line_obj = Line(edition=edition, num=line['num'],
                        em_id=EMPHASIS_REVERSE[line['emphasis']],
                        line=line['line'], attrs=attrs)
        db.session.add(line_obj)

        if i % 1000 == 0 and __name__ == '__main__':
            print(i)
        i+=1

    return i


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Insert lines into icc database")
    parser.add_argument('-c', '--config', action='store', type=str,
                        required=True, help="A yaml configuration file "
                        "adhering to a specific template. See Text Processing "
                        "in the documentation for details.")
    parser.add_argument('-i', '--input', action='store', type=str,
                        help="The input file or prepared and preprocessed "
                        "text.")
    parser.add_argument('-d', '--dryrun', action='store_true',
                        help="Flag for a dry run test.")

    args = parser.parse_args()
    config = yaml.load(open(args.config, 'rt'), Loader=yaml.FullLoader)
    FIN = io.open(args.input, 'r', encoding='utf-8-sig') if args.input\
        else open(args.input, 'rt', encoding='utf-8-sig')
    lines = json.load(FIN)

    app = create_app()

    with app.app_context():
        text = get_text(config)

        edition = get_edition(config, text)

        add_writer_connections(config, edition)

        i = populate_lines(lines, edition)

        print(f"After an arduous {i} lines, we are done.")
        if  args.dryrun:
            db.session.rollback()
            print(f"Nothing committed.")
        else:
            print(f"Now committing...")
            db.session.commit()
            print(f"Done.")
            print(f"Reindexing...")
            Line.reindex(edition=edition)
            print(f"Done.")
