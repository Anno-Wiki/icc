from flask import render_template, flash, redirect, url_for, request
from flask_login import logout_user, current_user, login_required

from icc import db
from icc.email.email import send_password_reset_email
from icc.funky import is_filled, generate_next
from icc.forms import AreYouSureForm

from icc.user import user
from icc.user.forms import (EditProfileForm, ResetPasswordRequestForm,
                            ResetPasswordForm)

from icc.models.user import User


@user.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.displayname = (form.displayname.data if
                                    is_filled(form.displayname.data) else
                                    f'user_{current_user.id}')
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your changes have been saved.")
        return redirect(url_for('user.profile', user_id=current_user.id))
    elif request.method == 'GET':
        form.displayname.data = current_user.displayname
        form.about_me.data = current_user.about_me

    return render_template('forms/edit_profile.html', title="Edit Profile",
                           form=form)


@user.route('/profile/delete', methods=['GET', 'POST'])
@login_required
def delete_profile_check():
    form = AreYouSureForm()
    redirect_url = generate_next(url_for('user.profile',
                                         user_id=current_user.id))
    if form.validate_on_submit():
        current_user.displayname = f'x_user{current_user.id}'
        current_user.email = '{current_user.id}'
        current_user.password_hash = '***'
        current_user.about_me = ''
        db.session.commit()
        logout_user()
        flash("Account anonymized.")
        return redirect(redirect_url)

    text = f"""You have clicked the link to delete your account. This page
serves as a double check to make sure that you’re really sure you want to delete
your account. You will not be able to undo this. Annopedia is not like Facebook.
We don’t secretly keep your personal information so you can reactivate your
account later on. If you delete it, it’s done.

Please note, however, that the account itself will not be expunged from our
database. Annopedia is a collaborative effort, and we therefore reserve the
right to retain all of your contributions. This deletion is an anonymization of
your account. Your display name, email address, and about me will all be erased
and anonymized. Every interaction you have ever made with the site will be
associated with an account which cannot be logged into and whose display name
will be `x_user_{current_user.id}` But you will never be able to log back in
and retrieve your account.

If you’re really sure about this, click the button “Yes, I’m sure.” Otherwise,
press back in your browser, or _close_ your browser, or even pull the power cord
from the back of your computer. Because if you click “Yes, I’m sure,” then your
account is gone."""
    return render_template('forms/delete_check.html', title="Are you sure?",
                           form=form, text=text)


@user.route('/password/reset/request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
            flash("Check your email for the instructions to request your "
                  "password.")
            return redirect(url_for('user.login'))
        else:
            flash("Email not found.")
    return render_template(
        'forms/reset_password_request.html', title="Reset Password", form=form)


@user.route('/password/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been changed.")
        return redirect(url_for('user.login'))
    return render_template('forms/reset_password.html', form=form)
