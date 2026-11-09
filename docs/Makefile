PYTHON ?= python
SPHINXBUILD ?= sphinx-build
SPHINXOPTS ?= -n -W --keep-going

.PHONY: html check linkcheck clean

html:
	$(SPHINXBUILD) $(SPHINXOPTS) -d _build/doctrees -b html . _build/html

check: html
	cd .. && $(PYTHON) -m experiments.docs_check docs/_build/html

linkcheck:
	$(SPHINXBUILD) $(SPHINXOPTS) -b linkcheck . _build/linkcheck

clean:
	$(PYTHON) -c "import shutil; shutil.rmtree('_build', ignore_errors=True)"
