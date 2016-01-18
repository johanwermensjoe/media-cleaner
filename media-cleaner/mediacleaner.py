#!/usr/bin/env python

"""
mediacleaner module:
The main media cleaner script.
"""

import mediatools
from mediatools import log, TextType
import argparse
import time

__version__ = "1.1"

# Main cleaning function.
def clean(flags, args):
    """ Cleans libraries . """
    # Check if safemode is enabled.
    if args.safemode:
        log(flags, "Safemode enabled, not changing any files.", \
                            TextType.INFO)
    else:
        log(flags, "Safemode disabled, all changes will be applied.", \
                            TextType.INFO)

    # Finish the log header.
    if args.cron:
        log(flags, "-------------------------" + \
                            "-----------------------", TextType.INFO)

    # Clean what was specified.
    if args.movie:
        # Find the library path.
        if args.movie_dir:
            root_dir = args.movie_dir
        else:
            # Get path from yaml file.
            root_dir = mediatools.get_value_from_yaml(args.config, \
                                                        "path", "movie")
        log(flags, "\nRunning movie cleanup script on: " + root_dir, \
                            TextType.INFO)
        mediatools.clean_movie(flags, root_dir)

    if args.tv:
        # Find the library path.
        if args.tv_dir:
            root_dir = args.tv_dir
        else:
            # Get path from yaml file.
            root_dir = mediatools.get_value_from_yaml(args.config, \
                                                        "path", "tv")

        log(flags, "\nRunning tv-serie cleanup script on: " + \
                            root_dir, TextType.INFO)
        mediatools.clean_tv(flags, root_dir)

    # Check if in cron-mode and write extra log info.
    if args.cron:
        log(flags, "-------------------------" + \
                            "-----------------------", TextType.INFO)

########################## Argument Parsing #############################
#########################################################################

def parse_args_and_execute():
    """ Parses arguments and executes requested operations. """
    # Parse arguments.
    parser = argparse.ArgumentParser(description=\
                                'Cleans and renames media files.')

    parser.add_argument('-V', '--version', action='store_true', \
        help='shows the version')

    group_vq = parser.add_mutually_exclusive_group()
    group_vq.add_argument('-v', '--verbose', action='store_true', \
        help='enables verbose mode')
    group_vq.add_argument("-q", "--quiet", action="store_true", \
        help='enables quiet mode')
    parser.add_argument('-c', '--color', action='store_true', \
        help='enables colored log output')
    parser.add_argument('-C', '--cron', action='store_true', \
        help='enables cron mode with extra log output')

    parser.add_argument('-s', '--safemode', action='store_true', \
        help='disables any file changes')
    parser.add_argument('-f', '--force', action='store_true', \
        help='force clean and ignore torrent activity')

    parser.add_argument('-t', '--tv', action='store_true', \
        help='clean tv-series directory')
    parser.add_argument('-m', '--movie', action='store_true', \
        help='clean movie directory')
    parser.add_argument('--movie-dir', \
        help='path to movie directory')
    parser.add_argument('--tv-dir', \
        help='path to tv-series directory')

    parser.add_argument('--config', \
        help='path to the yaml file containing media paths')

    args = parser.parse_args()
    flags = {'safemode':args.safemode, \
            'verbose':args.verbose, \
            'quiet':args.quiet, \
            'color':args.color}

    # Check path args.
    if args.tv and not args.tv_dir and not args.config:
        log(flags, "No path set for tv library, see " + \
                            "--tv-dir or --config", TextType.INFO)
        quit()
    if args.movie and not args.movie_dir and not args.config:
        log(flags, "No path set for movie library, see " + \
                            "--movie-dir or --config", TextType.INFO)
        quit()

    # Check if in cron-mode and write extra log info.
    if args.version:
        log(flags, __version__, TextType.INFO)
        quit()

    # Check if in cron-mode and write extra log header info.
    if args.cron:
        log(flags, "-------------------------" + \
                            "-----------------------", TextType.INFO)

        log(flags, "Running cleanup: " + \
                            time.strftime("%a %Y-%m-%d %H:%M:%S") + \
                            "\n", TextType.INFO)

    # Check if torrent activity should be ignored.
    if args.force:
        log(flags, "Force enabled, skipping torrent " + \
                            "activity check.", TextType.INFO)
        # Start cleanup.
        clean(flags, args)
    else:
        # Do torrent activity check and start cleanup.
        mediatools.deluge_run_if_no_torrents(clean)


############################ Start script ###############################
#########################################################################
parse_args_and_execute()
