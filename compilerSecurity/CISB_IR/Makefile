.PHONY: test generate run run-sanitized clean

PYTHON ?= python3

# Standard-library unit tests; do not require LLVM tools.
test:
	$(PYTHON) -m unittest discover -s tests -v

generate:
	$(PYTHON) -m cisb_hunter.mutations --cases cases --out generated-cases

# Run seed cases. Set OPT/CLANG/ALIVE_TV if tools are not on PATH.
run:
	$(PYTHON) -m cisb_hunter --cases cases --out artifacts/seed-run --passes instcombine,simplifycfg,gvn --sanitizers none $(if $(OPT),--opt "$(OPT)",) $(if $(CLANG),--clang "$(CLANG)",) $(if $(ALIVE_TV),--alive-tv "$(ALIVE_TV)",)

run-sanitized:
	$(PYTHON) -m cisb_hunter --cases cases --out artifacts/sanitized-run --passes instcombine,simplifycfg,gvn --sanitizers address,undefined $(if $(OPT),--opt "$(OPT)",) $(if $(CLANG),--clang "$(CLANG)",) $(if $(ALIVE_TV),--alive-tv "$(ALIVE_TV)",)

clean:
	rm -rf generated-cases artifacts
