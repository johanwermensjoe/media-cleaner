"""
delugetools module:
Contains various functions for communication with a deluge daemon.
"""

from subprocess import Popen, PIPE


def has_active_torrents():
    """Check for any active torrents on the local deluged server.

    :return: True if one or more torrents are active
    :rtype: Bool
    """
    try:
        proc = Popen(["deluge-console", "info"], stdout=PIPE, stderr=PIPE)
        std_output, std_err_output = proc.communicate()
    except (OSError, ValueError):
        raise RuntimeError("deluge-console could not be found, " +
                           "make sure it is installed")

    if (b'fatal' in std_output) or (
            b'fatal' in std_err_output) or proc.returncode >= 1:
        raise RuntimeError("Status check failed, " +
                           "make sure that deluged is running")
    else:
        # Success!
        return std_output.strip() != ""
