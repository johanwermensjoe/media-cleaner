"""
mediatools module:
Contains various media and io functions.
"""

from os import path, listdir, walk, rename, remove, rmdir, makedirs
from re import match, search, sub
import rarfile
from rarfile import RarFile
from yaml import load


##########################################################
################## Cleaning Procedures ###################


def clean_movie(flags, root_dir):
    """ Cleans a movie library. """

    # Setup a new operation counter for tv-series cleaning.
    # Extract and clean any archives.
    op_counter = _extract_and_clean_archives(flags, root_dir)

    # Sort and cleanup.
    for movie_name in listdir(root_dir):

        # Extract the cleaned movie directory name.
        cleaned_movie_name = _get_clean_movie_dir_name(movie_name,
                                                       path.join(root_dir,
                                                                 movie_name))

        # Try to clean the movie directory or file.
        if path.isfile(path.join(root_dir, movie_name)):
            log(flags, "Found movie file in root directory: " + movie_name)
            op_counter = _merge_op_counts(op_counter,
                                          _move_file_dir(
                                              flags, path.join(root_dir,
                                                               movie_name),
                                              path.join(path.join(
                                                  root_dir, cleaned_movie_name),
                                                  movie_name),
                                              "movie"))
        else:
            op_counter = _merge_op_counts(op_counter,
                                          _move_file_dir(
                                              flags,
                                              path.join(root_dir,
                                                        movie_name),
                                              path.join(root_dir,
                                                        cleaned_movie_name),
                                              "movie"))

        # Update path in case directory has been renamed or the file moved.
        if not flags['safemode']:
            # Update the current directory path.
            movie_name = cleaned_movie_name

        # Set the movie to walk through.
        current_dir = path.join(root_dir, movie_name)

        # Go through files in movies folder and check path.
        for dir_path, _, files in walk(current_dir):
            for file_ in files:
                # Check if main file.
                if _is_main_file(file_, dir_path):
                    # Clean tv main file name.
                    op_counter = _merge_op_counts(op_counter,
                                                  _clean_movie_main_file(
                                                      flags, dir_path, file_,
                                                      current_dir, movie_name))
                else:
                    op_counter = _merge_op_counts(op_counter,
                                                  _clean_other_file(
                                                      flags, current_dir,
                                                      dir_path, file_))

        # Delete duplicate main files.
        op_counter = _merge_op_counts(op_counter,
                                      _clean_duplicates(flags, current_dir))

    _finish_cleanup(flags, op_counter, root_dir)


def clean_tv(flags, root_dir):
    """ Cleans a tv-series library. """

    # Extract and clean any archives.
    op_counter = _extract_and_clean_archives(flags, root_dir)

    # Sort and cleanup.
    for series_name in listdir(root_dir):
        # Set the current series to walk through.
        current_dir = path.join(root_dir, series_name)

        # Go through files in a series folder and check path.
        for dir_path, _, files in walk(current_dir):
            for file_ in files:
                if _has_markers(file_) and \
                        _is_main_file(file_, dir_path):
                    # Clean tv main file name.
                    op_counter = _merge_op_counts(op_counter,
                                                  _clean_tv_main_file(
                                                      flags, current_dir,
                                                      dir_path, file_,
                                                      series_name))
                else:
                    op_counter = _merge_op_counts(op_counter,
                                                  _clean_other_file(flags,
                                                                    current_dir,
                                                                    dir_path,
                                                                    file_))

        for season in listdir(current_dir):
            # A season directory.
            season_dir = path.join(current_dir, season)
            if path.isdir(season_dir):
                for episode in listdir(season_dir):
                    # An episode directory.
                    episode_dir = path.join(season_dir, episode)
                    if path.isdir(episode_dir):
                        # Delete duplicate main files.
                        op_counter = _merge_op_counts(op_counter,
                                                      _clean_duplicates(
                                                          flags, episode_dir))

    _finish_cleanup(flags, op_counter, root_dir)


def _clean_other_file(flags, base_dir, dir_path, file_):
    """ Cleans auxiliary fies like extras content, soundtracks etc. """

    op_counter = {}

    # Clean other types of files.
    if _is_extras_file(file_, dir_path):
        # Extra video content, move to folder.
        extras_path = path.join(base_dir, "Extras")
        op_counter = _merge_op_counts(op_counter,
                                      _move_file_dir(flags,
                                                     path.join(dir_path,
                                                               file_),
                                                     path.join(extras_path,
                                                               file_),
                                                     "extras"))

    elif _is_music_file(file_):
        # Extra music content, move to folder.
        music_path = path.join(base_dir, "Soundtrack")
        op_counter = _merge_op_counts(op_counter,
                                      _move_file_dir(flags,
                                                     path.join(dir_path,
                                                               file_),
                                                     path.join(music_path,
                                                               file_),
                                                     "music"))

    elif not _is_torrent_file(file_):
        # File not needed remove.
        op_counter = _merge_op_counts(op_counter,
                                      _remove_file(flags, dir_path, file_))
    return op_counter


def _finish_cleanup(flags, op_counter, root_dir):
    """ Finishes cleanup with empty folder removal and stats message. """
    # Delete empty directories.
    op_counter = _merge_op_counts(op_counter,
                                  _remove_empty_folders(flags, root_dir))

    # Log stats.
    _print_op_count(flags, op_counter)
    log(flags, "Cleanup completed.\n", TextType.INFO)


##########################################################
################ File type checking/parsing ###############

# Min video file size = 2 MB.
_MIN_VIDEO_SIZE = 2000000

# Min main file file size = 200 MB.
_MIN_MAIN_VIDEO_SIZE = 200000000

# A file size factor for determining relevance. = 100 MB
_SIZE_SORT_INCREMENT = 100000000


def _is_video_file(file_):
    """ Checks if a file is a video file. """
    return file_.endswith(".mkv") or file_.endswith(".mp4") or \
           file_.endswith(".avi") or file_.endswith(".flv")


def _is_subtitle_file(file_):
    """ Checks if a file is a subtitle file. """
    return file_.endswith(".srt") or file_.endswith(".smi") or \
           file_.endswith(".sub")


def _is_sample_file(file_, path_):
    """ Checks if a file is a video sample file. """
    match_ = match(r'''(?i).*(?:\W+Sample(?:\W+|\d+))''', file_)
    return path.getsize(path.join(path_, file_)) < _MIN_VIDEO_SIZE or \
           (match_ is not None and
            path.getsize(path.join(path_, file_)) < _MIN_MAIN_VIDEO_SIZE)


def _is_compressed_file(file_):
    """ Checks if a file is compressed. """
    match_ = match(r'''.*\.(?:rar|r\d{1,3}|part|part\d{1,3})$''', file_)
    return match_ is not None


def _is_music_file(file_):
    """ Checks if a file is a music file. """
    return file_.endswith(".mp3") or file_.endswith(".wav") or \
           file_.endswith(".flac") or file_.endswith(".aac") or \
           file_.endswith(".ogg")


def _is_torrent_file(file_):
    """ Checks if a file is an incomplete torrent file. """
    return file_.endswith(".part")


def _is_main_file(file_, path_):
    """ Checks if a file is a main video file. """
    return (_is_video_file(file_) and not (_is_sample_file(file_, path_) or
                                           _is_extras_file(file_, path_))) or \
           (_is_subtitle_file(file_) and not _is_extras_file(file_, path_)) or \
           _is_compressed_file(file_)


def _is_proper_main_file(file_):
    """ Checks if a file is a proper/repack etc. release. """
    match_ = match(r'''(?i).*\W+(?:proper|repack|rerip|real)\W+''', file_)
    return match_ is not None


def _is_valid_media_name(name):
    """ Checks if a media name seems valid. (Not definitive) """
    return name != "None"


def _is_extras_file(file_, path_):
    """ Checks if a file is a extras file. """
    match_ = match(r'''(?i).*(?:\W+extra\W+)''', file_)
    return (_is_video_file(file_) and not _is_sample_file(file_, path_) and
            ((path.getsize(path.join(path_, file_)) <
              _MIN_MAIN_VIDEO_SIZE and
              not _has_markers(file_)) or match_ is not None)) or \
           (_is_subtitle_file(file_) and match_ is not None)


def _has_markers(file_):
    """ Checks if a file has season and episode markers/numbering. """
    return _get_season_num(file_) is not None and \
           _get_episode_num(file_) is not None


def _get_season_num(file_):
    """ Extract the season number of a file. """
    # Check standard pattern S01E01
    match_ = search(
        r'''(?i)(?:season|s)\s*(\d{1,2})|(\d{1,2})\s*x|^(\d)\s*\d{2}''', file_)
    if match_:
        if match_.group(1):
            return sub("^0+", "", match_.group(1))
        elif match_.group(2):
            return sub("^0+", "", match_.group(2))
        elif match_.group(3):
            return sub("^0+", "", match_.group(3))


def _get_episode_num(file_):
    """ Extract the episode number of a file. """
    # Check standard pattern S01E01
    match_ = search(r'''(?i)(?:episode|x|e)\s*(\d{1,2})|^\d(\d{2})''', file_)
    if match_:
        if match_.group(1):
            return sub("^0+", "", match_.group(1))
        elif match_.group(2):
            return sub("^0+", "", match_.group(2))


def _get_main_file_type(file_):
    """ Extract the type of a main video file. """
    if _is_subtitle_file(file_):
        return "subtitle"
    else:
        return "video"


##########################################################
##################### YAML tools #########################

def get_value_from_yaml(file_path, root_tree, branch):
    """ Extract a value from a yaml file. """
    doc = load(open(file_path, 'r'))
    return doc[root_tree][branch]


##########################################################
################### Cleaning  tools ######################

def _clean_duplicates(flags, dir_path):
    """ Removes the least wanted duplicate main files. """
    op_counter = {}
    # print "Dup: " + dir_path
    # Get all main files in directory.
    main_files = []
    for file_ in listdir(dir_path):
        # print "\tFile: " + file_
        file_path = path.join(dir_path, file_)
        if path.isfile(file_path) and (_is_main_file(file_, dir_path) and
                                           _is_video_file(file_)):
            main_files += [file_path]

    if len(main_files) > 1:
        main_files.sort(key=path.getsize, reverse=True)
        main_files.sort(key=_is_proper_main_file, reverse=True)
        main_files.sort(key=lambda f: path.getsize(f) / _SIZE_SORT_INCREMENT,
                        reverse=True)

        # Keep the best file.
        main_files = main_files[1:]
        for main_file in main_files:
            parts = path.split(main_file)
            op_counter = _merge_op_counts(op_counter,
                                          _remove_file(flags, parts[0],
                                                       parts[1],
                                                       file_type="duplicate"))

    return op_counter


def _clean_tv_main_file(flags, series_dir, dir_path, file_, series_name):
    """ Clean a main tv-series file. """
    # Make proper path.
    proper_path = path.join(
        path.join(series_dir,
                  "Season " + _get_season_num(file_)),
        "{} S{}E{}".format(series_name,
                           _get_season_num(file_).zfill(2),
                           _get_episode_num(file_).zfill(2)))

    # Try to move the video file to the correct location.
    op_counter = _move_file_dir(flags, path.join(dir_path, file_),
                                path.join(proper_path, file_),
                                _get_main_file_type(file_))
    # Clean tv main file name.
    op_counter = _merge_op_counts(op_counter,
                                  _clean_tv_main_file_name(flags, proper_path,
                                                           file_, series_name))

    return op_counter


def _clean_tv_main_file_name(flags, dir_path, file_, series_name):
    """ Clean a main tv-series file name. """
    return _move_file_dir(flags, path.join(dir_path, file_),
                          path.join(dir_path, _get_clean_tv_main_file_name(
                              file_, series_name)), _get_main_file_type(file_))


def _get_clean_tv_main_file_name(file_, series_name):
    """ Returns a cleaned a main tv-serie file name. """
    if _has_markers(file_):
        # Create episode id.
        episode_id = series_name.replace(" ", ".") + ".S" + \
                     str(_get_season_num(file_)).zfill(2) + "E" + \
                     str(_get_episode_num(file_)).zfill(2)

        # Name can be formatted.
        quality_match = search(
            r'''(?i)(?:(?:episode|x|e)\s*(?:\d{1,2})|^\d{3})\W+(.*)\..{1,4}$''',
            file_)
        # Omit quality if not found
        if quality_match is not None:
            quality = quality_match.group(1)
        elif _is_subtitle_file(file_):
            quality = file_.rsplit(".", 1)[0]
        else:
            quality = ""

        # Clean from additional episode id in quality string.
        if quality.lower().startswith(episode_id.lower()):
            quality = quality[len(episode_id):]

        quality = quality.strip(" ._-")

        return episode_id + ("." if quality != "" else "") + \
               quality.replace(" ", ".").upper() + "." + \
               file_.rsplit(".", 1)[1]

    else:
        # Return the old name.
        return file_


def _clean_movie_main_file(flags, dir_path, file_, movie_dir, movie_name):
    """ Clean a main movie file. """
    # Try to move the video file to the correct location.
    op_counter = _move_file_dir(flags, path.join(dir_path, file_),
                                path.join(movie_dir, file_),
                                _get_main_file_type(file_))
    # Clean tv main file name.
    op_counter = _merge_op_counts(op_counter,
                                  _clean_movie_main_file_name(flags, movie_dir,
                                                              file_,
                                                              movie_name))
    return op_counter


def _clean_movie_main_file_name(flags, dir_path, file_, movie_name):
    """ Clean a main movie file name. """
    return _move_file_dir(flags, path.join(dir_path, file_),
                          path.join(dir_path,
                                    _get_clean_movie_main_file_name(
                                        file_, movie_name)),
                          _get_main_file_type(file_))


def _get_clean_movie_main_file_name(file_, movie_name):
    """ Returns a cleaned a main movie file name.
        Relies on names formatted in std movie dir format:
        - "My Movie (2015)".
    """
    name_year_match = match(r'''(?i)(.*)\s[(](\d{4})[)]$''', movie_name)
    # Extract quality string from file name.
    quality_match = search(
        r'''(?i)(?:\W[\[(]?\d{4}[\])]?\W)(.*)\..{1,4}$''', file_)
    # Omit quality if not found
    if quality_match is not None:
        quality = quality_match.group(1)
    elif _is_subtitle_file(file_) and name_year_match is not None:
        quality = file_.rsplit(".", 1)[0].upper().replace(
            name_year_match.group(1).upper(), "")
    else:
        quality = ""
    quality = quality.strip(" ._-")
    if name_year_match is not None:
        return name_year_match.group(1).replace(" ", ".") + "." + \
               name_year_match.group(2) + ("." if quality != "" else "") + \
               quality.replace(" ", ".").upper() + "." + \
               file_.rsplit(".", 1)[1]
    else:
        return movie_name.replace(" ", ".") + ("." if quality != "" else "") + \
               quality.replace(" ", ".").upper() + "." + \
               file_.rsplit(".", 1)[1]


def _get_clean_movie_dir_name(movie_name, dir_):
    """ Returns a cleaned movie directory name. """
    match_ = _get_movie_name_year_match(movie_name)

    # If the name might be incorrect, check for possible alts.
    if (match_ is None or not _is_valid_media_name(match_[0])) \
            and path.isdir(dir_):
        match_ = _find_movie_name_year_match(dir_)

    if match_ is not None:
        # Format movie name into std format: "My Movie (2015)."
        return sub(r'''[._]+|\s+''', " ", match_[0]) + " (" + match_[1] + ")"
    else:
        # Return the inputted name in case of pattern matching would fail.
        return movie_name


def _find_movie_name_year_match(dir_):
    """ Finds a valid movie name in a movie directory, None if no exists. """
    # Find all possible files and directories to check.
    names_to_check = []
    for _, dirs, files in walk(dir_):
        names_to_check += files
        names_to_check += dirs

    # Test all names.
    for name in names_to_check:
        match_ = _get_movie_name_year_match(name)
        if match_ is not None and _is_valid_media_name(match_[0]):
            return match_
    return None


def _get_movie_name_year_match(movie_name):
    """ Returns a tuple with name and year or None if not found. """
    match_std = match(r'''(?i)(.*)\W[\[(]?(\d{4})[\])]?\W''', movie_name)
    if match_std is not None:
        return match_std.group(1).strip(), match_std.group(2)
    else:
        return None


##########################################################
################ File/Directory tools ####################

def _remove_empty_folders(flags, path_, remove_root=True):
    """ Removes empty folders in the given path. """
    if not path.isdir(path_):
        return

    op_counter = {}
    # Remove empty sub folders.
    files = listdir(path_)
    for file_ in files:
        full_path = path.join(path_, file_)
        if path.isdir(full_path):
            op_counter = _merge_op_counts(op_counter,
                                          _remove_empty_folders(flags,
                                                                full_path))

    # If folder empty, delete it
    files = listdir(path_)
    if len(files) == 0 and remove_root:
        log(flags, "Removing empty folder:" + path_)
        if not flags['safemode']:
            rmdir(path_)
        op_counter = _merge_op_counts(op_counter, {'d_rm': 1})

    return op_counter


def _move_file_dir(flags, old_path, new_path, file_dir_type):
    """ Moves a file or a directory. """
    op_counter = {}

    if old_path != new_path:
        # Calculate the parent directory paths.
        old_dir = path.dirname(old_path)
        new_dir = path.dirname(new_path)

        # Check if the file/dir is being moved or just renamed.
        if old_dir != new_dir:
            # Move
            op_counter = {('f_m' if path.isfile(old_path) else 'd_m'): 1}
            log(flags, "Moving " + file_dir_type +
                (" file" if path.isfile(old_path) else " directory") +
                ": " + old_path + "\nTo: " + new_path)
            if not flags['safemode']:
                # Make sure parent directory exists.
                if not path.isdir(new_dir):
                    makedirs(new_dir)
        else:
            # Rename
            op_counter = {('f_r' if path.isfile(old_path) else 'd_r'): 1}
            log(flags, "Renaming " + file_dir_type +
                (" file" if path.isfile(old_path) else " directory") +
                ": " + old_path + "\nTo: " + new_path)
        if not flags['safemode']:
            # If only case has been changed do temp move (Samba compatibility).
            if old_path.lower() == new_path.lower():
                rename(old_path, old_path + "_temp")
                old_path += "_temp"
            # Do the move/rename.
            rename(old_path, new_path)

    return op_counter


def _remove_file(flags, dir_path, file_, file_type=None):
    """ Removes a file. """
    log(flags, "Removing " + (
        file_type + " " if file_type is not None else "") + "file: " +
        path.join(dir_path, file_))
    if not flags['safemode']:
        remove(path.join(dir_path, file_))

    return {'f_rm': 1}


##########################################################
################ Archive extraction ######################

def _extract_and_clean_archives(flags, root_dir):
    """ Extracts all archives and removes the compressed archives. """
    op_counter = {}

    for content_folder in listdir(root_dir):
        # Set the current series to walk through.
        current_dir = path.join(root_dir, content_folder)

        # Go through files in a series folder and check path.
        for dir_path, _, files in walk(current_dir):
            for file_ in files:
                if file_.endswith(".rar"):
                    op_counter = _merge_op_counts(op_counter,
                                                  _extract_rar(flags, dir_path,
                                                               file_))
                    op_counter = _merge_op_counts(op_counter,
                                                  _remove_archive(flags,
                                                                  dir_path,
                                                                  file_))
    return op_counter


def _extract_rar(flags, dir_path, main_file):
    """ Extracts a .rar archive. """
    log(flags, "Extracting archive: " + path.join(dir_path, main_file))
    if not flags['safemode']:
        # Set to '/' to be more compatible with zipfile
        rarfile.PATH_SEP = '/'
        # Open rar archive.
        r_file = RarFile(path.join(dir_path, main_file))
        r_file.extractall(dir_path)
        r_file.close()
    return {'a_e': 1}


def _remove_archive(flags, dir_path, main_file):
    """ Removes all archive files belonging to and including the main file. """
    op_counter = {}

    for file_ in listdir(dir_path):
        if _is_compressed_file(file_) and main_file[:-4] in file_:
            op_counter = _merge_op_counts(op_counter, {'f_rm': 1})
            log(flags, "Removing archive file: " +
                path.join(dir_path, file_))
            if not flags['safemode']:
                remove(path.join(dir_path, file_))
    return op_counter


##########################################################
################# Operation Counting #####################

# All filesystem-operation functions will return a dict with
# operation types and counts.

_OP_KEYS = ['a_e',
            'f_rm',
            'f_r',
            'f_m',
            'd_rm',
            'd_r',
            'd_m']

_OP_VALUES = ["Archive extraction",
              "File remove",
              "File rename",
              "File move",
              "Directory remove",
              "Directory rename",
              "Directory move"]


def _format_op_count(op_count):
    """ Formats an operation count """
    f_str = []
    for i in range(0, len(_OP_KEYS)):
        k = _OP_KEYS[i]
        if k in op_count:
            f_str.append("- " + _OP_VALUES[i] + ": " + str(op_count[k]))
    return "\n".join(f_str)


def _print_op_count(flags, op_count):
    """ Prints an operation count summary. """
    if op_count is not None:
        # Check that it's not empty.
        log(flags, "Operation count " +
            ("(safemode/not executed):" if flags['safemode'] else ":"),
            TextType.INFO)
        log(flags, _format_op_count(op_count), TextType.INFO)
    else:
        log(flags, "No operations performed.", TextType.INFO)


def _merge_op_counts(op_count1, op_count2):
    """ Merges and adds two operation counters. """
    for key, val in op_count2.items():
        if key in op_count1:
            op_count1[key] += val
        else:
            op_count1[key] = val

    return op_count1


##########################################################
####################### Logging ##########################

class _ColorCode(object):
    """ Color codes for text. """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class _TextFormat(object):
    """ Text formats. """
    HEADER = _ColorCode.HEADER
    BLUE = _ColorCode.OKBLUE
    GREEN = _ColorCode.OKGREEN
    WARNING = _ColorCode.WARNING
    FAIL = _ColorCode.FAIL
    BOLD = _ColorCode.BOLD
    UNDERLINE = _ColorCode.UNDERLINE


class TextType(object):
    """ Text types with priority for logging. """
    INFO = ([_TextFormat.BLUE], 1)
    SUCCESS = ([_TextFormat.GREEN], 1)
    WARNING = ([_TextFormat.WARNING], 1)
    ERR = ([_TextFormat.FAIL], 2)
    ERR_EXTRA = ([], 2)
    INIT = ([_TextFormat.BOLD], 1)
    STD = ([], 0)


def _print_format(msg, format_):
    """
    Prints the "msg" to stdout using the specified text format
    (TextFormat class). Prints just standard text if no formats are given.
    """
    if format_:
        # Print format codes., message and end code.
        print("".join(format_) + msg + _ColorCode.ENDC)
    else:
        print(msg)


def log(flags, msg, type_=TextType.STD):
    """
    Prints log message depending on verbose flag and priority.
    Default priority is 0 which only prints if verbose, 1 always prints.
    """
    # Always print error messages and similar.
    if (type_[1] >= 2) or flags['verbose'] \
            or (not flags['quiet'] and type_[1] == 1):
        if flags['color']:
            _print_format(msg, type_[0])
        else:
            print(msg)


def log_err(msg):
    """ Prints an error message regardless of mode. """
    log({'color': False}, msg, TextType.ERR)


def log_success(flags):
    """ Prints a success message with appropriate color. """
    log(flags, "Success\n", TextType.SUCCESS)
