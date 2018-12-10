#!/home/malan/projects/icc/icc/venv/bin/python
from datetime import datetime, timedelta
import unittest
from app import app, db
from app.models import *

class MyTest(unittest.TestCase):
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    ELASTICSEARCH_URL = None
    TESTING = True

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_password_hashing(self):
        u = User(displayname="john", email="john@example.com")
        u.set_password("dog")
        self.assertFalse(u.check_password("cat"))
        self.assertTrue(u.check_password("dog"))

    def test_avatar(self):
        u = User(displayname="john", email="john@example.com")
        self.assertEqual(u.avatar(128), 
                ("https://www.gravatar.com/avatar/d4c74594d841139328695756648b6"
                "bd6?d=identicon&s=128"))


if __name__ == "__main__":
    unittest.main()
