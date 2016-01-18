"""
delugetools module:
Contains various functions for communication with a deluge daemon.
"""

from deluge.log import LOG as log
from deluge.ui.client import client
import deluge.component as component
from twisted.internet import reactor, defer
import time

# Set this to True to allow direct output or set to False for cron
is_interactive = False

status_keys = ["state",
        "save_path",
        "tracker",
        "tracker_status",
        "next_announce",
        "name",
        "total_size",
        "progress",
        "num_seeds",
        "total_seeds",
        "num_peers",
        "total_peers",
        "eta",
        "download_payload_rate",
        "upload_payload_rate",
        "ratio",
        "distributed_copies",
        "num_pieces",
        "piece_length",
        "total_done",
        "files",
        "file_priorities",
        "file_progress",
        "peers",
        "is_seed",
        "is_finished",
        "active_time",
        "seeding_time"
        ]

count = 0
torrent_ids = []

def printSuccess(dresult, is_success, smsg):
    global is_interactive
    if is_interactive:
        if is_success:
            print "[+]", smsg
        else:
            print "[i]", smsg

def printError(emsg):
    global is_interactive
    if is_interactive:
        print "[e]", emsg

def endSession(esresult):
    if esresult:
        print esresult
        reactor.stop()
    else:
        client.disconnect()
        printSuccess(None, False, "Client disconnected.")
        reactor.stop()

def printReport(rresult):
    printSuccess(None, True, "TOTAL TORRENTS: %i" % (count))
    endSession(None)

def on_torrents_status(torrents):
    global filtertime
    tlist = []
    count = len(torrents.items())
    for torrent_id, status in torrents.items():
        printSuccess(None, False, "Current torrent id is: %s" % (torrent_id))
        printSuccess(None, False, "--Torrent name is: %s" % (status["name"]))
        printSuccess(None, False, "--Torrent state is: %s" % (status["state"]))
        printSuccess(None, False, "--Torrent ratio is: %s" % (status["ratio"]))
        printSuccess(None, False, "--Torrent DL rate is: %s" % \
                        (status["download_payload_rate"]))
        printSuccess(None, False, "--Torrent UL rate is: %s" % \
                        (status["upload_payload_rate"]))
        printSuccess(None, False, "--Torrent tracker is: %s" % \
                        (status["tracker_status"]))
    # Set status.
    endSession(None)
    callback(count)
    #defer.DeferredList(tlist).addCallback(printReport)

def on_session_state(result):
    client.core.get_torrents_status({"id": result}, \
                        status_keys).addCallback(on_torrents_status)

def on_connect_success(result):
    printSuccess(None, True, "Connection was successful!")
    curtime = time.time()
    printSuccess(None, False, "Current unix time is %i" % (curtime))
    client.core.get_session_state().addCallback(on_session_state)

def update_status(fn):
    global callback
    callback = fn
    cliconnect = client.connect()
    cliconnect.addCallbacks(on_connect_success, endSession, \
            errbackArgs=("Connection failed: check settings and try again."))
    reactor.run()
