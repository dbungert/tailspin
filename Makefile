
APP:=python3 -m tailspin

run:
	$(APP) -er3 ./scripts/quick 10

color:
	$(APP) -r 1 ls -al --color=yes

jq:
	$(APP) -r 3 jq '.' tailspin/test/data/sample.json

reader:
	$(APP) -r 1 ./scripts/reader /var/log/syslog

aaaaa:
	$(APP) yes $(shell python3 -c "print('A' * $(shell tput cols))")

run-depends:
	sudo apt install python3-urwid

check: unit lint

unit:
	python3 -m unittest discover

lint:
	flake8 --exclude scripts
