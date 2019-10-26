install:
	python -m venv venv; \
	source venv/bin/activate; \
	pip install --upgrade pip; \
	pip install -r requirements.txt
db:
	mysql -u root --password=$$PW -e "drop database icc; create database icc;" # recreate db
	source venv/bin/activate; flask db upgrade # recreate db structure
	# populate default values
	source venv/bin/activate; \
	python inserts/insertenums.py data/enums.yml; \
	python inserts/insertusers.py data/users.yml -p 'test'; \
	python inserts/inserttags.py data/tags.yml
populate:
	source venv/bin/activate; \
	python inserts/insertlines.py data/library/conrad_joseph/hod; \
	python inserts/insertlines.py data/library/tolstoy_leo/wap; \
	python inserts/insertannotations.py \
		-i data/library/tolstoy_leo/wap/initial_annotations.json\
		-a 'constance-garnett' -t 'War and Peace' -e 1; \
	python inserts/insertlines.py data/library/bible/kjv/kjbo; \
	python inserts/insertlines.py data/library/shakespeare_william/mit/pericles; \
	python inserts/insertlines.py data/library/shakespeare_william/mit/sonnets; \
	python inserts/insertlines.py data/library/shakespeare_william/mit/taming_shrew; \
	python inserts/insertlines.py data/library/austen_jane/pride; \
	python inserts/insertlines.py data/library/austen_jane/sense; \
	for file in data/library/shakespeare_william/mit/processed/*; do \
		python inserts/insertlines.py $$file; \
	done
run:
	source venv/bin/activate; flask run --host=0.0.0.0
run-local:
	source venv/bin/activate; flask run
connect-production:
	export DATABASE_URL='mysql+pymysql://i11qc27cgerk4345:pkgs4zngtm4sfpyw@ui0tj7jn8pyv9lp6.cbetxkdyhwsb.us-east-1.rds.amazonaws.com:3306/f3gujvr9sir9425p';
	export ELASTICSEARCH_URL='https://paas:5cd2d7d67a0321394d2b56548dcc0c6e@thorin-us-east-1.searchly.com'
