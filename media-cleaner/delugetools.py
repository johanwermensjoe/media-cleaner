"""
delugetools module:
Contains various functions for communication with a deluge daemon.
"""

from subprocess import Popen, PIPE


def has_active_torrents():
    """ Check for any active torrents on the local deluged server.

    :return: True if one or more torrents are active
    :rtype: Bool
    """
    std_output, std_err_output = '', ''
    proc = None
    try:
        proc = Popen(["deluge-console", "info"], stdout=PIPE, stderr=PIPE)
        std_output, std_err_output = proc.communicate()
        # Decode
        std_output = std_output.decode("utf-8")
        std_err_output = std_err_output.decode("utf-8")
    except (OSError, ValueError):
        if proc is not None:
            proc.kill()
        raise RuntimeError("deluge-console could not be found, " +
                           "make sure it is installed")

    if ('fatal' in std_output) or (
            'fatal' in std_err_output) or proc.returncode >= 1:
        raise RuntimeError("Status check failed, " +
                           "make sure that deluged is running")
    else:
        # Success!
        return std_output.strip() != ""
