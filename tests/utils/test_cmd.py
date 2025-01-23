import pytest
from test_resources.fixtures import ExecutableSpec

from k_calibrate.utils.cmd import CommandException, is_cmd, run_cmd


def test_is_cmd_false():
    assert is_cmd("does_not_exist") == False
def test_is_cmd_true(with_executable):
    cmd_path = with_executable()
    assert is_cmd(cmd_path) == True

def test_run_cmd_basic(with_executable):
    # No errors on very simple usage
    cmd_path = with_executable(
        ExecutableSpec(return_code=0)
    )
    run_cmd([cmd_path])

    # Protects against non-zero by default
    cmd_path = with_executable(
        ExecutableSpec(return_code=1)
    )
    with pytest.raises(CommandException):
        run_cmd([cmd_path])

def test_run_cmd_with_protection(with_executable):
    cmd_path = with_executable(
        ExecutableSpec(return_code=1)
    )
    run_cmd(
        [cmd_path],
        expected_return_codes=(0, 1)
    )

    cmd_path = with_executable(
        ExecutableSpec(return_code=42)
    )
    with pytest.raises(CommandException):
        run_cmd(
            [cmd_path],
            expected_return_codes=(0, 1)
        )

def test_stderr_forwarding(with_executable, capsys):
    cmd_path = with_executable(
        ExecutableSpec(echo_stderr="My stderr text!")
    )
    run_cmd(
        [cmd_path],
        capture_output=True
    )

    captured = capsys.readouterr()
    assert captured.err == (
        f"stderr forwarded from '{cmd_path}':\n"
        '---------------------------\n'
        "My stderr text!\n\n" # For some reason the shell / subprocess or something is adding multiple newlines
        '---------------------------\n'
    )
