import os
from tempfile import NamedTemporaryFile

THIS_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

NR_HELM_VALUES_PATH = os.path.join(THIS_DIR, 'newrelic-helm-values.yaml')

def render_file(path: str, data: dict) -> str:
    assert os.path.isfile(path)

    with open(path, 'r') as f:
        file_contents = f.read()

    return file_contents.format(**data)

def render_file_to_temp(path: str, data: dict) -> NamedTemporaryFile:
    rendered = render_file(path, data)

    tmp_file = NamedTemporaryFile(suffix='.yaml')
    with open(tmp_file.name, 'w') as f:
        f.write(rendered)
        f.seek(0) # NOTE: Honestly can't remember if I need to this

    return tmp_file