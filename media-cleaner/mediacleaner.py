#!/usr/bin/env python

"""
mediacleaner module:
The main media cleaner script.
"""

import mediatools
import argparse
import time

__version__ = "1.1"

# Main cleaning function.
def clean(flags, args):
    """ Cleans libraries . """
    # Check if safemode is enabled.
    if args.safemode:
        mediatools.log("Safemode enabled, not changing any files.", flags, 1)
    else:
        mediatools.log("Safemode disabled, all changes will be applied.", \
                            flags, 1)

    # Finish the log header.
    if args.cron:
        mediatools.log("------------------------------------------------", \
                            flags, 1)

    # Clean what was specified.
    if args.movie:
        # Find the library path.
        if args.movie_dir:
            root_dir = args.movie_dir
        else:
            # Get path from yaml file.
            root_dir = mediatools.get_value_from_yaml(args.config, \
                                                        "path", "movie")
        mediatools.log("\nRunning movie cleanup script on: " + root_dir, \
                            flags, 1)
        mediatools.clean_movie(root_dir, flags)

    if args.tv:
        # Find the library path.
        if args.tv_dir:
            root_dir = args.tv_dir
        else:
            # Get path from yaml file.
            root_dir = mediatools.get_value_from_yaml(args.config, \
                                                        "path", "tv")

        mediatools.log("\nRunning tv-serie cleanup script on: " + root_dir, \
                            flags, 1)
        mediatools.clean_tv(root_dir, flags)

    # Check if in cron-mode and write extra log info.
    if args.cron:
        mediatools.log("\n------------------------------------------------", \
                            flags, 1)

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
    parser.add_argument('-c', '-cron', action='store_true', \
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
            'quiet':args.quiet}

    # Check path args.
    if args.tv and not args.tv_dir and not args.config:
        mediatools.log("No path set for tv library, see --tv-dir or --config", \
                            flags, 1)
        quit()
    if args.movie and not args.movie_dir and not args.config:
        mediatools.log("No path set for movie library, see --movie-dir or " + \
                            "--config", flags, 1)
        quit()

    # Check if in cron-mode and write extra log info.
    if args.version:
        mediatools.log(__version__, flags, 1)
        quit()

    # Check if in cron-mode and write extra log header info.
    if args.cron:
        mediatools.log("\n------------------------------------------------", \
                            flags, 1)
        mediatools.log("Running cleanup: " + \
                            time.strftime("%a %Y-%m-%d %H:%M:%S") + \
                            "\n", flags, 1)

    # Check if torrent activity should be ignored.
    if args.force:
        mediatools.log("Force enabled, skipping torrent activity check.", \
                            flags, 1)
        # Start cleanup.
        clean(flags, args)
    else:
        # Do torrent activity check and start cleanup.
        mediatools.deluge_run_if_no_torrents(clean)


############################ Start script ###############################
#########################################################################
parse_args_and_execute()
