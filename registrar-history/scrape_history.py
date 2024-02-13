#!/usr/bin/env python3
import json
import random
import sqlite3
import time

from loguru import logger

import requests

FETCH_UPDATES = False

def prepare_db(conn):
    cur = conn.cursor()
    # 'urlkey', 'timestamp', 'original', 'mimetype', 'statuscode', 'digest', 'length'
    cur.execute(
        """CREATE TABLE IF NOT EXISTS archives(
            urlkey,
            timestamp,
            original_url,
            cdx_raw,
            contents NULL,
            CONSTRAINT urlkey_timestamp UNIQUE (timestamp, urlkey) ON CONFLICT ABORT
            )
        """
    )

def insert_single_cdx(cdx, cur):
    record = (
        cdx['urlkey'],
        cdx['timestamp'],
        cdx['original'],
        json.dumps(cdx))
    #logger.debug(f"inserting record {record}")
    try:
        cur.execute("""
                INSERT INTO archives(urlkey, timestamp, original_url, cdx_raw)
                VALUES(?,?,?,?)
                """,
                record)
    except sqlite3.IntegrityError:
        logger.warning(f"record may already exist: {record}")
        pass

def load_cdx(cdx, conn):
    cur = conn.cursor()
    for record in cdx:
        insert_single_cdx(record, cur)
    conn.commit()



def get_history(url):
    params = {
        "output": "json",
        "url": url
    }
    res = requests.get("http://web.archive.org/cdx/search/cdx", params=params)
    raw = res.json()
    headers = raw[0]
    cdx = raw[1:]
    for record in cdx:
        yield dict(zip(headers, record))

def build_urls_from_cdx(cdx):
    without_headers = (x for x in cdx if x[0] != "urlkey")
    for record in without_headers:

        timestamp = record[1]
        original_url = record[2]
        yield f"https://web.archive.org/web/{timestamp}/{original_url}"

def refresh_archives(conn):
    logger.debug("fetching history")
    cdx = get_history("https://www.iana.org/assignments/registrar-ids/registrar-ids.xml")

    logger.debug("updating history")
    load_cdx(cdx, conn)

def build_archive_url(timestamp, original_url):
    return f"https://web.archive.org/web/{timestamp}/{original_url}"

def fetch_item(timestamp, original_url):
    res = requests.get(build_archive_url(timestamp, original_url))
    res.raise_for_status()

    if len(res.text) < 100:
        raise ValueError("Response seems too short")

    return res.text

def fetch_and_update_item(row, conn):
    timestamp = row['timestamp']
    url = row['original_url']
    logger.info(f"updating {url} from {timestamp}")
    res = fetch_item(row['timestamp'], row['original_url'])
    res = conn.execute(
            """
            UPDATE archives
            SET contents = :contents
            WHERE 
                timestamp = :timestamp
                AND original_url = :url
                AND contents IS NULL
            """,
            {
                "contents": res,
                "url": url,
                "timestamp": timestamp
            })
    conn.commit()


def handle_outstanding(conn):
    rows = conn.execute("select * from archives where contents IS NULL ORDER BY RANDOM()")
    for x in rows:
        print(x['timestamp'])
        fetch_and_update_item(x, conn)
        time.sleep(5 * random.random())

def main():
    conn = sqlite3.connect('history.db')
    conn.row_factory = sqlite3.Row
    prepare_db(conn)

    # Handle new scrapes
    if FETCH_UPDATES:
        refresh_archives(conn)
    else:
        logger.info("Skipping Refresh")

    handle_outstanding(conn)

if __name__ == "__main__":
    main()
