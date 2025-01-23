from k_calibrate.calibrate import Sampler


class _DummySampler(Sampler):
    def sample(self):
        return None