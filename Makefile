SHELL = /bin/sh
# Determine the Operating System
OSFLAG :=
ifeq ($(OS),Windows_NT)
	OSFLAG=WIN32
else
	UNAME_S := $(shell uname -s)
	ifeq ($(UNAME_S),Linux)
		OSFLAG=LINUX
	endif
	ifeq ($(UNAME_S),Darwin)
		OSFLAG=OSX
	endif
endif

# Installs pipenv
pipenv:
ifeq ($(OSFLAG),WIN32)
	@pip install -U pipenv; 
endif
ifeq ($(OSFLAG),LINUX)
	@sudo -H pip install -U pipenv; 
endif

# Installs pipenv, VS Code & VS Code extensions
dev-env-setup:
ifeq ($(OSFLAG),LINUX)
	@make pipenv; \
	sudo apt update; \
	sudo apt install software-properties-common apt-transport-https wget; \
	wget -q https://packages.microsoft.com/keys/microsoft.asc -O- | sudo apt-key add -; \
	sudo add-apt-repository "deb [arch=amd64] https://packages.microsoft.com/repos/vscode stable main"; \
	sudo apt install code; \
	code --install-extension ms-python.python;
else
	@echo "Please download and install VS Code and install the Python extension"
endif

# Opens the editor
vscode:
	@pipenv run code .; \

# Installs the dependencies in pipenv
install:
	@export PIPENV_VENV_IN_PROJECT=true; \
	pipenv install; \
	make update;

update:
	@pip freeze > requirements.txt; \
	pipenv update; \ 


test:
	@pipenv run pytest -v; \

run:
	#@pipenv run pytest;
ifeq ($(OSFLAG),LINUX)
	@make test; \
	sudo kill `sudo lsof -t -i:5000`; \
	pipenv run flask run
endif
ifeq ($(OSFLAG),WIN32)
	@pipenv run python src\main.py
endif

db:
	export FLASK_APP=apprunner.py; \
	flask db init; \ 
	flask db migrate -m "Initial database build"; \
	flask db upgrade; 


dist:
	@pipenv run pytest; \
	pipenv run python setup.py sdist; \

# Clean the repository of generated files
clean:
	@make clean-env; \
	make clean-dist; \
	make clean-nb; \

clean-env:
	@rm -rf .venv; \
	rm -rf .env; \

clean-dist:
	@rm -rf dist; \
	rm -rf *.egg-info; \
	rm -rf MANIFEST; \

clean-nb:
	@rm -rf .ipynb_checkpoints; \
