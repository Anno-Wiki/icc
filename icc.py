from app import app, db, elasticsearch
from app.models import Right, User, Vote, EditVote, Text, Writer, Line, \
    LineEnum, Tag, Annotation, Edit, BookRequest, BookRequestVote, \
    UserFlagEnum, UserFlag, AnnotationFlagEnum, AnnotationFlag, \
    TagRequest, TagRequestVote, ReputationChange, ReputationEnum, \
    Notification, NotificationEnum, NotificationObject, Edition

@app.shell_context_processor
def make_shell_context():
    return {"db": db,

            "User": User,
            "Right": Right,
            "Notification": Notification, "NotificationEnum": NotificationEnum,
            "NotificationObject": NotificationObject,
            "ReputationChange": ReputationChange,
            "ReputationEnum": ReputationEnum,
            "UserFlag": UserFlag, "UserFlagEnum": UserFlagEnum,

            "Vote": Vote, "EditVote": EditVote,

            "Text": Text, "Edition": Edition, "Writer": Writer,
            "BookRequest": BookRequest, "BookRequestVote": BookRequestVote,

            "Line": Line, "LineEnum": LineEnum, 
            "Annotation": Annotation, "Edit": Edit,
            "AnnotationFlag": AnnotationFlag,
            "AnnotationFlagEnum": AnnotationFlagEnum,

            "Tag": Tag,
            "TagRequest": TagRequest, "TagRequestVote": TagRequestVote,

            "es" : elasticsearch }
