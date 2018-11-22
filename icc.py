from app import app, db, elasticsearch
from app.models import AdminRight, User, Vote, EditVote, Book, Author, Line, \
    LineLabel, Tag, Annotation, AnnotationVersion, BookRequest, BookRequestVote, \
    UserFlag, UserFlagEvent, AnnotationFlag, AnnotationFlagEvent, \
    NotificationType, NotificationEvent, TagRequest, TagRequestVote

@app.shell_context_processor
def make_shell_context():
    return {"db": db,
            "AdminRight": AdminRight, "User": User,
            "UserFlag": UserFlag, "UserFlagEvent": UserFlagEvent,
            "NotificationType": NotificationType,
            "NotificationEvent": NotificationEvent,

            "Vote": Vote, "EditVote": EditVote,

            "Book": Book, "Author": Author,
            "BookRequest": BookRequest, "BookRequestVote": BookRequestVote,

            "Line": Line, "LineLabel": LineLabel, 
            "Annotation": Annotation, "AnnotationVersion": AnnotationVersion,
            "AnnotationFlag": AnnotationFlag,
            "AnnotationFlagEvent": AnnotationFlagEvent,

            "Tag": Tag,
            "TagRequest": TagRequest, "TagRequestVote": TagRequestVote,

            "es" : elasticsearch }
