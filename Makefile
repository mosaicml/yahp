.PHONY: setup lint 


lint:
# Lint does not automatically add licensing, as that 
	yapf -ri .
	isort .
	pyright .

patch:
	bumpversion patch

minor:
	bumpversion minor

major:
	bumpversion major

validate_version:
# Validates that the verison is consistent and set correctly
	bumpversion --no-tag --no-commit --new-version $(shell python setup.py --version) none
	git diff --exit-code
