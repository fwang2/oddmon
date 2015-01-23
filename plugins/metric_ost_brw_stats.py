#!/usr/bin/env python

import os
import glob
import logging
import json
import time
from collections import defaultdict

# Globals

logger = None

class G:
    fsname = None
    ostnames = None
    stats = defaultdict(lambda: defaultdict(int))
    buf = None

def scan_osts():
    osts = glob.glob("/proc/fs/lustre/obdfilter/*")
    ostnames = []
    if len(osts) != 0:
        fsname, _ = os.path.basename(osts[0]).split("-")
        for ost in osts:
            ostnames.append(os.path.basename(ost))
    else:
        logger.error("Can't locate Lustre OSTs")

    return fsname, ostnames

def extract_snaptime(ret):
    idx = G.buf.index('\n')
    ret['snapshot_time'] = G.buf[0].split()[1]
    # update buffer
    G.buf = G.buf[idx+1:]

def extract_hist(key1, key2, ret):
    idx = None

    try:
        idx = G.buf.index('\n')
    except:
        idx = len(ret) + 1

    # skip #0 and #1
    # process 1 line at a time
    for line in G.buf[2:idx]:
        fields = line.split()

        # after split: ['128:', '0', '0', '0', '|', '2', '0', '0']
        # first field '128:', remove colon
        ret[key1][fields[0][:-1]]  = fields[1:4]
        ret[key2][fields[0][:-1]] = fields[5:]

    # update buffer
    G.buf = G.buf[idx+1:]


def read_brw_stats(f):
    """
    expect input of a path to brw stats eg.
    /proc/fs/lustre/obdfilter/mytest-OST0000/brw_stats

    return a dictionary with key/val pairs
    """
    ret = { "snapshot_time"                 :'',
            "pages_per_bulk_read"           :defaultdict(list),
            "pages_per_bulk_write"          :defaultdict(list),
            "discontinuous_pages_read"       :{},
            "discontinuous_pages_write"      :{},
            "discontinuous_blocks_read"      :{},
            "discontinuous_blocks_write"     :{},
            "disk_fragmented_io_read"       :{},
            "disk_fragmented_io_write"      :{},
            "disk_io_in_flight_read"        :{},
            "disk_io_in_flight_write"       :{},
            "io_time_read"                  :{},
            "io_time_write"                 :{},
            "io_size_read"                  :{},
            "io_size_write"                 :{}
           }

    pfile = os.path.realpath(f) + "/brw_stats"
    with open(pfile, "r") as f:
        G.buf = f.readlines()
        extract_snaptime(ret)
        extract_hist('pages_per_bulk_read', 'pages_per_bulk_write', ret)
        extract_hist('discontinuous_pages_read', 'discontinuous_pages_write', ret)
        extract_hist('discontinuous_blocks_read', 'discontinuous_blocks_write', ret)
        extract_hist('disk_fragmented_io_read', 'disk_fragmented_io_write', ret)
        extract_hist('disk_io_in_flight_read', 'disk_io_in_flight_write', ret)
        extract_hist('io_time_read', 'io_time_write', ret)
        extract_hist('io_size_read', 'io_size_write', ret)
    return ret


def update():
    logger.debug("Updating stats")

    for ost in G.ostnames:
        fpath = '/proc/fs/lustre/obdfilter/' + ost
        G.stats[ost] = read_brw_stats(fpath)

    logger.debug("Sucessfully refreshing brw stats")


def metric_init(name):
    global logger
    logger = logging.getLogger(name)
    G.fsname, G.ostnames = scan_osts()

def get_stats():
    update()
    return json.dumps(G.stats)
    # return json.dumps(G.stats, sort_keys=True, indent=4)

def metric_cleanup():
    pass

if __name__ == '__main__':
    metric_init("brw-stats")
    while True:
        print get_stats()
        time.sleep(5)
    metric_cleanup()

