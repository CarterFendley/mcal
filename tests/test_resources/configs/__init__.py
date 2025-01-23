import os

THIS_DIR = os.path.abspath(os.path.dirname(__file__))

BAD_NOT_YAML = os.path.join(THIS_DIR, 'bad_not_yaml.txt')
BAD_NOT_CONFIG = os.path.join(THIS_DIR, 'bad_not_config.yml')
BAD_INVALID_SAMPLER = os.path.join(THIS_DIR, 'bad_invalid_sampler.yml')
BAD_INVALID_SCHEDULE = os.path.join(THIS_DIR, "bad_invalid_scheduler.yml")

COMPLETE_CONFIG = os.path.join(THIS_DIR, "complete_config.yml")
WITH_ARGUMENTS = os.path.join(THIS_DIR, 'with_arguments.yml')