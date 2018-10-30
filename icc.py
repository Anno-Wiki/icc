from app import app, db
from app.models import AdminRight, User, Vote, EditVote, Book, Author, Line, \
    Kind, Tag, Annotation, AnnotationVersion, BookRequest, BookRequestVote, \
    UserFlag, UserFlagEvent, AnnotationFlag, AnnotationFlagEvent, \
    NotificationType, NotificationEvent

@app.shell_context_processor
def make_shell_context():
    return {"db": db,
            "AdminRight": AdminRight, "User": User,
            "Vote": Vote, "EditVote": EditVote,
            "Book": Book, "Author": Author,
            "Line": Line, "Kind": Kind, "Tag": Tag,
            "Annotation": Annotation, "AnnotationVersion": AnnotationVersion,
            "BookRequest": BookRequest, "BookRequestVote": BookRequestVote,
            "UserFlag": UserFlag, "UserFlagEvent": UserFlagEvent,
            "AnnotationFlag": AnnotationFlag,
            "AnnotationFlagEvent": AnnotationFlagEvent,
            "NotificationType": NotificationType,
            "NotificationEvent": NotificationEvent }
