"""The error system."""
from flask import render_template, url_for
from icc import app, db
from icc.funky import generate_next


@app.errorhandler(404)
def not_found_error(error):
    """My 404"""
    redirect_url = generate_next(url_for("index"))
    return render_template("errors/404.html", redirect_url=redirect_url), 404


@app.errorhandler(500)
def internal_error(error):
    """My 500, for internal server error, which I see too much of too often."""
    db.session.rollback()
    redirect_url = generate_next(url_for("index"))
    return render_template("errors/500.html", redirect_url=redirect_url), 500


@app.errorhandler(403)
def forbidden_error(error):
    """My 403 error, for when someone goes somewhere they're not supposed to go.
    """
    redirect_url = generate_next(url_for("index"))
    return render_template("errors/403.html", redirect_url=redirect_url), 403
