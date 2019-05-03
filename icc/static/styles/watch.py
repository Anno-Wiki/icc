from os import stat
from subprocess import call
from time import sleep, time, localtime, asctime

filename = "style.scss"
last_seen = stat(filename).st_mtime

while True:
    if last_seen < stat(filename).st_mtime:
        call(['sass', 'style.scss', 'style.css'])
        last_seen = stat(filename).st_mtime
        print(f"Recompiled {asctime(localtime(time()))}")
    sleep(0.1)
