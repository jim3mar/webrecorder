import os

__version__ = '2.0'


# ============================================================================
def get_shared_config_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))) + os.path.sep


