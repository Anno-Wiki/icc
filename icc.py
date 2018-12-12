from app import app, db, elasticsearch
from app.models import Right, User,\
        Notification, NotificationEnum, NotificationObject,\
        ReputationChange, ReputationEnum,\
        UserFlagEnum, UserFlag,\
        Vote, EditVote,\
        Text, Edition, Writer,\
        WriterEditionConnection, ConnectionEnum,\
        TextRequest, TextRequestVote,\
        Line, LineEnum,\
        Annotation, Edit,\
        AnnotationFlag, AnnotationFlagEnum,\
        Tag, TagRequest, TagRequestVote

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
            "WriterEditionConnection": WriterEditionConnection,
            "ConnectionEnum": ConnectionEnum,
            "TextRequest": TextRequest, "TextRequestVote": TextRequestVote,

            "Line": Line, "LineEnum": LineEnum, 
            "Annotation": Annotation, "Edit": Edit,
            "AnnotationFlag": AnnotationFlag,
            "AnnotationFlagEnum": AnnotationFlagEnum,

            "Tag": Tag,
            "TagRequest": TagRequest, "TagRequestVote": TagRequestVote,

            "es" : elasticsearch }
