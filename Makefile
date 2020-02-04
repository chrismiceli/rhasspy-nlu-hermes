SHELL := bash
PYTHON_NAME = rhasspynlu_hermes
PACKAGE_NAME = rhasspy-nlu-hermes
SOURCE = $(PYTHON_NAME)
PYTHON_FILES = $(SOURCE)/*.py tests/*.py *.py
SHELL_FILES = bin/* debian/bin/*
PIP_INSTALL ?= install

.PHONY: reformat check dist venv test pyinstaller debian deploy

version := $(shell cat VERSION)
architecture := $(shell bash architecture.sh)

debian_package := $(PACKAGE_NAME)_$(version)_$(architecture)
debian_dir := debian/$(debian_package)

ifneq (,$(findstring -dev,$(version)))
	DOCKER_TAGS = -t "rhasspy/$(PACKAGE_NAME):$(version)" -t "rhasspy/$(PACKAGE_NAME):latest"
else
	DOCKER_TAGS = -t "rhasspy/$(PACKAGE_NAME):$(version)"
endif

DOCKER_PLATFORMS = linux/amd64,linux/arm64,linux/arm/v7,linux/arm/v6

# -----------------------------------------------------------------------------
# Python
# -----------------------------------------------------------------------------

reformat:
	black .
	isort $(PYTHON_FILES)

check:
	flake8 $(PYTHON_FILES)
	pylint $(PYTHON_FILES)
	mypy $(PYTHON_FILES)
	black --check .
	isort --check-only $(PYTHON_FILES)
	bashate $(SHELL_FILES)
	yamllint .
	pip list --outdated

venv:
	scripts/create-venv.sh

test:
	coverage run --source=$(SOURCE) -m unittest discover tests
	coverage report -m
	coverage xml

coverage:
	coverage report -m

dist: sdist debian

sdist:
	python3 setup.py sdist

# -----------------------------------------------------------------------------
# Docker
# -----------------------------------------------------------------------------

docker-deploy:
	echo "$$DOCKER_PASSWORD" | docker login -u rhasspy --password-stdin
	docker buildx build . --platform $(DOCKER_PLATFORMS) --push $(DOCKER_TAGS)

# -----------------------------------------------------------------------------
# Debian
# -----------------------------------------------------------------------------

pyinstaller:
	mkdir -p dist
	pyinstaller -y --workpath pyinstaller/build --distpath pyinstaller/dist $(PYTHON_NAME).spec
	tar -C pyinstaller/dist -czf dist/$(PACKAGE_NAME)_$(version)_$(architecture).tar.gz $(SOURCE)/

debian: pyinstaller
	mkdir -p dist
	rm -rf "$(debian_dir)"
	mkdir -p "$(debian_dir)/DEBIAN" "$(debian_dir)/usr/bin" "$(debian_dir)/usr/lib"
	cat debian/DEBIAN/control | version=$(version) architecture=$(architecture) envsubst > "$(debian_dir)/DEBIAN/control"
	cp debian/bin/* "$(debian_dir)/usr/bin/"
	cp -R pyinstaller/dist/$(PYTHON_NAME) "$(debian_dir)/usr/lib/"
	cd debian/ && fakeroot dpkg --build "$(debian_package)"
	mv "debian/$(debian_package).deb" dist/
