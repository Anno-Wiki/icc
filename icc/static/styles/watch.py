from os import stat, walk
from subprocess import call
from time import sleep, time, localtime, asctime


last_seen = 0
for root, dirs, files in walk('.'):
    for name in files:
        if last_seen < stat(name).st_mtime:
            last_seen = stat(name).st_mtime

while True:
    for root, dirs, files in walk('.'):
        for name in files:
            if last_seen < stat(name).st_mtime:
                call(['sass', '-C', 'style.scss', 'style.css'])
                last_seen = stat(name).st_mtime
                print(f"Recompiled {asctime(localtime(time()))}")
            sleep(0.1)
