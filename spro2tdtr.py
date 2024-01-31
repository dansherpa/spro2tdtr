# coding=utf-8
import sqlite3
import sys
import zipfile
from sqlite3 import Error

from Result import Result


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn


FINISHES_QUERY = '''SELECT F."C_NUM" AS bib,
  S."C_HOUR2" start_micros,
  STRFTIME("%Hh%M:%S", S."C_HOUR2"/1000000.0, "unixepoch") || "." || SUBSTR("000000" || (S."C_HOUR2" % 1000000), -6, 4) AS start_hour_cell,
  F."C_HOUR2" finish_micros,
  STRFTIME("%Hh%M:%S", F."C_HOUR2"/1000000.0, "unixepoch") || "." || SUBSTR("000000" || (F."C_HOUR2" % 1000000), -6, 4) AS finish_hour_cell,
  CAST((F."C_HOUR2" - S."C_HOUR2") / 10000.0 AS int)/ 100.0 AS net_raw,
  SUBSTR(TIME(CAST((F."C_HOUR2" - S."C_HOUR2") / 10000.0 AS int)/ 100.0, "unixepoch"), 4) || SUBSTR(printf("%.2f", CAST((F."C_HOUR2" - S."C_HOUR2") / 10000.0 AS int)/ 100.0 - CAST(CAST((F."C_HOUR2" - S."C_HOUR2") / 10000.0 AS int)/ 100.0 AS int)), 2) AS net_time
FROM "TTIMERECORDS_HEAT{run}_FINISH" AS F
JOIN "TTIMERECORDS_HEAT{run}_START" AS S ON (S."C_NUM" = F."C_NUM" AND S."C_STATUS" = 0)
WHERE F."C_STATUS" = 0
AND bib > 0 AND (bib < 901 OR bib > 909)
ORDER BY F."C_LINE"'''


def get_first_last_best_run(run, system, first=0, last=0, best=0):
    conn = create_connection("File2")

    cur = conn.cursor()
    query = FINISHES_QUERY.format(run=run)
    cur.execute(query)

    desc = cur.description
    column_names = [col[0] for col in desc]
    data = [dict(zip(column_names, row))
            for row in cur.fetchall()]
    cur.fetchall()

    bibs = 0
    result_first = Result(0, 0, "", 0, "", 0, "")
    result_last = Result(0, 0, "", 0, "", 0, "")
    result_best = Result(0, 0, "", 0, "", 999999999.0, "")
    for d in data:
        result = Result(d['bib'], int(d['start_micros']), d['start_hour_cell'], int(d['finish_micros']), d['finish_hour_cell'], d['net_raw'], d['net_time'])
        if d['bib'] == first:
            result_first = result
        else:
            if bibs == 0:
                result_first = result
        if best > 0:
            if d['bib'] == best:
                result_best = result
        else:
            if d['net_raw'] < result_best.net_raw:
                result_best = result
        if last > 0:
            if d['bib'] == last:
                result_last = result
        else:
            result_last = result
        bibs = bibs + 1
    print("Run:", run, "(" + system + ")")
    print("First:", result_first.bib, result_first.start, result_first.finish, result_first.net_time)
    print("Last:", result_last.bib, result_last.start, result_last.finish, result_last.net_time)
    print("Best:", result_best.bib, result_best.net_time)
    print("Total Finishes:", bibs)
    return result_first.bib, result_last.bib, result_best.bib


def process_file(primary, backup, tdtr):
    with zipfile.ZipFile(primary, 'r') as zipObj:
        zipObj.extractall()
    first_1, last_1, best_1 = get_first_last_best_run(1, "Primary")
    first_2, last_2, best_2 = get_first_last_best_run(2, "Primary")

    with zipfile.ZipFile(backup, 'r') as zipObj:
        zipObj.extractall()
    get_first_last_best_run(1, "Backup", first_1, last_1, best_1)
    get_first_last_best_run(2, "Backup", first_2, last_2, best_2)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: " + sys.argv[0] + " primary.spro backup.spro draft-tdtr.xml")
        exit(1)
    process_file(sys.argv[1], sys.argv[2], sys.argv[3])
