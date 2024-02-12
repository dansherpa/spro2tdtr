# coding=utf-8
import os
import sqlite3
import sys
import tempfile
import zipfile
from sqlite3 import Error
import declxml as xml


class Result:
  def __init__(self, bib, start_micros, start, finish_micros, finish, net_raw, net_time):
    self.bib = bib
    self.start_micros = start_micros
    self.start = start
    self.finish_micros = finish_micros
    self.finish = finish
    self.net_raw = net_raw
    self.net_time = net_time


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn


FINISHES_QUERY = '''SELECT F."C_NUM" AS bib, F."C_STATUS" as status,
  S."C_HOUR2" start_micros,
  STRFTIME("%H:%M:%S", S."C_HOUR2"/1000000.0, "unixepoch") || "." || SUBSTR("000000" || (S."C_HOUR2" % 1000000), -6, 4) AS start_hour_cell,
  F."C_HOUR2" finish_micros,
  STRFTIME("%H:%M:%S", F."C_HOUR2"/1000000.0, "unixepoch") || "." || SUBSTR("000000" || (F."C_HOUR2" % 1000000), -6, 4) AS finish_hour_cell,
  CAST((F."C_HOUR2" - S."C_HOUR2") / 10000.0 AS int)/ 100.0 AS net_raw,
  SUBSTR(TIME(CAST((F."C_HOUR2" - S."C_HOUR2") / 10000.0 AS int)/ 100.0, "unixepoch"), 4) || SUBSTR(printf("%.2f", CAST((F."C_HOUR2" - S."C_HOUR2") / 10000.0 AS int)/ 100.0 - CAST(CAST((F."C_HOUR2" - S."C_HOUR2") / 10000.0 AS int)/ 100.0 AS int)), 2) AS net_time
FROM "TTIMERECORDS_HEAT{run}_FINISH" AS F
JOIN "TTIMERECORDS_HEAT{run}_START" AS S ON (S."C_NUM" = F."C_NUM" AND S."C_STATUS" = 0)
WHERE (F."C_STATUS" = 0 OR F."C_STATUS" = 131840)
AND bib > 0 AND (bib < 901 OR bib > 909)
ORDER BY F."C_LINE"'''


def get_first_last_best_run(tempdir, run, system, first=0, last=0, best=0):
    conn = create_connection(os.path.join(tempdir, "File2"))

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
            if d['net_raw'] < result_best.net_raw and d['status'] == 0:
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
    return result_first, result_last, result_best


def write_tdtr(results, first, last, best, system, run):
    for r in results['AL_timingreport']['Timing']['Times']:
        if int(r['Run']) == run:
            times = r
            if system == 'A':
                times['Bibfirst']['no'] = first.bib
                times['Bibfirst']['Net'] = first.net_time
            for s in times['Bibfirst']['Start']:
                if s['System'] == system:
                    s['.'] = first.start
            for s in times['Bibfirst']['Finish']:
                if s['System'] == system:
                    s['.'] = first.finish

            if system == 'A':
                times['Biblast']['no'] = last.bib
                times['Biblast']['Net'] = last.net_time
            for s in times['Biblast']['Start']:
                if s['System'] == system:
                    s['.'] = last.start
            for s in times['Biblast']['Finish']:
                if s['System'] == system:
                    s['.'] = last.finish

            if system == 'A':
                times['BestA']['Bib'] = best.bib
                times['BestA']['Time'] = best.net_time
            break

jury_processor = xml.dictionary('Jury', [
    xml.string('.', attribute='Function'),
    xml.string('Lastname'),
    xml.string('Firstname'),
    xml.string('Nation'),
    xml.string('Number', required=False, omit_empty=True),
    xml.string('Email', required=False, omit_empty=True),
    xml.string('Phonenbr', required=False, omit_empty=True),
])

timer_processor = xml.dictionary('Timer', [
    xml.string('.', attribute='System'),
    xml.string('.', attribute='used'),
    xml.string('Brand'),
    xml.string('Model'),
    xml.string('Serial'),
    xml.string('Homologation')
])

timer_start_processor = xml.dictionary('Timer_start', [
    xml.string('.', attribute='System'),
    xml.string('Brand'),
    xml.string('Model'),
    xml.string('Serial'),
    xml.string('Homologation')
])

startdevice_processor = xml.dictionary('Startdevice', [
    xml.string('.', attribute='Type'),
    xml.string('Brand'),
    xml.string('Model'),
    xml.string('Serial'),
    xml.string('Homologation')
])

finishcells_processor = xml.dictionary('Finishcells', [
    xml.string('.', attribute='System'),
    xml.string('Brand'),
    xml.string('Model'),
    xml.string('Serial'),
    xml.string('Homologation')
])

photofinish_processor = xml.dictionary('Photofinish', [
    xml.string('.', attribute='System'),
    xml.string('Brand'),
    xml.string('Model'),
    xml.string('Serial'),
])

videofinish_processor = xml.dictionary('Videofinish', [
    xml.string('Brand'),
    xml.string('Model'),
    xml.string('Resolution'),
    xml.string('Frequency'),
])

software_processor = xml.dictionary('Software', [
    xml.string('Brand'),
    xml.string('Version')
])

mode_processor = xml.dictionary('Mode', [
    xml.string('.', attribute='System'),
    xml.string('.')
])

synccheck_processor = xml.dictionary('Synccheck', [
    xml.string('.', attribute='System'),
    xml.string('.')
])

start_processor = xml.dictionary('Start', [
    xml.string('.', attribute='System'),
    xml.string('.')
])

finish_processor = xml.dictionary('Finish', [
    xml.string('.', attribute='System'),
    xml.string('.')
])

bibfirst_processor = xml.dictionary('Bibfirst', [
    xml.string('.', attribute='no'),
    xml.string('.'),
    xml.array(start_processor),
    xml.array(finish_processor),
    xml.string('Net')
])

biblast_processor = xml.dictionary('Biblast', [
    xml.string('.', attribute='no'),
    xml.string('.'),
    xml.array(start_processor),
    xml.array(finish_processor),
    xml.string('Net')
])

times_processor = xml.dictionary('Times', [
    xml.string('.', attribute='Run'),
    xml.string('.'),
    bibfirst_processor,
    biblast_processor,
    xml.dictionary('BestA', [
        xml.string('Bib'),
        xml.string('Time')
    ]),
    xml.dictionary('Allresults', [
        xml.string('.', attribute='SystemA')
    ]),
    xml.string('Comment')
])

tdtr_processor = xml.dictionary('Fisresults', [
    xml.string('Timingreportversion'),
    xml.string('OSversion'),
    xml.string('XMLversion'),
    xml.integer('Draft'),
    xml.dictionary('Raceheader', [
        xml.string('.', attribute='Sector'),
        xml.string('.', attribute='Gender'),
        xml.integer('Season'),
        xml.string('Category'),
        xml.string('Discipline'),
        xml.string('Codex'),
        xml.string('NAT_code'),
        xml.string('Type'),
        xml.dictionary('Racedate', [
            xml.integer('Day'),
            xml.integer('Month'),
            xml.integer('Year')
        ]),
        xml.string('Place'),
        xml.string('Nation'),
        xml.string('Eventname')
    ]),
    xml.dictionary('AL_race', [
        xml.array(jury_processor)
    ]),
    xml.dictionary('AL_timingreport', [
        xml.dictionary('Timekeeper', [
            xml.string('Company'),
            xml.string('Lastname'),
            xml.string('Firstname'),
            xml.string('Nation'),
            xml.string('Email'),
            xml.string('Phonenbr')
        ]),
        xml.dictionary('Devices', [
            xml.array(timer_processor),
            xml.array(timer_start_processor),
            startdevice_processor,
            xml.array(finishcells_processor),
            xml.array(photofinish_processor),
            videofinish_processor,
            software_processor
        ]),
        xml.dictionary('Connections', [
            xml.array(mode_processor),
            xml.string('Voice')
        ]),
        xml.dictionary('Timing', [
            xml.integer('.', attribute='Runs'),
            xml.dictionary('Synchronisation', [
                xml.string('Sync'),
                xml.string('Handsync'),
                xml.array(synccheck_processor)
            ]),
            xml.array(times_processor),
            xml.string('CertifyFIS')
        ]),
    ])
])


def process_file(primary, backup, tdtr):
    tempdir = tempfile.gettempdir()
    print("Using temp dir: ", tempdir)
    with zipfile.ZipFile(primary, 'r') as zipObj:
        zipObj.extractall(path=tempdir)
    a_first_1, a_last_1, a_best_1 = get_first_last_best_run(tempdir,1, "Primary")
    a_first_2, a_last_2, a_best_2 = get_first_last_best_run(tempdir, 2, "Primary")

    with zipfile.ZipFile(backup, 'r') as zipObj:
        zipObj.extractall(path=tempdir)
    b_first_1, b_last_1, b_best_1 = get_first_last_best_run(tempdir, 1, "Backup", a_first_1.bib, a_last_1.bib, a_best_1.bib)
    b_first_2, b_last_2, b_best_2 = get_first_last_best_run(tempdir,2, "Backup", a_first_2.bib, a_last_2.bib, a_best_2.bib)

    results = xml.parse_from_file(tdtr_processor, tdtr, 'utf-8')
    write_tdtr(results, a_first_1, a_last_1, a_best_1, "A", 1)
    write_tdtr(results, b_first_1, b_last_1, b_best_1, "B", 1)
    write_tdtr(results, a_first_2, a_last_2, a_best_2, "A", 2)
    write_tdtr(results, b_first_2, b_last_2, b_best_2, "B", 2)

    # print(xml.serialize_to_string(tdtr_processor, results, indent='    '))
    xml.serialize_to_file(tdtr_processor, results, tdtr, 'utf=8', '  ')


def runit():
    if len(sys.argv) != 4:
        print("Usage: " + sys.argv[0] + " primary.spro backup.spro draft-tdtr.xml")
        exit(1)
    # tempdir = tempfile.gettempdir()
    # os.chdir(tempdir)
    process_file(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == '__main__':
    runit()
