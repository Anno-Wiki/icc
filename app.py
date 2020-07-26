from icc import create_app

app = create_app()

@app.shell_context_processor
def make_shell_context():
    """Make the shell context."""
    from icc import classes, db
    classes['db'] = db
    classes['es'] = app.elasticsearch
    return classes
