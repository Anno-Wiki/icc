from icc import create_app, db, classes


app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Make the shell context."""
    classes['db'] = db
    classes['es'] = app.elasticsearch
    return classes
