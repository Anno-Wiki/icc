from icc import create_app, db
from icc.models import classes

app = create_app()

@app.shell_context_processor
def make_shell_context():
    classes['db'] = db
    classes['es'] = app.elasticsearch
    return classes
