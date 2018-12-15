import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    DEBUG = True
    ADMINS = ["emails@futuretld.org"]
    ANNOTATIONS_PER_PAGE = 5
    AUTHORIZATION = { 
            "anonymize_users": -1,
            "approve_edits": -1,
            "create_tags": -1,
            "deactivate_annotations": -1,
            "delete_annotations": -1,
            "delete_book_requests": -1,
            "delete_edits": -1,
            "delete_tag_requests": -1,
            "edit_bios": -1,
            "edit_book_requests": -1,
            "edit_deactivated_annotations": -1,
            "edit_edition_histories": -1,
            "edit_lines": -1,
            "edit_locked_annotations": -1,
            "edit_summaries": -1,
            "edit_tag_requests": -1,
            "edit_tags": -1,
            "immediate_edits": -1,
            "lock_annotations": -1,
            "lock_users": -1,
            "reject_edits": -1,
            "request_books": 100,
            "request_tags": 100,
            "resolve_annotation_flags": -1,
            "resolve_deactivated_annotation_flags": -1,
            "resolve_user_flags": -1,
            "review_edits": 25,
            "review_deactivated_annotation_edits": -1,
            "use_restricted_tags": -1,
            "view_deactivated_annotations": -1,
            }


    # mail system
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 25)
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS") is not None

    # vote margins
    MIN_EDIT_APPROVAL_RATING = 2
    MIN_EDIT_REJECTION_RATING = -2

    # per pages
    ANNOTATIONS_PER_SEARCH_PAGE = 5
    CARDS_PER_PAGE = 15
    COMMENTS_PER_PAGE = 25
    LINES_PER_PAGE = 30
    LINES_PER_SEARCH_PAGE = 10
    NOTIFICATIONS_PER_PAGE = 15

    USER_PAGE_AVATAR_SIZE = 255
    TIME = "%I:%M %p %m/%d/%y (UTC)"

    # technicals
    SECRET_KEY = os.environ.get("SECRET_KEY") or "youllneverguess"
    ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "mysql+pymysql://root@localhost/icc?charset=utf8mb4"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = 0
    #SERVER_NAME = "www.annopedia.org:5000"
