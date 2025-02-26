# Built in criteria
from mcal.runner.models import RunStats


def after_iterations(amount: int):
    def _after_iterations(stats: RunStats):
        return stats.iterations >= amount

    return _after_iterations