import os

THIS_DIR = os.path.abspath(os.path.dirname(__file__))

BAD_NOT_YAML = os.path.join(THIS_DIR, 'bad_not_yaml.txt')
BAD_NOT_CONFIG = os.path.join(THIS_DIR, 'bad_not_config.yml')
BAD_INVALID_SAMPLER = os.path.join(THIS_DIR, 'bad_invalid_sampler.yml')
BAD_INVALID_SCHEDULE = os.path.join(THIS_DIR, "bad_invalid_scheduler.yml")
BAD_INVALID_STOP_ONE = os.path.join(THIS_DIR, 'bad_invalid_stop_criteria_one.yml')
BAD_INVALID_STOP_TWO = os.path.join(THIS_DIR, 'bad_invalid_stop_criteria_two.yml')
BAD_INVALID_STOP_THREE = os.path.join(THIS_DIR, 'bad_invalid_stop_criteria_three.yml')
BAD_INVALID_STOP_FOUR = os.path.join(THIS_DIR, 'bad_invalid_stop_criteria_four.yml')


COMPLETE_CONFIG = os.path.join(THIS_DIR, "complete_config.yml")
WITH_ARGUMENTS = os.path.join(THIS_DIR, 'with_arguments.yml')