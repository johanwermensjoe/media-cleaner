#!/usr/bin/env python

import os
import media_tools
import sys
import argparse
import time

__version__ = "1.0.1"

# Main cleaning function.
def clean():
    # Check if safemode is enabled.
    if args.safemode:
        media_tools.log(flags, "Safemode enabled, not changing any files.", 1)
    else:
        media_tools.log(flags, "Safemode disabled, all changes will be applied.", 1)
    
    # Finish the log header. 
    if args.cron:   
        media_tools.log(flags, "------------------------------------------------", 1)
        
    # Clean what was specified.
    if args.movie:
        # Find the library path.
        if args.movie_dir:
            rootDir = args.movie_dir     
        else:
            # Get path from yaml file.
            rootDir = media_tools.get_value_from_yaml(args.config, "path", "movie")
        media_tools.log(flags, "\nRunning movie cleanup script on: " + rootDir, 1)
        media_tools.clean_movie(flags, rootDir)
        
    if args.tv:
        # Find the library path.
        if args.tv_dir:
            rootDir = args.tv_dir  
        else:
            # Get path from yaml file.
            rootDir = media_tools.get_value_from_yaml(args.config, "path", "tv")
        
        media_tools.log(flags, "\nRunning tv-serie cleanup script on: " + rootDir, 1)
        media_tools.clean_tv(flags, rootDir)
    
    # Check if in cron-mode and write extra log info.
    if args.cron:
        media_tools.log(flags, "\n------------------------------------------------", 1)

# Parse arguments.
parser = argparse.ArgumentParser(description='Cleans and renames media files.')

parser.add_argument('-V', '--version', action='store_true', \
    help='shows the version')
    
group_vq = parser.add_mutually_exclusive_group()
group_vq.add_argument('-v', '--verbose', action='store_true', \
    help='enables verbose mode')
group_vq.add_argument("-q", "--quiet", action="store_true", \
    help='enables quiet mode')
parser.add_argument('-c', '--cron', action='store_true', \
    help='enables cron mode with extra log output')

parser.add_argument('-s', '--safemode', action='store_true', \
    help='disables any file changes')
parser.add_argument('-f', '--force', action='store_true', \
    help='force clean and ignore torrent activity')
    
parser.add_argument('-t', '--tv', action='store_true', \
    help='clean tv-series directory' )
parser.add_argument('-m', '--movie', action='store_true', \
    help='clean movie directory')
parser.add_argument('--movie-dir', \
    help='path to movie directory')
parser.add_argument('--tv-dir', \
    help='path to tv-series directory')
    
parser.add_argument('--config', \
    help='path to the yaml file containing media paths')
    
args = parser.parse_args()
flags = {'safemode':args.safemode, 'verbose':args.verbose, 'quiet':args.quiet}

# Check path args.
if args.tv and not args.tv_dir and not args.config:
    media_tools.log(flags, "No path set for tv library, see --tv-dir or --config", 1)
    quit()
if args.movie and not args.movie_dir and not args.config:
    media_tools.log(flags, "No path set for movie library, see --movie-dir or --config", 1)
    quit()

# Check if in cron-mode and write extra log info.
if args.version:
    media_tools.log(flags, __version__, 1)
    quit()

# Check if in cron-mode and write extra log header info.
if args.cron:
    media_tools.log(flags, "\n------------------------------------------------", 1)
    media_tools.log(flags, "Running cleanup: " + time.strftime("%a %Y-%m-%d %H:%M:%S") + "\n", 1)

# Check if torrent activity should be ignored.
if args.force:
    media_tools.log(flags, "Force enabled, skipping torrent activity check.", 1)
    # Start cleanup.
    clean()
else:
    # Do torrent activity check and start cleanup.
    media_tools.deluge_run_if_no_torrents(clean)
