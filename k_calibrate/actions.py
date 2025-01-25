import os
import time

from k_calibrate.orchestrate import RunStats


def _dummy_file_create(directory: str, prefix: str = ''):
    def __dummy_file_create(stats: RunStats):
        file_path = os.path.join(directory, f'{prefix}{stats.iterations}.txt')
        with open(file_path, 'w') as f:
            pass

    return __dummy_file_create

def _dummy_delayed_action(delay: float):
    def __dummy_delayed_action(stats: RunStats):
        time.sleep(delay)

    return __dummy_delayed_action