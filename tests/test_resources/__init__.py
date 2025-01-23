import os

TEST_RESOURCES_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

ENV_FILE = os.path.join(TEST_RESOURCES_DIR, 'env.toml')
ENV_FILE_EMPTY = os.path.join(TEST_RESOURCES_DIR, 'env_empty.toml')
ENV_BAD_FILE = os.path.join(TEST_RESOURCES_DIR, 'env_bad_file.txt')