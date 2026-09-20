.PHONY: help catalog harvest harvest-status privacy validate test lint-email all

EMAIL_SKILL ?= skills/padosoft-email-html-builder
EMAIL       ?= $(EMAIL_SKILL)/templates/reference-welcome-dark.html
SUBJECT     ?= Your account is ready: start here

help:            ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "};{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

catalog:         ## Regenerate CATALOG.md, profiles.json and the catalog inside the router skill
	python3 scripts/build_catalog.py

harvest:         ## What changed in the know-how of the repositories you harvest from
	python3 scripts/harvest.py scan

harvest-status:  ## What has been considered, and what is still pending
	python3 scripts/harvest.py status

privacy:         ## No skill may carry the provenance of the work it was learned from
	python3 skills/padosoft-skill-creator/scripts/check_provenance.py skills/

validate:        ## Validate every SKILL.md and the catalog consistency
	@for d in skills/*/; do python3 $(EMAIL_SKILL)/scripts/validate_skill.py "$$d" || exit 1; done
	python3 scripts/build_catalog.py --check
	python3 scripts/validate_plugins.py

test:            ## Run all the tests
	python3 -m unittest discover -s tests -v

lint-email:      ## Lint an email: make lint-email EMAIL=path/to/email.html
	python3 $(EMAIL_SKILL)/scripts/lint_email.py $(EMAIL) --subject "$(SUBJECT)"

all: privacy validate test lint-email ## All the checks (same as CI)
