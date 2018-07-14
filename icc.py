from app import app, db
from app.models import User, Book, Page, Position, Author

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Book': Book, 'Page': Page, 'Position':
            Position, 'Author': Author}
