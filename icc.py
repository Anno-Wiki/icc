from app import app, db, elasticsearch
from app.models import classes

@app.shell_context_processor
def make_shell_context():
    classes['db'] = db
    classes['es'] = elasticsearch
    return classes
