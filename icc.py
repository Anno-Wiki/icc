from app import app, db, elasticsearch
from app.models import Right, User, Vote, EditVote, Book, Author, Line, \
    LineLabel, Tag, Annotation, Edit, BookRequest, BookRequestVote, \
    UserFlag, UserFlagEvent, AnnotationFlag, AnnotationFlagEvent, \
    TagRequest, TagRequestVote, ReputationChange, ReputationEnum, \
    Notification, NotificationEnum, NotificationObject

@app.shell_context_processor
def make_shell_context():
    return {"db": db,

            "User": User,
            "Right": Right,
            "Notification": Notification, "NotificationEnum": NotificationEnum,
            "NotificationObject": NotificationObject,
            "ReputationChange": ReputationChange,
            "ReputationEnum": ReputationEnum,
            "UserFlag": UserFlag, "UserFlagEvent": UserFlagEvent,

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
