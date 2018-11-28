from app import app, db, elasticsearch
from app.models import Right, User, Vote, EditVote, Book, Author, Line, \
    LineLabel, Tag, Annotation, Edit, BookRequest, BookRequestVote, \
    UserFlag, UserFlagEvent, AnnotationFlag, AnnotationFlagEvent, \
    NotificationType, NotificationEvent, TagRequest, TagRequestVote

@app.shell_context_processor
def make_shell_context():
    return {"db": db,
            "Right": Right, "User": User,
            "UserFlag": UserFlag, "UserFlagEvent": UserFlagEvent,
            "NotificationType": NotificationType,
            "NotificationEvent": NotificationEvent,

            "Vote": Vote, "EditVote": EditVote,

            "Book": Book, "Author": Author,
            "BookRequest": BookRequest, "BookRequestVote": BookRequestVote,

            "Line": Line, "LineLabel": LineLabel, 
            "Annotation": Annotation, "Edit": Edit,
            "AnnotationFlag": AnnotationFlag,
            "AnnotationFlagEvent": AnnotationFlagEvent,

            "Tag": Tag,
            "TagRequest": TagRequest, "TagRequestVote": TagRequestVote,

            "es" : elasticsearch }
