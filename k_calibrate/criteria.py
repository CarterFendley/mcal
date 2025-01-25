# Built in criteria
from k_calibrate.orchestrate import RunStats


def after_iterations(amount: int):
    def _after_iterations(stats: RunStats):
        return stats.iterations >= amount

    return _after_iterations