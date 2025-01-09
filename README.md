# k-calibrate

```bash
conda create --name k-calibrate python
conda activate k-calibrate
```

```bash
python -m pip install -e '.[dev]'
```

## Running tests

```bash 
coverage erase && python -m pytest --cov clean_tree
tox -e cov_clean,py312
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