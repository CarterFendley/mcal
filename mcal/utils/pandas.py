import json
import os
from typing import Tuple

import pandas as pd


def save_dtypes(path: str, df: pd.DataFrame, overwrite: bool = False):
    if not overwrite:
        assert not os.path.exists(path)

    dtypes_dict = df.dtypes.apply(lambda x: x.name).to_dict()

    with open(path, 'w') as f:
        json.dump(dtypes_dict, f)

def load_dtypes(path: str) -> Tuple[dict, list]:
    """
    This method will load a previously saved json file by `save_dtypes` and return the arguments needed to load a CSV via `pd.read_csv(...)`. Specifically `dtype` and `parse_dates`.

    **NOTE:** The use of `parse_dates` is needed because pd.read_csv(...) currently (version `2.2.3`) explodes when providing `datetime[ns, UTC]`

    General reference: https://stackoverflow.com/questions/21269399/datetime-dtypes-in-pandas-read-csv

    Args:
        path (str): Path to the file saved by `save_dtypes`

    Returns:
        Tuple[dict, list]: The `dtype` and `parse_dates` arguments to `read_csv` respectively.
    """

    # TODO: For `datetime[ns, UTC]` this will currently remove the UTC in the type

    with open(path, 'r') as f:
        dtypes_dict = json.load(f)

    parse_dates = []
    for name, value in dtypes_dict.items():
        if value.startswith('datetime'):
            parse_dates.append(name)

    for name in parse_dates:
        del dtypes_dict[name]

    return dtypes_dict, parse_dates