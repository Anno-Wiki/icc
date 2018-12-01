INSERT INTO notification_enum (code, public_code, entity_type, notification,
    vars) VALUES

    ("edit_approved",
        "Edit approved",
        "EditVote",
        "Edit #{} on [{}] of {} by {}",
        "edit.edit_num,edit.annotation_id,edit.book.title,edit.book.author.name")
    ,

    ("edit_rejected",
        "Edit rejected",
        "EditVote",
        "Edit #{} on [{}] of _{}_ by {}",
        "edit.edit_num,edit.annotation_id,edit.book.title,edit.book.author.name")
    ;
