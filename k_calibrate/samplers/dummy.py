from k_calibrate.calibrate import Sample, Sampler


class _DummySampler(Sampler):
    def sample(self):
        return Sample(data_points={})