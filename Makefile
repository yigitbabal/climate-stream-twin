IMAGE ?= cstwin:0.1.0
WORK  ?= work

.PHONY: install test run docker-build docker-run k3s-import k3s-deploy argo-submit

install:        ## editable install with test deps
	pip install -e ".[dev]"

test:
	pytest -q

run:            ## full local run on synthetic data
	cstwin --workdir $(WORK) sample --days 14
	cstwin --workdir $(WORK) run-all
	cstwin --workdir $(WORK) report

docker-build:
	docker build -t $(IMAGE) .

docker-run:     ## same pipeline inside the container
	mkdir -p ci-work && chmod 777 ci-work
	docker run --rm -v $(PWD)/ci-work:/work $(IMAGE) sample --days 14
	docker run --rm -v $(PWD)/ci-work:/work $(IMAGE) run-all
	docker run --rm -v $(PWD)/ci-work:/work $(IMAGE) report

k3s-import:     ## load the local image into k3s containerd (no registry needed)
	docker save $(IMAGE) | sudo k3s ctr -n k8s.io images import -

k3s-deploy:
	./scripts/k3s_setup.sh

argo-submit:
	argo submit -n cstwin k8s/workflow.yaml --watch
