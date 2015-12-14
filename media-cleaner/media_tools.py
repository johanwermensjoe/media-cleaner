# media_tools module.

import os
import re
import deluge_tools
import rarfile.rarfile
import yaml

##########################################################
################## Cleaning Procedures ###################

def clean_movie(flags, rootDir):
    # Setup a new operation counter for tv-series cleaning.
    # Extract and clean any archives.
    opCounter = extract_and_clean_archives(flags, rootDir)

    # Sort and cleanup.
    for movieName in os.listdir(rootDir):
        
        # Extract the cleaned movie directory name.
        cleanedMovieName = get_clean_movie_dir_name(movieName)
        
        # Try to clean the movie directory or file.
        if os.path.isfile(os.path.join(rootDir, movieName)):
            log(flags, "Found movie file in root directory: " + movieName)
            opCounter = merge_op_counts(opCounter, \
                move_file_dir(flags, os.path.join(rootDir, movieName), \
                    os.path.join(os.path.join(rootDir, cleanedMovieName), movieName), \
                        "movie"))
        else:
            opCounter = merge_op_counts(opCounter, \
                move_file_dir(flags, os.path.join(rootDir, movieName), \
                    os.path.join(rootDir, cleanedMovieName), "movie"))
       
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
                if is_main_file(file, dirPath):
                    # Clean tv main file name.
                    opCounter = merge_op_counts(opCounter, \
                        clean_movie_main_file(flags, dirPath, file, \
                                                currentDir, movieName))
                else:
                    opCounter = merge_op_counts(opCounter, \
                        clean_other_file(flags, currentDir, dirPath, file))

        # Delete empty directories.
        opCounter = merge_op_counts(opCounter, \
            remove_empty_folders(flags, currentDir))
        
    print_op_count(flags, opCounter)
    log(flags, "Cleanup completed.\n", 1)

def clean_tv(flags, rootDir):
    # Extract and clean any archives.
    opCounter = media_tools.extract_and_clean_archives(flags, rootDir)

    # Sort and cleanup.
    for seriesName in os.listdir(rootDir):
        # Set the current series to walk through.
        currentDir = os.path.join(rootDir, seriesName)

        # Go through files in a series folder and check path.
        for dirPath, dirs, files in os.walk(currentDir):
            for file in files:
                if has_markers(file) and \
                        is_main_file(file, dirPath):
                    # Clean tv main file name.
                    opCounter = merge_op_counts(opCounter, \
                        clean_tv_main_file(flags, currentDir, dirPath, \
                                            file, seriesName))
                else:
                    opCounter = merge_op_counts(opCounter, \
                        clean_other_file(flags, currentDir, dirPath, file))

        # Delete empty directories.
        opCounter = merge_op_counts(opCounter, \
            remove_empty_folders(flags, currentDir))
    
    print_op_count(flags, opCounter)
    log(flags, "Cleanup completed.\n", 1)
    
def clean_other_file(flags, baseDir, dirPath, file):
    opCounter = {}
    
    # Clean other types of files.
    if is_extras_file(file, dirPath):
        # Extra video content, move to folder.
        extrasPath = os.path.join(baseDir, "Extras")
        opCounter = merge_op_counts(opCounter, \
            move_file_dir(flags, os.path.join(dirPath, file), \
                            os.path.join(extrasPath, file), "extras"))
    
    elif is_music_file(file):
        # Extra music content, move to folder.
        musicPath = os.path.join(baseDir, "Soundtrack")
        opCounter = merge_op_counts(opCounter, \
                                    move_file_dir(flags, os.path.join(dirPath, file), \
                                    os.path.join(musicPath, file), "music"))
                    
    elif not is_torrent_file(file):
        # File not needed remove.
        opCounter = merge_op_counts(opCounter, \
                                    media_tools.remove_file(flags, dirPath, file))
    return opCounter
        
##########################################################
################ Filetype checking/parsing ###############

# Min video filesize = 2 MB.
minVideoSize = 2000000

# Min main file filesize = 200 MB.
minMainVideoSize = 200000000

def _is_video_file(file):
    return file.endswith(".mkv") or \
           file.endswith(".mp4") or file.endswith(".avi") or \
           file.endswith(".flv")
    		    
def _is_subtitle_file(file):
    return file.endswith(".srt") or \
           file.endswith(".smi") or file.endswith(".sub")

def _is_sample_file(file, path):
    match = re.match(r'''(?i).*(?:\W+Sample(?:\W+|\d+))''', file)
    return os.path.getsize(os.path.join(path, file)) < minVideoSize or \
           (match != None and \
           os.path.getsize(os.path.join(path, file)) < minMainVideoSize)

def _is_compressed_file(file):
    match = re.match(r'''.*\.(?:rar|r\d{1,3}|part|part\d{1,3})$''', file)
    if match:
        return True
        
def is_music_file(file):
    return file.endswith(".mp3") or \
           file.endswith(".wav") or file.endswith(".flac") or \
           file.endswith(".aac") or file.endswith(".ogg")

def is_torrent_file(file):
    return file.endswith(".part")

def is_main_file(file, path):
    return (_is_video_file(file) and not (_is_sample_file(file, path) \
                or is_extras_file(file, path))) \
            or (_is_subtitle_file(file) and not is_extras_file(file, path)) \
            or _is_compressed_file(file)
             
def is_extras_file(file, path):
    match = re.match(r'''(?i).*(?:\W+extra\W+)''', file)
    return (_is_video_file(file) and not _is_sample_file(file, path) and \
            ((os.path.getsize(os.path.join(path, file)) < minMainVideoSize and \
                not has_markers(file)) or match != None)) or \
            (_is_subtitle_file(file) and match != None)
                         
def has_markers(file):
    return _get_season_num(file) != None and \
           _get_episode_num(file) != None
           
def _get_season_num(filename):
    # Check standard pattern S01E01
    match = re.search(r'''(?i)(?:season|s)\s*(\d{1,2})|(\d{1,2})\s*x|^(\d)\s*\d{2}''', \
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
            
def _get_main_file_type(file):
    if _is_subtitle_file(file):
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

def clean_tv_main_file(flags, seriesDir, dirPath, file, seriesName):
    # Make proper path.
    properPath = os.path.join(
                          os.path.join(seriesDir, 
                                "Season " + _get_season_num(file)), 
                          seriesName + " S" + \
                          str(_get_season_num(file)).zfill(2) + "E" + \
                          str(_get_episode_num(file)).zfill(2))
                          
    # Try to move the video file to the correct location.
    opCounter = move_file_dir(flags, os.path.join(dirPath, file), \
            os.path.join(properPath, file), _get_main_file_type(file))
    # Clean tv main file name.
    opCounter = merge_op_counts(opCounter, \
        _clean_tv_main_file_name(flags, properPath, file, seriesName))
        
    return opCounter

def _clean_tv_main_file_name(flags, dirPath, file, seriesName):
    return move_file_dir(flags, os.path.join(dirPath, file), \
            os.path.join(dirPath, _get_clean_tv_main_file_name(file, seriesName)), \
                        _get_main_file_type(file))

def _get_clean_tv_main_file_name(file, seriesName):
    if has_markers(file):
        # Name can be formatted.
        qualityMatch = re.search(
            r'''(?i)(?:(?:episode|x|e)\s*(?:\d{1,2})|^\d{3})\W+(.*)\..{1,4}$''', file)
        # Omit quality if not found
        if qualityMatch != None:
            quality = qualityMatch.group(1)
        elif _is_subtitle_file(file):
            quality = file.rsplit(".", 1)[0]
        else:
            quality = ""
        quality = quality.strip(" ._-");
        return seriesName.replace(" ", ".") + ".S" + \
                  str(_get_season_num(file)).zfill(2) + "E" + \
                  str(_get_episode_num(file)).zfill(2) + \
                  ("." if quality != "" else "") + \
                  quality.replace(" ", ".").upper() + "." + file.rsplit(".", 1)[1]
                  
    else:
        # Return the old name.
        return file
    
def clean_movie_main_file(flags, dirPath, file, movieDir, movieName):
    # Try to move the video file to the correct location.
    opCounter = move_file_dir(flags, os.path.join(dirPath, file), \
            os.path.join(movieDir, file), _get_main_file_type(file))
    # Clean tv main file name.
    opCounter = merge_op_counts(opCounter, \
        _clean_movie_main_file_name(flags, movieDir, file, movieName))
        
    return opCounter

def _clean_movie_main_file_name(flags, dirPath, file, movieName):
    return move_file_dir(flags, os.path.join(dirPath, file), \
            os.path.join(dirPath, _get_clean_movie_main_file_name(file, movieName)), \
                        _get_main_file_type(file))

def _get_clean_movie_main_file_name(file, movieName):
    # Extract pain movie name and year.
    # Relies on names formatted in std movie dir format: "My Movie (2015)".
    nameYearMatch = re.match(r'''(?i)(.*)\s[(](\d{4})[)]$''', movieName)
    # Extract quality string from file name. 
    qualityMatch = re.search(
        r'''(?i)(?:\W[\[(]?\d{4}[\])]?\W)(.*)\..{1,4}$''', file)
    # Omit quality if not found
    if qualityMatch != None:
        quality = qualityMatch.group(1)
    elif _is_subtitle_file(file) and nameYearMatch != None:
        quality = file.rsplit(".", 1)[0].upper().replace(\
                            nameYearMatch.group(1).upper(), "")
    else:
        quality = ""
    quality = quality.strip(" ._-");
    if nameYearMatch != None:
        return nameYearMatch.group(1).replace(" ", ".") + "." + \
                nameYearMatch.group(2) + ("." if quality != "" else "") + \
                quality.replace(" ", ".").upper() + "." + file.rsplit(".", 1)[1]
    else:
        return movieName.replace(" ", ".") + ("." if quality != "" else "") + \
                quality.replace(" ", ".").upper() + "." + file.rsplit(".", 1)[1]
        

def get_clean_movie_dir_name(movieName):
    matchStd = re.match(r'''(?i)(.*)\W[\[(]?(\d{4})[\])]?\W''', movieName)
    if matchStd != None:
        # Format movie name into std format: "My Movie (2015)".
        return re.sub("[._]+|\s+", " ", matchStd.group(1).strip()) + " (" \
                        + matchStd.group(2) + ")"
    else:
        # Return the inputed name in case of pattern matching would fail.
        return movieName
      
##########################################################
################ File/Directory tools ####################

def remove_empty_folders(flags, path, removeRoot=True):
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
                    remove_empty_folders(flags, fullpath))
                
    # If folder empty, delete it
    files = os.listdir(path)
    if len(files) == 0 and removeRoot:
        log(flags, "Removing empty folder:" + path)
        if not flags['safemode']:
            os.rmdir(path)
        merge_op_counts(opCounter, {'d_rm': 1})
    
    return opCounter
            
def move_file_dir(flags, oldPath, newPath, fileDirType):
    opCounter = {}
    
    if oldPath != newPath:
        # Calculate the parent directory paths.
        oldDir = os.path.dirname(oldPath)
        newDir = os.path.dirname(newPath)
        
        # Check if the file/dir is being moved or just renamed.  
        if oldDir != newDir:
            # Move
            opCounter = {('f_m' if os.path.isfile(oldPath) else 'd_m'): 1}
            log(flags, "Moving " + fileDirType + \
                (" file" if os.path.isfile(oldPath) else " directory") + ":\n" + \
                oldPath + "\nTo: " + newPath)
            if not flags['safemode']:
                # Make sure parent directory exists.
                if not os.path.isdir(newDir):
                    os.makedirs(newDir)
        else:
            # Rename
            opCounter = {('f_r' if os.path.isfile(oldPath) else 'd_r'): 1}
            log(flags, "Renaming " + fileDirType + \
                (" file" if os.path.isfile(oldPath) else " directory") + ":\n" + \
                oldPath + "\nTo: " + newPath)
        if not flags['safemode']:
            # Do the move/rename.
            os.rename(oldPath, newPath)
            
    return opCounter
            
def remove_file(flags, dirPath, file):
    log(flags, "Removing file: "  + os.path.join(dirPath, file))
    if not flags['safemode']:
        os.remove(os.path.join(dirPath, file))
        
    return {'f_rm': 1}

##########################################################
################ Archive extraction ######################

def extract_and_clean_archives(flags, rootDir):
    opCounter = {}
    
    for contentFolder in os.listdir(rootDir):
        # Set the current series to walk through.
        currentDir = os.path.join(rootDir, contentFolder)

        # Go through files in a series folder and check path.
        for dirPath, dirs, files in os.walk(currentDir):
            for file in files:
                if file.endswith(".rar"):
                    opCounter = merge_op_counts(opCounter, \
                        _extract_rar(flags, dirPath, file))
                    opCounter = merge_op_counts(opCounter, \
                        _remove_archive(flags, dirPath, file))
    return opCounter

def _extract_rar(flags, dirPath, mainFile):
    
    # Extract files.
    log(flags, "Extracting archive: " + os.path.join(dirPath, mainFile))
    if not flags['safemode']:
        # Set to '/' to be more compatible with zipfile
        rarfile.PATH_SEP = '/'
        # Open rar archive.
        rf = rarfile.RarFile(os.path.join(dirPath, mainFile))
        rf.extractall(dirPath)
        rf.close()
    return {'a_e': 1}
    
# Removes all archive files belonging to and including the main file. 
def _remove_archive(flags, dirPath, mainFile):
    opCounter = {}
    
    for file in os.listdir(dirPath):
        if _is_compressed_file(file) and mainFile[:-4] in file:
            opCounter = merge_op_counts(opCounter, {'f_rm': 1})
            log(flags, "Removing archive file: " + os.path.join(dirPath, file))
            if not flags['safemode']:
                os.remove(os.path.join(dirPath, file))
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
        k = _opKeys[i];
        if opCount.has_key(k):
            fs.append("- " + _opValues[i] + ": " + str(opCount[k]))
    return "\n".join(fs)
    
def print_op_count(flags, opCount):
    if opCount:
        # Check that it's not empty.
        log(flags, "Operation count " + ("(safemode/not executed):" \
                        if flags['safemode'] else ":"), 1)
        log(flags, _format_op_count(opCount), 1)
    else:
        log(flags, "No operations performed.", 1) 
              
def merge_op_counts(opCount1, opCount2):
    for k,v in opCount2.items():
        if opCount1.has_key(k):
            opCount1[k] += v
        else:
            opCount1[k] = v
            
    return opCount1
    
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

def _print_format(msg, formats):
    """
    Prints the "msg" to stdout using the specified text formats (TextFormat class).
    Prints just standard text if no formats are given.
    """
    if formats:
        # Print format codes., message and end code.
        print string.join(formats) + msg + _ColorCode.ENDC
    else:
        print msg

#TODO Replace with new log
def log(flags, msg, priority=0):
    if flags['verbose'] or (not flags['quiet'] and priority > 0):
        print msg

'''
def log(flags, msg, type_=TextType.STD):
    """
    Prints log messages depending on verbose flag and priority.
    Default priority is 0 which only prints if verbose, 1 always prints.
    """
    # Always print error messages and similar.
    if (type_[1] >= 2) or flags['verbose'] \
            or (not flags['quiet'] and type_[1] == 1):
        if flags['color']:
            _print_format(msg, type_[0])
        else:
            print msg

def log_success(flags):
    """ Prints a success message with appropriate color. """
    log(flags, "Success\n", TextType.SUCCESS)
'''
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
