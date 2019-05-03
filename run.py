from icc import create_app
import os

app = create_app()

extra_dirs = ['icc/static', 'icc/main/templates']
extra_files = extra_dirs[:]
for extra_dir in extra_dirs:
    for dirname, dirs, files in os.walk(extra_dir):
        for filename in files:
            filename = os.path.join(dirname, filename)
            if os.path.isfile(filename):
                extra_files.append(filename)
app.run(extra_files=extra_files, host='0.0.0.0')
