import logging
import os
from typing import Optional

import pytest

from mcal import files
from mcal.files import load_file, load_to_temp_file
from mcal.utils.logging import get_logger

logger_name = files.__name__

def test_load_file_failure():
    with pytest.raises(AssertionError):
        load_file('some/path/that_does_not_exist.txt')

@pytest.mark.parametrize(
    "file, arguments, expected",
    [
        ("dummy/my_file.txt", None, "My text!"),
        ("dummy/my_renderable.txt", {'my_argument': "My argument!"}, "My argument!")
    ]
)
def test_str_loading(caplog, file: str, arguments: Optional[dict], expected: str):
    output = load_file(file, arguments)
    assert output == expected

    # Test rendered logging
    caplog.clear()
    logger = get_logger(logger_name)
    logger.setLevel(logging.DEBUG)
    load_file(file, arguments, log_rendered=True)
    
    file_path = os.path.join(files.THIS_DIR, file)
    assert (
        logger_name,
        logging.DEBUG,
        "Rendered file '%s':\n%s" % (file_path, expected)
    ) in caplog.record_tuples

def test_tmp_file_loading():
    tmp_file = load_to_temp_file(
        file="dummy/my_renderable.txt",
        arguments={'my_argument': "My argument!"}
    )

    with open(tmp_file.name, 'r') as f: 
        assert f.read() == "My argument!"
