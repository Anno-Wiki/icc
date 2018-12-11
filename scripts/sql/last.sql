INSERT INTO authors (writer_id, text_id) VALUES
    (
        (SELECT id FROM writer WHERE name="Joseph Conrad"),
        (SELECT id FROM text WHERE title="Heart of Darkness")
    )
    ,
    (
        (SELECT id FROM writer WHERE name="Leo Tolstoy"),
        (SELECT id FROM text WHERE title="War and Peace")
    )
    ;
