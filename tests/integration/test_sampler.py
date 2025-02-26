from pathlib import Path

import pandas as pd
import pytest

from mcal.utils.cmd import run_cmd


def test_sampler_doesnt_exist():
    result = run_cmd(
        args=['mcal', '-vvv', 'sampler', 'run', 'SamplerDoesNotExist'],
        expected_return_codes=[1],
        capture_output=True
    )

    assert "Unable to find sampler with name: 'SamplerDoesNotExist'" in result.stderr.decode()

@pytest.mark.parametrize(
    "num_files", (0, 1, 2, 3)
)
def test_sampler_execution(tmpdir: Path, num_files: int):
    tmpdir = Path(tmpdir)
    for i in range(num_files):
        (tmpdir / f'file_{i}.txt').touch()

    result = run_cmd(
        args=['mcal', '-vvv',
              'sampler', 'run', '_DummyFileCount',
              f'--directory={tmpdir}'
        ],
        capture_output=True
    )

    # TODO: This is a pretty awkward validation until the sample data can be saved alone.
    expected = pd.DataFrame([{'file_count': num_files}])
    assert f"{expected}" in result.stdout.decode()