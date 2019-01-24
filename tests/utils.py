import re

def get_token(data):
    m = re.search(b'<input id="csrf_token" name="csrf_token" type="hidden" value="(.*)">', data)
    return m.group(1).decode("utf-8")
