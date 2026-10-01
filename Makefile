.PHONY: init validate db publish
init:
	python3 -m ota init
validate:
	python3 -m ota experiment validate experiments/manifests/EXP-000001.yaml
db:
	python3 -m ota database init
publish:
	python3 -m ota publish
