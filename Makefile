PYTHON ?= python3
export PYTHONDONTWRITEBYTECODE = 1
export CUDA_VISIBLE_DEVICES =
export OMP_NUM_THREADS = 1
export MKL_NUM_THREADS = 1
export OPENBLAS_NUM_THREADS = 1
export TMPDIR ?= $(CURDIR)/.scratch
export MPLCONFIGDIR = $(TMPDIR)/matplotlib

.PHONY: smoke cinc2012-smoke findings verify
smoke:
	@mkdir -p "$(TMPDIR)"
	$(PYTHON) -B -m unittest discover -s tests -v
	$(PYTHON) -B src/organ_graph_ssm_model.py
	$(PYTHON) -B src/cvsim_hemodynamics_simulator.py --selftest
cinc2012-smoke:
	@mkdir -p "$(TMPDIR)"
	$(PYTHON) -B tools/cinc2012/smoke.py
findings:
	$(PYTHON) -B tools/summarize_results.py --check
verify:
	sha256sum --quiet -c SHA256SUMS
