"""What the other scripts know about files written by experiment and survey software.

Used by fair_scan.py, to recognise an export and its structure, and by
draft_dictionary.py, to fill the label and unit of the columns the software
writes on its own (key_resp.rt, Reaction Time, subject_nr ...). The labels
follow each program's documentation; draft_dictionary still marks them "to
check", because versions and settings change what a column holds.

Covered: Qualtrics, PsychoPy (and Pavlovia), jsPsych (and JATOS), Gorilla,
OpenSesame (and OSWeb), E-Prime. See references/software-exports.md.
"""

import re


def canon(name):
    """'Reaction Time', 'Reaction.Time', 'reaction_time' -> 'reactiontime'."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


# ------------------------------------------------------------- recognising a file

# columns each program writes on its own; a file is attributed to the program
# with the most matches, if it reaches `min`
SIGNATURES = {
    "Qualtrics": {"min": 4, "columns": {
        "startdate", "enddate", "status", "ipaddress", "progress", "durationinseconds", "finished",
        "recordeddate", "responseid", "distributionchannel", "userlanguage", "locationlatitude",
        "locationlongitude", "externalreference", "recipientemail"}},
    "PsychoPy": {"min": 2, "columns": {"psychopyversion", "framerate", "expname", "expstart"},
                 "patterns": [r"\.(thisRepN|thisTrialN|thisN|thisIndex)$", r"\.(rt|keys|corr|started|stopped)$"]},
    "jsPsych": {"min": 3, "columns": {"trialtype", "trialindex", "timeelapsed", "internalnodeid"}},
    "Gorilla": {"min": 3, "columns": {
        "eventindex", "utctimestamp", "utcdate", "utcdateandtime", "localtimestamp", "localtimezone",
        "experimentid", "experimentversion", "treenodekey", "repeatkey", "scheduleid",
        "participantpublicid", "participantprivateid", "participantstatus", "participantcompletioncode",
        "zonename", "zonetype", "taskname", "taskversion"}},
    "OpenSesame": {"min": 3, "columns": {
        "opensesameversion", "opensesamecodename", "subjectnr", "subjectparity", "logfile",
        "experimentfile", "experimentpath", "liverow", "repeatcycle"}},
    "E-Prime": {"min": 4, "columns": {
        "experimentname", "subject", "session", "procedure", "running", "sessiondate", "sessiontime",
        "sessiontimeutc", "randomseed", "displayrefreshrate", "clockinformation", "experimentversion"},
        "patterns": [r"\.(RT|ACC|RESP|CRESP|OnsetTime|OnsetDelay|RTTime|DurationError)$"]},
}


def detect_software(header):
    """Return (program, evidence) for a header, or (None, None)."""
    names = [h.strip() for h in header if str(h).strip()]
    cn = {canon(h) for h in names}
    best, best_score, evidence = None, 0, None
    for prog, sig in SIGNATURES.items():
        hits = sorted(cn & sig["columns"])
        score = len(hits)
        for pat in sig.get("patterns", []):
            matched = [h for h in names if re.search(pat, h)]
            if len(matched) >= 2:
                score += 2
                hits += matched[:3]
        if score >= sig["min"] and score > best_score:
            best, best_score, evidence = prog, score, hits[:6]
    return best, evidence


# experiment files and scripts: the instrument, not the analysis. They go in
# materials/ and are not run by run_code.py
EXPERIMENT_EXT = {
    ".psyexp": "PsychoPy Builder experiment", ".osexp": "OpenSesame experiment",
    ".opensesame": "OpenSesame experiment (old format)",
    ".es": "E-Prime experiment (E-Studio)", ".es2": "E-Prime 2 experiment (E-Studio)",
    ".es3": "E-Prime 3 experiment (E-Studio)", ".ebs": "E-Prime compiled script",
    ".ebs2": "E-Prime 2 compiled script", ".ebs3": "E-Prime 3 compiled script",
    ".qsf": "Qualtrics survey file", ".iqx": "Inquisit script", ".iqjs": "Inquisit script",
}
# (pattern, what it is, extensions where it applies): an analysis script that
# only reads PsychoPy or jsPsych data must not be taken for the experiment
EXPERIMENT_CODE = [
    (r"(?m)^\s*from\s+psychopy\s+import\s+[^\n]*\b(visual|core|event|sound|gui|monitors|hardware)\b|"
     r"^\s*import\s+psychopy\.(visual|core|event)|visual\.Window\s*\(", "PsychoPy experiment script", (".py",)),
    (r"PsychoJS|psychojs", "PsychoPy online experiment (PsychoJS)", (".js", ".html", ".htm")),
    (r"initJsPsych\s*\(|jsPsych\.init\s*\(|jspsych", "jsPsych experiment", (".js", ".html", ".htm")),
    (r"\blab\.(flow|html|canvas|core)\.", "lab.js experiment", (".js", ".html", ".htm")),
    (r"(?m)^\s*(import\s+expyriment|from\s+expyriment)", "Expyriment experiment script", (".py",)),
    (r"(?m)^\s*(from\s+libopensesame|import\s+libopensesame|from\s+opensesame)", "OpenSesame script", (".py",)),
    (r"Screen\s*\(\s*['\"]OpenWindow|PsychImaging\s*\(|KbCheck", "Psychtoolbox experiment (MATLAB)", (".m",)),
]


def experiment_role(path, text=""):
    """If a file is part of the experiment rather than the analysis, say what it is."""
    name = path.name if hasattr(path, "name") else str(path)
    ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    if ext in EXPERIMENT_EXT:
        return EXPERIMENT_EXT[ext]
    if re.search(r"_lastrun\.py$", name):
        return "PsychoPy experiment script (generated by Builder)"
    for pat, what, exts in EXPERIMENT_CODE:
        if ext in exts and re.search(pat, text[:200000]):
            return what
    return None


# --------------------------------------------------- columns written by the software

# (program, pattern on the column name, description). A pattern starting with
# "=" is an exact match on canon(name); otherwise it is a regex on the name
# itself, and {1} in the label is the first group (the component's name).
# unit: as written in the column. coding: only where the software fixes it.
KNOWN_COLUMNS = [
    # PsychoPy Builder (and Pavlovia, which writes the same columns)
    ("PsychoPy", r"^(.+)\.rt$", {"label": "Response time of the component {1}, from the start of the component",
                                 "unit": "seconds"}),
    ("PsychoPy", r"^(.+)\.keys$", {"label": "Key(s) pressed in the component {1}"}),
    ("PsychoPy", r"^(.+)\.corr$", {"label": "Whether the response in the component {1} was correct",
                                   "coding": "1 = correct; 0 = incorrect"}),
    ("PsychoPy", r"^(.+)\.duration$", {"label": "Duration recorded by the component {1} (for a keyboard: how long the key was held)",
                                       "unit": "seconds"}),
    ("PsychoPy", r"^(.+)\.started$", {"label": "Time the component {1} started, on the experiment clock", "unit": "seconds"}),
    ("PsychoPy", r"^(.+)\.stopped$", {"label": "Time the component {1} stopped, on the experiment clock", "unit": "seconds"}),
    ("PsychoPy", r"^(.+)\.thisRepN$", {"label": "Repetition number of the loop {1}, counted from 0"}),
    ("PsychoPy", r"^(.+)\.thisTrialN$", {"label": "Trial number within the current repetition of the loop {1}, counted from 0"}),
    ("PsychoPy", r"^(.+)\.thisN$", {"label": "Trial number across all repetitions of the loop {1}, counted from 0"}),
    ("PsychoPy", r"^(.+)\.thisIndex$", {"label": "Row of the conditions file used on this trial of the loop {1}, counted from 0"}),
    ("PsychoPy", r"^(.+)\.(x|y)$", {"label": "Mouse position recorded by the component {1}, in the experiment's units"}),
    ("PsychoPy", "=participant", {"label": "Participant identifier typed in the start dialog"}),
    ("PsychoPy", "=session", {"label": "Session label typed in the start dialog"}),
    ("PsychoPy", "=date", {"label": "Date and time the session started"}),
    ("PsychoPy", "=expname", {"label": "Name of the experiment"}),
    ("PsychoPy", "=psychopyversion", {"label": "Version of PsychoPy that ran the experiment"}),
    ("PsychoPy", "=framerate", {"label": "Refresh rate of the monitor, measured at the start", "unit": "Hz"}),
    ("PsychoPy", "=expstart", {"label": "Date and time the experiment started, with time zone"}),

    # jsPsych (same columns whether saved locally, on JATOS, Pavlovia or cognition.run)
    ("jsPsych", "=rt", {"label": "Response time, from the onset of the stimulus to the response", "unit": "milliseconds"}),
    ("jsPsych", "=trialtype", {"label": "jsPsych plugin used for the trial"}),
    ("jsPsych", "=trialindex", {"label": "Position of the trial in the experiment, counted from 0"}),
    ("jsPsych", "=timeelapsed", {"label": "Time from the start of the experiment to the end of the trial", "unit": "milliseconds"}),
    ("jsPsych", "=internalnodeid", {"label": "Position of the trial in the jsPsych timeline (internal identifier)"}),
    ("jsPsych", "=stimulus", {"label": "Stimulus shown on the trial"}),
    ("jsPsych", "=response", {"label": "Response: key or button for response plugins, an object of answers for survey plugins"}),
    ("jsPsych", "=responses", {"label": "Answers of a survey trial, as a JSON object (jsPsych 6)"}),
    ("jsPsych", "=keypress", {"label": "JavaScript key code of the key pressed (jsPsych 6)"}),
    ("jsPsych", "=buttonpressed", {"label": "Index of the button clicked, counted from 0 (jsPsych 6)"}),
    ("jsPsych", "=viewhistory", {"label": "Pages viewed and time spent on each (instructions plugin), as JSON"}),

    # OpenSesame / OSWeb
    ("OpenSesame", "=subjectnr", {"label": "Participant number entered at the start"}),
    ("OpenSesame", "=subjectparity", {"label": "Whether the participant number is odd or even", "coding": "odd; even"}),
    ("OpenSesame", "=responsetime", {"label": "Response time of the most recent response item", "unit": "milliseconds"}),
    ("OpenSesame", "=response", {"label": "Most recent response collected"}),
    ("OpenSesame", "=correct", {"label": "Whether the most recent response was correct", "coding": "1 = correct; 0 = incorrect"}),
    ("OpenSesame", "=correctresponse", {"label": "Expected (correct) response for the trial"}),
    ("OpenSesame", r"^response_time_(.+)$", {"label": "Response time collected by the item {1}", "unit": "milliseconds"}),
    ("OpenSesame", r"^correct_(.+)$", {"label": "Whether the response collected by the item {1} was correct",
                                       "coding": "1 = correct; 0 = incorrect"}),
    ("OpenSesame", r"^response_(.+)$", {"label": "Response collected by the item {1}"}),
    ("OpenSesame", r"^time_(.+)$", {"label": "Time the item {1} was last executed, from the start of the experiment",
                                    "unit": "milliseconds"}),
    ("OpenSesame", r"^count_(.+)$", {"label": "Number of times the item {1} had been executed before, counted from 0"}),
    ("OpenSesame", "=acc", {"label": "Running accuracy: percentage of correct responses so far", "unit": "%"}),
    ("OpenSesame", "=accuracy", {"label": "Running accuracy: percentage of correct responses so far", "unit": "%"}),
    ("OpenSesame", "=avgrt", {"label": "Running average response time so far", "unit": "milliseconds"}),
    ("OpenSesame", "=averageresponsetime", {"label": "Running average response time so far", "unit": "milliseconds"}),
    ("OpenSesame", "=totalcorrect", {"label": "Number of correct responses so far"}),
    ("OpenSesame", "=totalresponses", {"label": "Number of responses so far"}),
    ("OpenSesame", "=totalresponsetime", {"label": "Sum of the response times so far", "unit": "milliseconds"}),
    ("OpenSesame", "=datetime", {"label": "Date and time the session started"}),
    ("OpenSesame", "=logfile", {"label": "Path of the log file on the computer that ran the experiment"}),
    ("OpenSesame", "=experimentpath", {"label": "Folder of the experiment on the computer that ran it"}),
    ("OpenSesame", "=experimentfile", {"label": "Name of the experiment file"}),
    ("OpenSesame", "=opensesameversion", {"label": "Version of OpenSesame that ran the experiment"}),
    ("OpenSesame", "=opensesamecodename", {"label": "Code name of the OpenSesame version"}),
    ("OpenSesame", "=width", {"label": "Width of the display", "unit": "pixels"}),
    ("OpenSesame", "=height", {"label": "Height of the display", "unit": "pixels"}),

    # Gorilla (Task Builder 1 and 2, Questionnaire Builder 2); names with spaces,
    # or with dots after read.csv
    ("Gorilla", "=eventindex", {"label": "Order of the event within the participant's data"}),
    ("Gorilla", "=utctimestamp", {"label": "Time of the event, in milliseconds since 1 January 1970 (UTC)", "unit": "milliseconds"}),
    ("Gorilla", "=utcdate", {"label": "Date and time of the event (UTC)"}),
    ("Gorilla", "=utcdateandtime", {"label": "Date and time of the event (UTC)"}),
    ("Gorilla", "=localtimestamp", {"label": "Time of the event on the participant's device, in milliseconds since 1 January 1970", "unit": "milliseconds"}),
    ("Gorilla", "=localtimezone", {"label": "Time zone of the participant's device (offset from UTC)"}),
    ("Gorilla", "=localdate", {"label": "Date and time of the event on the participant's device"}),
    ("Gorilla", "=localdateandtime", {"label": "Date and time of the event on the participant's device"}),
    ("Gorilla", "=experimentid", {"label": "Gorilla identifier of the experiment"}),
    ("Gorilla", "=experimentversion", {"label": "Version of the experiment the participant took part in"}),
    ("Gorilla", "=treenodekey", {"label": "Key of the experiment-tree node (task or questionnaire) that produced the row"}),
    ("Gorilla", "=repeatkey", {"label": "Key of the repeat node and iteration, if the node was repeated"}),
    ("Gorilla", "=scheduleid", {"label": "Identifier of this participant's run of the task at this node"}),
    ("Gorilla", "=participantpublicid", {"label": "Participant ID from the recruitment platform (e.g. Prolific): can identify the person"}),
    ("Gorilla", "=participantprivateid", {"label": "Anonymous participant ID assigned by Gorilla"}),
    ("Gorilla", "=participantstartinggroup", {"label": "Group the participant was assigned to at the start"}),
    ("Gorilla", "=participantstatus", {"label": "Status of the participant (e.g. complete)"}),
    ("Gorilla", "=participantcompletioncode", {"label": "Completion code shown to the participant"}),
    ("Gorilla", "=participantexternalsessionid", {"label": "Session ID from the recruitment platform"}),
    ("Gorilla", "=participantdevicetype", {"label": "Type of device (computer, mobile, tablet)"}),
    ("Gorilla", "=participantdevice", {"label": "Device of the participant"}),
    ("Gorilla", "=participantos", {"label": "Operating system of the participant's device"}),
    ("Gorilla", "=participantbrowser", {"label": "Browser of the participant"}),
    ("Gorilla", "=participantmonitorsize", {"label": "Screen size of the participant's device", "unit": "pixels"}),
    ("Gorilla", "=participantviewportsize", {"label": "Size of the browser window", "unit": "pixels"}),
    ("Gorilla", "=taskname", {"label": "Name of the task"}),
    ("Gorilla", "=taskversion", {"label": "Version of the task"}),
    ("Gorilla", "=trialnumber", {"label": "Trial number within the task"}),
    ("Gorilla", "=screennumber", {"label": "Number of the screen within the trial"}),
    ("Gorilla", "=screenname", {"label": "Name of the screen"}),
    ("Gorilla", "=screen", {"label": "Name of the screen"}),
    ("Gorilla", "=zonename", {"label": "Name of the zone that produced the row (Task Builder 1)"}),
    ("Gorilla", "=zonetype", {"label": "Type of the zone that produced the row, e.g. a response (Task Builder 1)"}),
    ("Gorilla", "=componentname", {"label": "Name of the component that produced the row (Task Builder 2)"}),
    ("Gorilla", "=objectname", {"label": "Name of the object that produced the row"}),
    ("Gorilla", "=objectid", {"label": "Identifier of the object that produced the row"}),
    ("Gorilla", "=reactiontime", {"label": "Time from the start of the screen to the response", "unit": "milliseconds"}),
    ("Gorilla", "=response", {"label": "Response given"}),
    ("Gorilla", "=responsetype", {"label": "Kind of row (Questionnaire Builder 2): continue, action, info or response"}),
    ("Gorilla", "=attempt", {"label": "Attempt number for this trial"}),
    ("Gorilla", "=correct", {"label": "Whether the response was correct", "coding": "1 = correct; 0 = incorrect"}),
    ("Gorilla", "=incorrect", {"label": "Whether the response was incorrect", "coding": "1 = incorrect; 0 = correct"}),
    ("Gorilla", "=timedout", {"label": "Whether the screen ended because time ran out"}),
    ("Gorilla", "=spreadsheetname", {"label": "Name of the spreadsheet that defined the trials"}),
    ("Gorilla", "=spreadsheetrow", {"label": "Row of the spreadsheet used on this trial"}),
    ("Gorilla", "=display", {"label": "Display (trial template) used, from the spreadsheet"}),
    ("Gorilla", "=xcoordinate", {"label": "Horizontal position of the response"}),
    ("Gorilla", "=ycoordinate", {"label": "Vertical position of the response"}),
    ("Gorilla", r"(?i)^store\s*:\s*(.+)$", {"label": "Value stored in the field {1}"}),

    # Qualtrics
    ("Qualtrics", "=startdate", {"label": "Date and time the response was started"}),
    ("Qualtrics", "=enddate", {"label": "Date and time the response was ended"}),
    ("Qualtrics", "=recordeddate", {"label": "Date and time the response was recorded"}),
    ("Qualtrics", "=status", {"label": "Type of response (normal, preview, test, imported, spam ...)"}),
    ("Qualtrics", "=ipaddress", {"label": "IP address of the respondent: personal data"}),
    ("Qualtrics", "=progress", {"label": "Share of the survey completed", "unit": "%"}),
    ("Qualtrics", "=durationinseconds", {"label": "Time from the start to the end of the response", "unit": "seconds"}),
    ("Qualtrics", "=finished", {"label": "Whether the respondent reached the end of the survey", "coding": "1 = finished; 0 = not finished"}),
    ("Qualtrics", "=responseid", {"label": "Qualtrics identifier of the response"}),
    ("Qualtrics", "=recipientlastname", {"label": "Last name of the recipient (from the contact list): personal data"}),
    ("Qualtrics", "=recipientfirstname", {"label": "First name of the recipient (from the contact list): personal data"}),
    ("Qualtrics", "=recipientemail", {"label": "E-mail of the recipient (from the contact list): personal data"}),
    ("Qualtrics", "=externalreference", {"label": "External data reference: an identifier linked to the respondent"}),
    ("Qualtrics", "=locationlatitude", {"label": "Approximate latitude estimated from the IP address: personal data"}),
    ("Qualtrics", "=locationlongitude", {"label": "Approximate longitude estimated from the IP address: personal data"}),
    ("Qualtrics", "=distributionchannel", {"label": "How the survey reached the respondent (anonymous link, e-mail, preview ...)"}),
    ("Qualtrics", "=userlanguage", {"label": "Language code the survey was shown in"}),
    ("Qualtrics", r"(?i)^(.+)_First Click$", {"label": "Time to the first click on the page of {1}", "unit": "seconds"}),
    ("Qualtrics", r"(?i)^(.+)_Last Click$", {"label": "Time to the last click on the page of {1}", "unit": "seconds"}),
    ("Qualtrics", r"(?i)^(.+)_Page Submit$", {"label": "Time to the submission of the page of {1}", "unit": "seconds"}),
    ("Qualtrics", r"(?i)^(.+)_Click Count$", {"label": "Number of clicks on the page of {1}"}),

    # E-Prime (E-DataAid export, or log .txt)
    ("E-Prime", r"^(.+)\.RT$", {"label": "Response time to the object {1}, from its onset", "unit": "milliseconds"}),
    ("E-Prime", r"^(.+)\.ACC$", {"label": "Accuracy of the response to the object {1}", "coding": "1 = correct; 0 = incorrect"}),
    ("E-Prime", r"^(.+)\.RESP$", {"label": "Response given to the object {1}"}),
    ("E-Prime", r"^(.+)\.CRESP$", {"label": "Correct response for the object {1}"}),
    ("E-Prime", r"^(.+)\.RTTime$", {"label": "Time of the response to the object {1}, on the E-Prime clock", "unit": "milliseconds"}),
    ("E-Prime", r"^(.+)\.OnsetTime$", {"label": "Onset time of the object {1}, on the E-Prime clock", "unit": "milliseconds"}),
    ("E-Prime", r"^(.+)\.OnsetDelay$", {"label": "Delay between the intended and the actual onset of the object {1}", "unit": "milliseconds"}),
    ("E-Prime", r"^(.+)\.OffsetTime$", {"label": "Offset time of the object {1}, on the E-Prime clock", "unit": "milliseconds"}),
    ("E-Prime", r"^(.+)\.DurationError$", {"label": "Difference between the intended and the actual duration of the object {1}", "unit": "milliseconds"}),
    ("E-Prime", r"^(.+)\.Duration$", {"label": "Duration of the object {1}", "unit": "milliseconds"}),
    ("E-Prime", r"^(.+)\.Cycle$", {"label": "Cycle of the list {1}"}),
    ("E-Prime", r"^(.+)\.Sample$", {"label": "Sample (row draw) of the list {1}"}),
    ("E-Prime", "=experimentname", {"label": "Name of the experiment"}),
    ("E-Prime", "=experiment", {"label": "Name of the experiment"}),
    ("E-Prime", "=subject", {"label": "Subject number entered at the start"}),
    ("E-Prime", "=session", {"label": "Session number entered at the start"}),
    ("E-Prime", "=sessiondate", {"label": "Date of the session"}),
    ("E-Prime", "=sessiontime", {"label": "Time of day the session started"}),
    ("E-Prime", "=sessiontimeutc", {"label": "Time the session started (UTC)"}),
    ("E-Prime", "=procedure", {"label": "Procedure that ran this row"}),
    ("E-Prime", "=running", {"label": "List that ran this row"}),
    ("E-Prime", "=randomseed", {"label": "Seed of E-Prime's random number generator for the session"}),
    ("E-Prime", "=displayrefreshrate", {"label": "Refresh rate of the display", "unit": "Hz"}),
    ("E-Prime", "=clockinformation", {"label": "Technical information on E-Prime's clock (XML)"}),
]

_COMPILED = [(prog, pat, re.compile(pat) if not pat.startswith("=") else None, desc) for prog, pat, desc in KNOWN_COLUMNS]


def describe_column(program, name):
    """The documented meaning of a column the program writes on its own, or None.
    E-DataAid's level-qualified names (Procedure[Block]) are described from the
    base name."""
    if not program:
        return None
    lv = re.match(r"^(.+)\[(.+)\]$", name.strip())
    if lv:
        base = describe_column(program, lv.group(1))
        if base:
            base["label"] += f" (value at the {lv.group(2)} level)"
        return base
    cn = canon(name)
    for prog, pat, rx, desc in _COMPILED:
        if prog != program:
            continue
        if rx is None:
            if cn == pat[1:]:
                return dict(desc)
        else:
            m = rx.search(name.strip())
            if m:
                out = dict(desc)
                out["label"] = out["label"].replace("{1}", m.group(1) if m.groups() else "")
                return out
    return None


# --------------------------------------------------------------- E-Prime log files

def is_eprime_log(text):
    return "*** Header Start ***" in text[:4000]


def parse_eprime_log(text):
    """Turn an E-Prime log (.txt written during the session) into a table.

    The log is a sequence of frames ("*** LogFrame Start ***" ... "End"), each
    with a Level. Rows are the frames of the most frequent level (usually the
    trials); each row also gets the values of the frames that enclose it (block,
    session: in the log they come after their trials) and of the header, as
    E-DataAid does. Returns (header_row, rows, info)."""
    level_names, header, frames = [], {}, []
    mode, level, cur = None, None, None
    for raw in text.splitlines():
        line = raw.strip()
        if line == "*** Header Start ***":
            mode = "header"
            continue
        if line == "*** Header End ***":
            mode = None
            continue
        if line == "*** LogFrame Start ***":
            mode, cur = "frame", {}
            continue
        if line == "*** LogFrame End ***":
            frames.append((level or 0, cur))
            mode, cur = None, None
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()
        if mode == "header":
            if k == "LevelName":
                level_names.append(v)
            else:
                header[k] = v
        elif mode == "frame":
            cur[k] = v
        elif k == "Level":
            try:
                level = int(v)
            except ValueError:
                level = None
    if not frames:
        table = [list(header), list(header.values())] if header else []
        return table, {"levels": {}, "row_level": None}
    counts = {}
    for lv, _ in frames:
        counts[lv] = counts.get(lv, 0) + 1
    row_level = max(counts, key=lambda lv: (counts[lv], lv))
    # walk backwards: a frame of a lower level encloses the frames before it
    parents, rows = {}, []
    for lv, fr in reversed(frames):
        if lv < row_level:
            parents[lv] = fr
            for deeper in [k for k in parents if k > lv]:
                del parents[deeper]
        elif lv == row_level:
            rows.append((fr, {k: v for k, v in parents.items()}))
    rows.reverse()

    def lname(lv):
        return level_names[lv - 1] if 0 < lv <= len(level_names) else f"Level{lv}"

    columns, table = [], []
    for fr, par in rows:
        row = dict(header)
        for lv in sorted(par):
            for k, v in par[lv].items():
                row[k if k not in fr else f"{k}[{lname(lv)}]"] = v
        row.update(fr)
        for k in row:
            if k not in columns:
                columns.append(k)
        table.append(row)
    body = [[r.get(c, "") for c in columns] for r in table]
    info = {"levels": {lname(k): v for k, v in sorted(counts.items())}, "row_level": lname(row_level)}
    return [columns] + body, info
