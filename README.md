# Multi Calibrate

A multi-purpose calibration tool.

## Local setup

```bash
conda create --name mcal python
conda activate mcal
```

```bash
# Editable install
python -m pip install -e .
# Dev dependencies
python -m pip install -e '.[dev]'
# Docs dependencies
python -m pip install -e '.[docs]'
# All dependencies
pip install -e '.[all]'
```

## Running tests

```bash 
python -m pytest --cov mcal
python -m pytest --cov mcal --slow # With slow tests

# Run full test suite across all versions
# Note: Tox will run slow tests
tox
tox -m single_version
```

### Dev Kubernetes

Install the following:
- Kind
- Kubectl
- Helm

Setup cluster

```bash
# Create kind cluster
mcal dev cluster create
# Configure KUBECONFIG to use created cluster
$(mcal dev cluster setup)
```

Apply needed configurations

```bash
mcal dev cluster apply MetricsServer
mcal dev cluster apply NRI
mcal dev cluster apply DaskOperator
```

Delete cluster after finished
```bash
mcal dev cluster delete-all
```

### Releasing

Update the version in `pyproject.toml`
```
version='X.Y.Z'
```

Create a git tag and push
```
git tag vX.Y.Z
git push --tags
```

Then create a release via github.

#### If you mess up and need to edit things

Remove old tag and re-tag
```
git tag -d vX.Y.Z
git tag vX.Y.Z

git push -f --tags
```

Delete previous github release and re-create.

# TODO:
- Pixie?
- Prometheus 