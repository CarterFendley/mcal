# k-calibrate

```bash
conda create --name k-calibrate python
conda activate k-calibrate
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
python -m pytest --cov k_calibrate
python -m pytest --cov k_calibrate --slow # With slow tests

# Run full test suite across all versions
# Note: Tox will run slow tests
tox
tox -m single_version
```

### Kubernetes

The following instructions are for creating a [kind cluster](https://kind.sigs.k8s.io/)

```
kind create cluster
```

Bootstrap newrelic integration into the cluster (based on instructions [here](https://docs.newrelic.com/install/kubernetes)).

```
kc dev nr-bootstrap
```

List clusters connected to NR

```
kc dev list-clusters
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