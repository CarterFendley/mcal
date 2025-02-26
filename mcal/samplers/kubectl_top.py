from io import StringIO

import pandas as pd
from kubernetes.utils import quantity

from mcal.calibrate import Sampler
from mcal.utils.cmd import is_cmd, run_cmd


class KubectlTop(Sampler):
    def __init__(self, command: str, namespace: str = None):
        if not is_cmd('kubectl'):
            raise RuntimeError("This sampler relies on 'kubectl' which could not be found.")

        if command not in ('pod', 'node'):
            raise NotImplementedError("Not implemented for command: %s" % command)
        self.command = command
        if namespace is not None:
            self.namespace = f'--namespace={namespace}'
        else:
            self.namespace = '--all-namespaces'

    def sample(self) -> pd.DataFrame:
        result = run_cmd(
            ['kubectl', 'top', self.command, self.namespace],
            capture_output=True
        )

        stdout = result.stdout.decode()
        df = pd.read_csv(StringIO(stdout), delimiter='\s+')

        # Parse the quantity
        df['CPU(cores)'] = df['CPU(cores)'].map(quantity.parse_quantity)
        df['MEMORY(bytes)'] = df['MEMORY(bytes)'].map(quantity.parse_quantity)

        return df