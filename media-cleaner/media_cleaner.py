import os
import media_tools
import sys
import argparse

__version__ = "1.0.0"

def clean_movies(rootDir, flags):
    # Setup a new operation counter for tv-series cleaning.
    # Extract and clean any archives.
    opCounter = media_tools.extract_and_clean_archives(rootDir, flags)

    # Sort and cleanup.
    for movieName in os.listdir(rootDir):
        
        # Extract the cleaned movie directory name.
        cleanedMovieName = media_tools.get_clean_movie_dir_name(movieName)
        
        # Try to clean the movie directory or file.
        if os.path.isfile(os.path.join(rootDir, movieName)):
            if flags['verbose']:
                print "Found movie file in root directory: " + movieName
            opCounter = media_tools.merge_op_counts(opCounter, \
                media_tools.move_file_dir(os.path.join(rootDir, movieName), \
                    os.path.join(os.path.join(rootDir, cleanedMovieName), movieName), \
                        "movie", flags))
        else:
            opCounter = media_tools.merge_op_counts(opCounter, \
                media_tools.move_file_dir(os.path.join(rootDir, movieName), \
                    os.path.join(rootDir, cleanedMovieName), "movie", flags))
       
        # Update path incase directory has been renamed or the file moved.
        if not flags['safemode']:
            # Update the current directory path.
            movieName = cleanedMovieName    

        # Set the movie to walk through.
        currentDir = os.path.join(rootDir, movieName)

        # Go through files in movies folder and check path.
        for dirPath, dirs, files in os.walk(currentDir):
            for file in files:
                # Check if main file.
                if media_tools.is_main_file(file, dirPath):
                    # Clean tv main file name.
                    opCounter = media_tools.merge_op_counts(opCounter, \
                        media_tools.clean_movie_main_file(dirPath, file, \
                                                        currentDir, movieName, flags))
                else:
                    opCounter = media_tools.merge_op_counts(opCounter, \
                        clean_other_file(currentDir, dirPath, file, flags))

        # Delete empty directories.
        opCounter = media_tools.merge_op_counts(opCounter, \
            media_tools.remove_empty_folders(currentDir, flags))
        
    media_tools.print_op_count(opCounter, flags)
    print "Cleanup completed.\n"

def clean_tv(rootDir, flags):
    # Extract and clean any archives.
    opCounter = media_tools.extract_and_clean_archives(rootDir, flags)

    # Sort and cleanup.
    for seriesName in os.listdir(rootDir):
        # Set the current series to walk through.
        currentDir = os.path.join(rootDir, seriesName)

        # Go through files in a series folder and check path.
        for dirPath, dirs, files in os.walk(currentDir):
            for file in files:
                if media_tools.has_markers(file) and \
                        media_tools.is_main_file(file, dirPath):
                    # Clean tv main file name.
                    opCounter = media_tools.merge_op_counts(opCounter, \
                        media_tools.clean_tv_main_file(\
                            currentDir, dirPath, file, seriesName, flags))
                else:
                    opCounter = media_tools.merge_op_counts(opCounter, \
                        clean_other_file(currentDir, dirPath, file, flags))

        # Delete empty directories.
        opCounter = media_tools.merge_op_counts(opCounter, \
            media_tools.remove_empty_folders(currentDir, flags))
    
    media_tools.print_op_count(opCounter, flags)
    print "Cleanup completed.\n"
    
def clean_other_file(baseDir, dirPath, file, flags):
    opCounter = {}
    
    # Clean other types of files.
    if media_tools.is_extras_file(file, dirPath):
        # Extra video content, move to folder.
        extrasPath = os.path.join(baseDir, "Extras")
        opCounter = media_tools.merge_op_counts(opCounter, \
            media_tools.move_file_dir(os.path.join(dirPath, file), \
                                    os.path.join(extrasPath, file), "extras", flags))
    
    elif media_tools.is_music_file(file):
        # Extra music content, move to folder.
        musicPath = os.path.join(baseDir, "Soundtrack")
        opCounter = media_tools.merge_op_counts(opCounter, \
            media_tools.move_file_dir(os.path.join(dirPath, file), \
                                    os.path.join(musicPath, file), "music", flags))
                    
    elif not media_tools.is_torrent_file(file):
        # File not needed remove.
        opCounter = media_tools.merge_op_counts(opCounter, \
            media_tools.remove_file(dirPath, file, flags))
            
    return opCounter
 
def clean():
    # Check if safemode is enabled.
    if args.safemode:
        print "Safemode enabled, not changing any files."
    else:
        print "Safemode disabled, all changes will be applied."
        
    flags = {'safemode':args.safemode, 'verbose':args.verbose}

    # Clean what was specified.
    if args.movies:
        # Get path from yaml file
        rootDir = media_tools.get_value_from_yaml(args.settingsfile, "path", "movie")
        print "Running movie cleanup script on: " + rootDir  
        clean_movies(rootDir, flags)
        
    if args.tv:
        # Get path from yaml file
        rootDir = media_tools.get_value_from_yaml(args.settingsfile, "path", "tv")
        print "Running tv-serie cleanup script on: " + rootDir
        clean_tv(rootDir, flags)
    

# Start
parser = argparse.ArgumentParser(description='Cleans and renames media files.')

parser.add_argument('--safemode', '-s', action='store_true', \
    help='disables any file changes')
parser.add_argument('--verbose', '-v', action='store_true', \
    help='disables any file changes')
parser.add_argument('--force', '-f', action='store_true', \
    help='force clean and ignore torrent activity')
parser.add_argument('--tv', '-t', action='store_true', \
    help='clean tv-series directory' )
parser.add_argument('--movies', '-m', action='store_true', \
    help='clean movie directory')
parser.add_argument('settingsfile', \
    help='path to the yaml file containing media paths')
    
args = parser.parse_args()

# Check if torrent activity should be ignored.
if args.force:
    print "Force enabled, skipping torrent activity check."
    # Start cleanup.
    clean()
else:
    # Do torrent activity check and start cleanup.
    media_tools.deluge_run_if_no_torrents(clean)
