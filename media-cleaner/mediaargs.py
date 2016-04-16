"""
gbpxargs module:
Contains argument identifiers.
"""
from enum import Enum


class Flag(Enum):
    """ Execution flag identifiers. """
    VERBOSE = 'verbose'
    QUIET = 'quiet'
    COLOR = 'color'
    SAFEMODE = 'safemode'


class Option(Enum):
    """ Execution option identifiers. """
    VERSION = 'version'
    CRON = 'cron'
    FORCE = 'force'
    TV_SERIES = 'tv'
    MOVIE = 'movie'
    CONFIG = 'config'
    MOVIE_DIR = 'movie-dir'
    TV_SERIES_DIR = 'tv-dir'
