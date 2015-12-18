"""
mediatools module:
Contains various media and io functions.
"""

import os
import re
import delugetools
import rarfile
import yaml

##########################################################
################## Cleaning Procedures ###################

def clean_movie(rootDir, flags):
    # Setup a new operation counter for tv-series cleaning.
    # Extract and clean any archives.
    opCounter = extract_and_clean_archives(rootDir, flags)

    # Sort and cleanup.
    for movieName in os.listdir(rootDir):
        
        # Extract the cleaned movie directory name.
        cleanedMovieName = get_clean_movie_dir_name(movieName)
        
        # Try to clean the movie directory or file.
        if os.path.isfile(os.path.join(rootDir, movieName)):
            log("Found movie file in root directory: " + movieName, flags)
            opCounter = merge_op_counts(opCounter, \
                move_file_dir(os.path.join(rootDir, movieName), \
                    os.path.join(os.path.join(rootDir, cleanedMovieName), \
                                    movieName), "movie", flags))
        else:
            opCounter = merge_op_counts(opCounter, \
                move_file_dir(os.path.join(rootDir, movieName), \
                    os.path.join(rootDir, cleanedMovieName), "movie", flags))
       
        # Update path incase directory has been renamed or the file moved.
        if not flags['safemode']:
            # Update the current directory path.
            movieName = cleanedMovieName    

        # Set the movie to walk through.
        currentDir = os.path.join(rootDir, movieName)

        # Go through files in movies folder and check path.
        for dirPath, dirs, files in os.walk(currentDir):
            for file_ in files:
                # Check if main file.
                if is_main_file(file_, dirPath):
                    # Clean tv main file name.
                    opCounter = merge_op_counts(opCounter, \
                        clean_movie_main_file(dirPath, file_, \
                                                currentDir, movieName, flags))
                else:
                    opCounter = merge_op_counts(opCounter, \
                        clean_other_file(currentDir, dirPath, file_, flags))

        # Delete empty directories.
        opCounter = merge_op_counts(opCounter, \
            remove_empty_folders(currentDir, flags))
        
    print_op_count(opCounter, flags)
    log("Cleanup completed.\n", flags, 1)

def clean_tv(rootDir, flags):
    # Extract and clean any archives.
    opCounter = media_tools.extract_and_clean_archives(rootDir, flags)

    # Sort and cleanup.
    for seriesName in os.listdir(rootDir):
        # Set the current series to walk through.
        currentDir = os.path.join(rootDir, seriesName)

        # Go through files in a series folder and check path.
        for dirPath, dirs, files in os.walk(currentDir):
            for file_ in files:
                if has_markers(file_) and \
                        is_main_file(file_, dirPath):
                    # Clean tv main file name.
                    opCounter = merge_op_counts(opCounter, \
                        clean_tv_main_file(currentDir, dirPath, \
                                            file_, seriesName, flags))
                else:
                    opCounter = merge_op_counts(opCounter, \
                        clean_other_file(currentDir, dirPath, file_, flags))

        # Delete empty directories.
        opCounter = merge_op_counts(opCounter, \
            remove_empty_folders(currentDir, flags))
    
    print_op_count(opCounter, flags)
    log("Cleanup completed.\n", flags, 1)
    
def clean_other_file(baseDir, dirPath, file_, flags):
    opCounter = {}
    
    # Clean other types of files.
    if is_extras_file(file, dirPath):
        # Extra video content, move to folder.
        extrasPath = os.path.join(baseDir, "Extras")
        opCounter = merge_op_counts(opCounter, \
            move_file_dir(os.path.join(dirPath, file_), \
                            os.path.join(extrasPath, file_), "extras", flags))
    
    elif is_music_file(file):
        # Extra music content, move to folder.
        musicPath = os.path.join(baseDir, "Soundtrack")
        opCounter = merge_op_counts(opCounter, \
                                    move_file_dir(os.path.join(dirPath, file_), \
                                        os.path.join(musicPath, file_), \
                                        "music", flags))
                    
    elif not is_torrent_file(file):
        # File not needed remove.
        opCounter = merge_op_counts(opCounter, 
                                        media_tools.remove_file(\
                                            dirPath, file_, flags))
    return opCounter
        
##########################################################
################ Filetype checking/parsing ###############

# Min video filesize = 2 MB.
minVideoSize = 2000000

# Min main file filesize = 200 MB.
minMainVideoSize = 200000000

def _is_video_file(file_):
    return file_.endswith(".mkv") or \
           file_.endswith(".mp4") or file_.endswith(".avi") or \
           file_.endswith(".flv")
    		    
def _is_subtitle_file(file_):
    return file_.endswith(".srt") or \
           file_.endswith(".smi") or file_.endswith(".sub")

def _is_sample_file(file_, path):
    match = re.match(r'''(?i).*(?:\W+Sample(?:\W+|\d+))''', file_)
    return os.path.getsize(os.path.join(path, file_)) < minVideoSize or \
           (match != None and \
           os.path.getsize(os.path.join(path, file_)) < minMainVideoSize)

def _is_compressed_file(file_):
    match = re.match(r'''.*\.(?:rar|r\d{1,3}|part|part\d{1,3})$''', file_)
    if match:
        return True
        
def is_music_file(file_):
    return file_.endswith(".mp3") or \
           file_.endswith(".wav") or file_.endswith(".flac") or \
           file_.endswith(".aac") or file_.endswith(".ogg")

def is_torrent_file(file_):
    return file_.endswith(".part")

def is_main_file(file_, path):
    return (_is_video_file(file_) and not (_is_sample_file(file_, path) \
                or is_extras_file(file_, path))) \
            or (_is_subtitle_file(file_) and not is_extras_file(file_, path)) \
            or _is_compressed_file(file_)
             
def is_extras_file(file_, path):
    match = re.match(r'''(?i).*(?:\W+extra\W+)''', file_)
    return (_is_video_file(file_) and not _is_sample_file(file_, path) and \
            ((os.path.getsize(os.path.join(path, file_)) < minMainVideoSize and \
                not has_markers(file_)) or match != None)) or \
            (_is_subtitle_file(file_) and match != None)
                         
def has_markers(file_):
    return _get_season_num(file_) != None and \
           _get_episode_num(file_) != None
           
def _get_season_num(filename):
    # Check standard pattern S01E01
    match = re.search(\
        r'''(?i)(?:season|s)\s*(\d{1,2})|(\d{1,2})\s*x|^(\d)\s*\d{2}''', \
        filename)
    if match:
        if match.group(1):
            return re.sub("^0+", "", match.group(1))
        elif match.group(2):
            return re.sub("^0+", "", match.group(2))
        elif match.group(3):
            return re.sub("^0+", "", match.group(3))
        
def _get_episode_num(filename):
    # Check standard pattern S01E01
    match = re.search(r'''(?i)(?:episode|x|e)\s*(\d{1,2})|^\d(\d{2})''', \
                      filename)
    if match:
        if match.group(1):
            return re.sub("^0+", "", match.group(1))
        elif match.group(2):
            return re.sub("^0+", "", match.group(2))
            
def _get_main_file_type(file_):
    if _is_subtitle_file(file_):
        return "subtitle"
    else:
        return "video" 

##########################################################
##################### YAML tools #########################

def get_value_from_yaml(filepath, rootTree, branch):
    doc = yaml.load(open(filepath, 'r'))
    return doc[rootTree][branch]
    
##########################################################
################### Cleaning  tools ######################

def clean_tv_main_file(seriesDir, dirPath, file_, seriesName, flags):
    # Make proper path.
    properPath = os.path.join(
                          os.path.join(seriesDir, 
                                "Season " + _get_season_num(file_)), 
                          seriesName + " S" + \
                          str(_get_season_num(file_)).zfill(2) + "E" + \
                          str(_get_episode_num(file_)).zfill(2))
                          
    # Try to move the video file to the correct location.
    opCounter = move_file_dir(os.path.join(dirPath, file_), \
            os.path.join(properPath, file_), _get_main_file_type(file_), flags)
    # Clean tv main file name.
    opCounter = merge_op_counts(opCounter, \
        _clean_tv_main_file_name(properPath, file_, seriesName, flags))
        
    return opCounter

def _clean_tv_main_file_name(dirPath, file_, seriesName, flags):
    return move_file_dir(os.path.join(dirPath, file_), \
            os.path.join(dirPath, _get_clean_tv_main_file_name(\
                        file_, seriesName)), _get_main_file_type(file_), flags)

def _get_clean_tv_main_file_name(file_, seriesName):
    if has_markers(file_):
        # Name can be formatted.
        qualityMatch = re.search(
            r'''(?i)(?:(?:episode|x|e)\s*
                (?:\d{1,2})|^\d{3})\W+(.*)\..{1,4}$''', file_)
        # Omit quality if not found
        if qualityMatch != None:
            quality = qualityMatch.group(1)
        elif _is_subtitle_file(file_):
            quality = file_.rsplit(".", 1)[0]
        else:
            quality = ""
        quality = quality.strip(" ._-")
        return seriesName.replace(" ", ".") + ".S" + \
                  str(_get_season_num(file_)).zfill(2) + "E" + \
                  str(_get_episode_num(file_)).zfill(2) + \
                  ("." if quality != "" else "") + \
                  quality.replace(" ", ".").upper() + "." + \
                  file_.rsplit(".", 1)[1]
                  
    else:
        # Return the old name.
        return file_
    
def clean_movie_main_file(dirPath, file_, movieDir, movieName, flags):
    # Try to move the video file to the correct location.
    opCounter = move_file_dir(os.path.join(dirPath, file_), \
            os.path.join(movieDir, file_), _get_main_file_type(file_), flags)
    # Clean tv main file name.
    opCounter = merge_op_counts(opCounter, \
        _clean_movie_main_file_name(movieDir, file_, movieName, flags))
        
    return opCounter

def _clean_movie_main_file_name(dirPath, file_, movieName, flags):
    return move_file_dir(os.path.join(dirPath, file_), \
            os.path.join(dirPath, _get_clean_movie_main_file_name(\
                        file_, movieName)), _get_main_file_type(file_), flags)

def _get_clean_movie_main_file_name(file_, movieName):
    # Extract pain movie name and year.
    # Relies on names formatted in std movie dir format: "My Movie (2015)".
    nameYearMatch = re.match(r'''(?i)(.*)\s[(](\d{4})[)]$''', movieName)
    # Extract quality string from file name. 
    qualityMatch = re.search(
        r'''(?i)(?:\W[\[(]?\d{4}[\])]?\W)(.*)\..{1,4}$''', file_)
    # Omit quality if not found
    if qualityMatch != None:
        quality = qualityMatch.group(1)
    elif _is_subtitle_file(file_) and nameYearMatch != None:
        quality = file_.rsplit(".", 1)[0].upper().replace(\
                            nameYearMatch.group(1).upper(), "")
    else:
        quality = ""
    quality = quality.strip(" ._-")
    if nameYearMatch != None:
        return nameYearMatch.group(1).replace(" ", ".") + "." + \
                nameYearMatch.group(2) + ("." if quality != "" else "") + \
                quality.replace(" ", ".").upper() + "." + file_.rsplit(".", 1)[1]
    else:
        return movieName.replace(" ", ".") + ("." if quality != "" else "") + \
                quality.replace(" ", ".").upper() + "." + file_.rsplit(".", 1)[1]
        

def get_clean_movie_dir_name(movieName):
    matchStd = re.match(r'''(?i)(.*)\W[\[(]?(\d{4})[\])]?\W''', movieName)
    if matchStd != None:
        # Format movie name into std format: "My Movie (2015)."
        return re.sub(r'''[._]+|\s+''', " ", matchStd.group(1).strip()) + \
                        " (" + matchStd.group(2) + ")"
    else:
        # Return the inputed name in case of pattern matching would fail.
        return movieName
      
##########################################################
################ File/Directory tools ####################

def remove_empty_folders(path, flags, removeRoot=True):
    if not os.path.isdir(path):
        return

    opCounter = {}
    # Remove empty subfolders
    files = os.listdir(path)
    if len(files):
        for f in files:
            fullpath = os.path.join(path, f)
            if os.path.isdir(fullpath):
                opCounter = merge_op_counts(opCounter, \
                    remove_empty_folders(fullpath, flags))
                
    # If folder empty, delete it
    files = os.listdir(path)
    if len(files) == 0 and removeRoot:
        log("Removing empty folder:" + path, flags)
        if not flags['safemode']:
            os.rmdir(path)
        merge_op_counts(opCounter, {'d_rm': 1})
    
    return opCounter
            
def move_file_dir(oldPath, newPath, fileDirType, flags):
    opCounter = {}
    
    if oldPath != newPath:
        # Calculate the parent directory paths.
        oldDir = os.path.dirname(oldPath)
        newDir = os.path.dirname(newPath)
        
        # Check if the file/dir is being moved or just renamed.  
        if oldDir != newDir:
            # Move
            opCounter = {('f_m' if os.path.isfile(oldPath) else 'd_m'): 1}
            log("Moving " + fileDirType + \
                (" file" if os.path.isfile(oldPath) else " directory") + \
                ":\n" + oldPath + "\nTo: " + newPath, flags)
            if not flags['safemode']:
                # Make sure parent directory exists.
                if not os.path.isdir(newDir):
                    os.makedirs(newDir)
        else:
            # Rename
            opCounter = {('f_r' if os.path.isfile(oldPath) else 'd_r'): 1}
            log("Renaming " + fileDirType + \
                (" file" if os.path.isfile(oldPath) else " directory") + \
                ":\n" + oldPath + "\nTo: " + newPath, flags)
        if not flags['safemode']:
            # Do the move/rename.
            os.rename(oldPath, newPath)
            
    return opCounter
            
def remove_file(dirPath, file_, flags):
    log("Removing file: "  + os.path.join(dirPath, file_), flags)
    if not flags['safemode']:
        os.remove(os.path.join(dirPath, file_))
        
    return {'f_rm': 1}

##########################################################
################ Archive extraction ######################

def extract_and_clean_archives(rootDir, flags):
    opCounter = {}
    
    for contentFolder in os.listdir(rootDir):
        # Set the current series to walk through.
        currentDir = os.path.join(rootDir, contentFolder)

        # Go through files in a series folder and check path.
        for dirPath, dirs, files in os.walk(currentDir):
            for file_ in files:
                if file_.endswith(".rar"):
                    opCounter = merge_op_counts(opCounter, \
                        _extract_rar(dirPath, file_, flags))
                    opCounter = merge_op_counts(opCounter, \
                        _remove_archive(dirPath, file_, flags))
    return opCounter

def _extract_rar(dirPath, mainFile, flags):
    
    # Extract files.
    log("Extracting archive: " + os.path.join(dirPath, mainFile), flags)
    if not flags['safemode']:
        # Set to '/' to be more compatible with zipfile
        rarfile.PATH_SEP = '/'
        # Open rar archive.
        rf = rarfile.RarFile(os.path.join(dirPath, mainFile))
        rf.extractall(dirPath)
        rf.close()
    return {'a_e': 1}
    
# Removes all archive files belonging to and including the main file. 
def _remove_archive(dirPath, mainFile, ):
    opCounter = {}
    
    for file_ in os.listdir(dirPath):
        if _is_compressed_file(file_) and mainFile[:-4] in file_:
            opCounter = merge_op_counts(opCounter, {'f_rm': 1})
            log("Removing archive file: " + os.path.join(dirPath, file_), flags)
            if not flags['safemode']:
                os.remove(os.path.join(dirPath, file_))
    return opCounter

##########################################################
################# Operation Counting #####################                

# All filesystem-operation functions will return a dict with 
# operation types and counts.

_opKeys = ['a_e',
            'f_rm',
            'f_r',
            'f_m',
            'd_rm',
            'd_r',
            'd_m']
            
_opValues = ["Archive extraction",
            "File remove",
            "File rename",
            "File move",
            "Directory remove",
            "Directory rename",
            "Directory move"]
                
         
def _format_op_count(opCount):
    fs = []
    for i in range(0, len(_opKeys)):
        k = _opKeys[i]
        if opCount.has_key(k):
            fs.append("- " + _opValues[i] + ": " + str(opCount[k]))
    return "\n".join(fs)
    
def print_op_count(opCount, flags):
    if opCount:
        # Check that it's not empty.
        log("Operation count " + \
            ("(safemode/not executed):" if flags['safemode'] else ":"), \
            flags, 1)
        log(_format_op_count(opCount), flags, 1)
    else:
        log("No operations performed.", flags, 1) 
              
def merge_op_counts(opCount1, opCount2):
    for k, v in opCount2.items():
        if opCount1.has_key(k):
            opCount1[k] += v
        else:
            opCount1[k] = v
            
    return opCount1
    
##########################################################
####################### Logging ##########################

def log(msg, flags, priority=0):
    if flags['verbose'] or (not flags['quiet'] and priority > 0):
        print msg

# Prints the "msg" to stdout using the specified text type (TextType class).
def print_color(msg, color):
    print color + msg + _ColorCode.ENDC

class TextType:
    HEADER = _ColorCode.HEADER
    BLUE = _ColorCode.OKBLUE
    GREEN = _ColorCode.OKGREEN
    WARNING = _ColorCode.WARNING
    FAIL = _ColorCode.FAIL
    BOLD = _ColorCode.BOLD
    UNDERLINE = _ColorCode.UNDERLINE

class _ColorCode:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


##########################################################
################ Deluge communication ####################

def _deluge_torrent_count_callback(count):
    if count == 0:
        callback()
    else:
        log("There are still live torrents, aborting.", {'verbose': True}, 1)
        
def deluge_run_if_no_torrents(fn):
    global callback
    callback = fn
    deluge_tools.update_status(_deluge_torrent_count_callback)
