#!/usr/bin/env python3
"""
Schedule Combinator
--------------------

Companion to prepreg_scraper.py. Give it several course codes (the ones
you're planning to register for this semester) and it works out every
possible way to pick one section per course such that:

  * no two chosen sections' class times overlap (theory OR lab), and
  * no two chosen sections' final exam times overlap.

Every surviving combination is a valid "course adjustment" -- a full
semester schedule with zero clashes. All of them are written out to a PDF
(one option per page, laid out as a weekly class schedule) and/or a CSV, so
you can just flip through and pick the one that suits you.

Note: final-exam times are *only* used to filter out clashing combinations --
they are deliberately left out of the weekly class-schedule table itself
(exams aren't a weekly recurring thing), but they're listed separately at the
bottom of each page for your records.

You can also ask for a specific number of class-days per week (e.g. "I only
want to be on campus 3 days a week") with --target-days, and either sort by
closeness to that (--sort-by target_days,gap) or hard-filter to it exactly
(--exact-days).

Usage
-----
    python schedule_combinator.py CSE370 CSE470 EEE201
    python schedule_combinator.py CSE370 CSE470 EEE201 MAT361 --only-open
    python schedule_combinator.py --from-file my_courses.txt --max-results 20
    python schedule_combinator.py CSE370 CSE470 --format csv
    python schedule_combinator.py CSE370 CSE470 EEE201 --target-days 3 --sort-by target_days,gap

Run `python schedule_combinator.py --help` for all options.

Prefer clicking over typing flags? `schedule_gui.py` is a single-window GUI
(no popups) for all of the above -- run `python schedule_gui.py`.

This file lives next to prepreg_scraper.py and reuses its feed-fetching /
schedule-parsing helpers, so keep them in the same folder.
"""

import argparse
import csv
import itertools
import heapq
from functools import lru_cache
import re
import sys
from datetime import datetime
from pathlib import Path

# Reuse everything already built for the single-course organizer.
from prepreg_scraper import (
    DAY_ORDER,
    DEFAULT_FEED_URL,
    _12h_to_minutes,
    fetch_feed,
    format_meetings,
    get_lab_meetings,
    get_theory_meetings,
    suggest_similar,
)

# --------------------------------------------------------------------------
# Final-exam parsing (best-effort -- the feed only gives us free text here)
# --------------------------------------------------------------------------

DATE_TOKEN_RE = re.compile(
    r"\d{1,2}[-/][A-Za-z]{3,9}[-/]\d{4}"          # 07-DEC-2025 / 07/December/2025
    r"|\d{4}-\d{2}-\d{2}"                          # 2025-12-07
    r"|\d{1,2}/\d{1,2}/\d{4}"                      # 12/07/2025
    r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}"          # December 7, 2025 / Dec 07 2025
    r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"            # 07 December 2025
)

TIME_RANGE_RE = re.compile(
    r"(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(\d{1,2}:\d{2}\s*[AP]M)", re.IGNORECASE
)

DATE_FORMATS = [
    "%d-%b-%Y", "%d-%B-%Y", "%d/%b/%Y",
    "%Y-%m-%d",
    "%m/%d/%Y", "%d/%m/%Y",
    "%B %d %Y", "%b %d %Y",
    "%d %B %Y", "%d %b %Y",
]


def _parse_exam_date(token):
    cleaned = token.replace(",", "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt.replace(",", "")).date()
        except ValueError:
            continue
    return None


def get_exam_window(section):
    """Best-effort extraction of (date, start_minutes, end_minutes) from the
    feed's free-text finalExamDetail field. Returns a dict with 'parsed'
    False when the text can't be confidently read -- unparsed exams are
    never treated as conflicting (we don't want to hide a valid schedule
    just because we couldn't read the exam text), but they're still shown
    on the page so you can eyeball them yourself."""
    sched = section.get("sectionSchedule") or {}
    raw = (sched.get("finalExamDetail") or "").strip()
    if not raw or raw.upper() in ("N/A", "NA", "TBA", "NONE", "-"):
        return {"raw": raw or "N/A", "date": None, "start": None, "end": None, "parsed": False}

    date_obj = None
    date_match = DATE_TOKEN_RE.search(raw)
    if date_match:
        date_obj = _parse_exam_date(date_match.group(0))

    start_min = end_min = None
    time_match = TIME_RANGE_RE.search(raw)
    if time_match:
        try:
            start_min = _12h_to_minutes(time_match.group(1))
            end_min = _12h_to_minutes(time_match.group(2))
        except ValueError:
            pass

    parsed = date_obj is not None and start_min is not None and end_min is not None
    return {"raw": raw, "date": date_obj, "start": start_min, "end": end_min, "parsed": parsed}


def exam_conflict(w1, w2):
    if not w1["parsed"] or not w2["parsed"]:
        return False
    if w1["date"] != w2["date"]:
        return False
    return w1["start"] < w2["end"] and w2["start"] < w1["end"]


# --------------------------------------------------------------------------
# Class-time conflict checking
# --------------------------------------------------------------------------

def meetings_conflict(m1, m2):
    return m1.day == m2.day and m1.start_minutes < m2.end_minutes and m2.start_minutes < m1.end_minutes


def is_valid_combo(combo):
    """combo: tuple of section-rows, one per course."""
    n = len(combo)
    for i in range(n):
        for j in range(i + 1, n):
            for m1 in combo[i]["all_meetings"]:
                for m2 in combo[j]["all_meetings"]:
                    if meetings_conflict(m1, m2):
                        return False
            if exam_conflict(combo[i]["exam"], combo[j]["exam"]):
                return False
    return True


def gap_score(combo):
    """Total idle minutes between classes, summed across days used this
    combo. Lower = more compact/less time wasted on campus between classes."""
    by_day = {}
    for r in combo:
        for m in r["all_meetings"]:
            by_day.setdefault(m.day, []).append((m.start_minutes, m.end_minutes))
    total_gap = 0
    for intervals in by_day.values():
        intervals.sort()
        span = max(e for _, e in intervals) - intervals[0][0]
        busy = sum(e - s for s, e in intervals)
        total_gap += span - busy
    return total_gap


def earliest_start_score(combo):
    starts = [m.start_minutes for r in combo for m in r["all_meetings"]]
    return min(starts) if starts else 0


def latest_end_score(combo):
    ends = [m.end_minutes for r in combo for m in r["all_meetings"]]
    return max(ends) if ends else 0


def days_used_score(combo):
    """Number of distinct weekdays this combo has any class on (theory or
    lab). Lower = classes packed onto fewer days = more full days off."""
    days = set()
    for r in combo:
        for m in r["all_meetings"]:
            days.add(m.day)
    return len(days)


def target_days_score(combo, target_days):
    """Absolute distance between this combo's day-count and the desired
    number of class days per week. Lower = closer to what was asked for.
    If target_days is None this is meaningless and callers shouldn't use
    it as a sort key."""
    return abs(days_used_score(combo) - target_days)


# --------------------------------------------------------------------------
# Section matching and mandatory section constraints
# --------------------------------------------------------------------------

def normalize_sec_str(sec):
    sec = str(sec).strip().upper()
    if sec.startswith("SECTION"):
        sec = sec[7:].strip()
    elif sec.startswith("SEC"):
        sec = sec[3:].strip()
    return sec


def section_name_matches(actual_name, target_name):
    """Smart matching for section names:
    - '01' matches '01' or '1'
    - 'Sec 01' matches '1'
    - '01A' matches '1A' or '01A'
    """
    a = normalize_sec_str(actual_name)
    t = normalize_sec_str(target_name)
    if not a or not t:
        return False
    if a == t:
        return True
    try:
        if int(a) == int(t):
            return True
    except ValueError:
        pass
    match_a = re.match(r"^0*(\d+)(.*)$", a)
    match_t = re.match(r"^0*(\d+)(.*)$", t)
    if match_a and match_t:
        if match_a.group(1) == match_t.group(1) and match_a.group(2) == match_t.group(2):
            return True
    return False


def parse_mandatory_sections(tokens):
    """tokens like ['CSE370:01', 'MAT215:02,03', '01'] ->
    {'global': {'01'}, 'per_course': {'CSE370': {'01'}, 'MAT215': {'02', '03'}}}.
    A bare section applies across all courses (if no course is prefixed);
    'COURSE:SEC1,SEC2' restricts it to that course."""
    result = {"global": set(), "per_course": {}}
    if not tokens:
        return result
    if isinstance(tokens, str):
        tokens = [t.strip() for t in re.split(r"[,;\s]+", tokens) if t.strip()]
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        if ":" in tok:
            course, secs = tok.split(":", 1)
            course = course.strip().upper()
            sec_set = {s.strip().upper() for s in re.split(r"[,;]+", secs) if s.strip()}
            result["per_course"].setdefault(course, set()).update(sec_set)
        else:
            for s in re.split(r"[,;]+", tok):
                s = s.strip().upper()
                if s:
                    result["global"].add(s)
    return result


def extract_course_codes_and_sections(raw_courses):
    """Takes course input tokens which might contain inline sections, e.g.
    ['CSE370:01', 'CSE470', 'MAT215:02,03'], and separates them into ordered
    course codes ['CSE370', 'CSE470', 'MAT215'] and an inline section map
    {'CSE370': {'01'}, 'MAT215': {'02', '03'}}."""
    ordered_codes = []
    inline_sections = {}
    for item in raw_courses or []:
        tok = item.strip()
        if not tok:
            continue
        if ":" in tok:
            parts = tok.split(":", 1)
            code = parts[0].strip().upper()
            sec_part = parts[1].strip()
            if code:
                if code not in ordered_codes:
                    ordered_codes.append(code)
                if sec_part:
                    secs = {s.strip().upper() for s in re.split(r"[,;]+", sec_part) if s.strip()}
                    inline_sections.setdefault(code, set()).update(secs)
        else:
            code = tok.strip().upper()
            if code and code not in ordered_codes:
                ordered_codes.append(code)
    return ordered_codes, inline_sections


def filter_mandatory_sections(rows, target_secs, course_code):
    """Filters section rows for course_code to only those matching target_secs.
    Returns (kept_rows, dropped_rows)."""
    if not target_secs:
        return rows, []
    kept, dropped = [], []
    for r in rows:
        sec_name = r.get("sectionName") or ""
        if any(section_name_matches(sec_name, t) for t in target_secs):
            kept.append(r)
        else:
            dropped.append(r)
    return kept, dropped


# --------------------------------------------------------------------------
# Faculty preference
# --------------------------------------------------------------------------

def parse_faculty_preferences(tokens):
    """tokens like ['AIB', 'DZK', 'CSE370:TAZ,MTR'] ->
    {'global': {'AIB', 'DZK'}, 'per_course': {'CSE370': {'TAZ', 'MTR'}}}.
    A bare name applies to every course; 'COURSE:NAME1,NAME2' restricts it
    to just that course. Matching is a case-insensitive substring check
    against the section's faculty field (which can list more than one
    initial for team-taught sections)."""
    prefs = {"global": set(), "per_course": {}}
    if not tokens:
        return prefs
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        if ":" in tok:
            course, names = tok.split(":", 1)
            course = course.strip().upper()
            name_set = {n.strip().upper() for n in names.split(",") if n.strip()}
            prefs["per_course"].setdefault(course, set()).update(name_set)
        else:
            prefs["global"].add(tok.strip().upper())
    return prefs


def section_matches_faculty_pref(row, prefs):
    if not prefs["global"] and not prefs["per_course"]:
        return False
    fac = (row["faculty"] or "").upper()
    names = set(prefs["global"]) | prefs["per_course"].get(row["course_code"], set())
    return any(n and n in fac for n in names)


def filter_out_avoided_faculty(rows, avoid_prefs):
    """Drop sections taught by anyone in avoid_prefs (hard exclusion, not
    just a ranking preference). Returns (kept_rows, dropped_rows)."""
    if not avoid_prefs["global"] and not avoid_prefs["per_course"]:
        return rows, []
    kept, dropped = [], []
    for r in rows:
        (dropped if section_matches_faculty_pref(r, avoid_prefs) else kept).append(r)
    return kept, dropped


def filter_non_preferred_faculty(rows, prefer_prefs, course_code):
    """If mandatory preferred faculty is enabled, drop any section for course_code
    that does NOT match the preferred faculty specified for this course or globally.
    Returns (kept_rows, dropped_rows)."""
    names = set(prefer_prefs["global"]) | prefer_prefs["per_course"].get(course_code.upper(), set())
    if not names:
        return rows, []
    kept, dropped = [], []
    for r in rows:
        fac = (r["faculty"] or "").upper()
        if any(n and n in fac for n in names):
            kept.append(r)
        else:
            dropped.append(r)
    return kept, dropped


DAY_NAME_MAP = {
    "SUN": "SUNDAY", "SUNDAY": "SUNDAY",
    "MON": "MONDAY", "MONDAY": "MONDAY",
    "TUE": "TUESDAY", "TUESDAY": "TUESDAY", "TUES": "TUESDAY",
    "WED": "WEDNESDAY", "WEDNESDAY": "WEDNESDAY",
    "THU": "THURSDAY", "THURSDAY": "THURSDAY", "THUR": "THURSDAY", "THURS": "THURSDAY",
    "FRI": "FRIDAY", "FRIDAY": "FRIDAY",
    "SAT": "SATURDAY", "SATURDAY": "SATURDAY",
}


def _parse_time_str(t_str):
    """Parses time strings like '08:00 AM', '8:00AM', '8AM', '8:00', '17:00' into minutes since midnight."""
    t_str = t_str.strip().upper()
    match_12h = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*([AP]M)$", t_str)
    if match_12h:
        hr = int(match_12h.group(1))
        mn = int(match_12h.group(2) or 0)
        ampm = match_12h.group(3)
        if ampm == "PM" and hr < 12:
            hr += 12
        elif ampm == "AM" and hr == 12:
            hr = 0
        return hr * 60 + mn

    match_24h = re.match(r"^(\d{1,2}):(\d{2})$", t_str)
    if match_24h:
        hr = int(match_24h.group(1))
        mn = int(match_24h.group(2))
        if 1 <= hr <= 7:
            hr += 12
        return hr * 60 + mn

    match_hr = re.match(r"^(\d{1,2})$", t_str)
    if match_hr:
        hr = int(match_hr.group(1))
        if 1 <= hr <= 7:
            hr += 12
        return hr * 60

    raise ValueError(f"unrecognized time format '{t_str}'")


def parse_skip_times(tokens):
    """Parses skip time tokens into structured rules:
    - '08:00 AM - 09:20 AM'
    - 'Sun 08:00 AM - 09:20 AM'
    - '05:00 PM - 06:20 PM'
    - '8:00 AM'
    """
    if not tokens:
        return []
    if isinstance(tokens, str):
        tokens = [t.strip() for t in re.split(r"[,;]", tokens) if t.strip()]

    rules = []
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue

        days = set()
        words = tok.split()
        time_part_words = []

        for w in words:
            w_clean = w.strip(",;").upper()
            if w_clean in DAY_NAME_MAP:
                days.add(DAY_NAME_MAP[w_clean])
            else:
                time_part_words.append(w)

        time_part = " ".join(time_part_words).strip()
        if not time_part:
            continue

        if "-" in time_part:
            parts = time_part.split("-", 1)
            try:
                start_min = _parse_time_str(parts[0])
                end_min = _parse_time_str(parts[1])
                if start_min > end_min:
                    start_min, end_min = end_min, start_min
                rules.append({
                    "raw": tok,
                    "days": days,
                    "start_minutes": start_min,
                    "end_minutes": end_min,
                    "is_point_time": False,
                })
            except ValueError as e:
                raise CombinatorError(f"Invalid skip time format in '{tok}': {e}")
        else:
            try:
                t_min = _parse_time_str(time_part)
                rules.append({
                    "raw": tok,
                    "days": days,
                    "start_minutes": t_min,
                    "end_minutes": t_min,
                    "is_point_time": True,
                })
            except ValueError as e:
                raise CombinatorError(f"Invalid skip time format in '{tok}': {e}")

    return rules


def section_overlaps_skip_rules(row, skip_rules):
    if not skip_rules:
        return False, None
    for m in row["all_meetings"]:
        for rule in skip_rules:
            if rule["days"] and m.day not in rule["days"]:
                continue
            if rule["is_point_time"]:
                if m.start_minutes <= rule["start_minutes"] < m.end_minutes or m.start_minutes == rule["start_minutes"]:
                    return True, m
            else:
                if m.start_minutes < rule["end_minutes"] and rule["start_minutes"] < m.end_minutes:
                    return True, m
    return False, None


def filter_out_skipped_times(rows, skip_rules):
    if not skip_rules:
        return rows, []
    kept, dropped = [], []
    for r in rows:
        overlaps, meeting = section_overlaps_skip_rules(r, skip_rules)
        if overlaps:
            dropped.append((r, meeting))
        else:
            kept.append(r)
    return kept, dropped



def faculty_match_count(combo, prefs):
    return sum(1 for r in combo if section_matches_faculty_pref(r, prefs))


def faculty_score(combo, prefs):
    """Lower is better, so more preferred-faculty matches -> lower score."""
    return -faculty_match_count(combo, prefs)


SORT_KEY_CHOICES = ("gap", "days", "target_days", "earliest", "latest", "faculty", "none")


class CombinatorError(Exception):
    """Raised for any user-facing error in the combinator pipeline (bad
    course code, no feed data, contradictory options, etc). The CLI catches
    this and exits with a message; the GUI catches it and shows it inline
    instead of crashing."""


def build_sort_key_fn(sort_by, prefs, target_days=None, on_warning=print):
    """sort_by is a comma-separated list, e.g. 'target_days,gap' -- closest
    match to the desired day-count first, ties broken by the most compact
    schedule. Every individual score is normalized so lower = better, so
    the combined tuple can always be sorted ascending."""
    keys = [k.strip().lower() for k in sort_by.split(",") if k.strip()]
    if not keys:
        keys = ["gap"]
    bad = [k for k in keys if k not in SORT_KEY_CHOICES]
    if bad:
        raise CombinatorError(
            f"unknown --sort-by key(s): {', '.join(bad)}. Choose from: {', '.join(SORT_KEY_CHOICES)}"
        )
    if "faculty" in keys and not prefs["global"] and not prefs["per_course"]:
        on_warning("  ! --sort-by includes 'faculty' but no --prefer-faculty was given, so it has no effect.")
    if "target_days" in keys and target_days is None:
        on_warning("  ! --sort-by includes 'target_days' but no --target-days was given, so it has no effect.")

    funcs = {
        "gap": gap_score,
        "days": days_used_score,
        "target_days": (lambda c: target_days_score(c, target_days)) if target_days is not None else (lambda c: 0),
        "earliest": earliest_start_score,
        "latest": lambda c: -latest_end_score(c),
        "faculty": lambda c: faculty_score(c, prefs),
        "none": lambda c: 0,
    }

    def key_fn(combo):
        return tuple(funcs[k](combo) for k in keys)

    return key_fn, keys


def search_combinations(per_course_lists, sort_keys, prefs, target_days=None,
                        exact_days=False, max_results=30):
    """Count every valid combination and retain the exact best results.

    Pair conflicts are evaluated once, then propagated as integer bitsets.
    No sampling, search cap, or approximate scoring is used. Original course
    and section order breaks ties, matching a stable sort of itertools.product.
    """
    n = len(per_course_lists)
    if not n or any(not rows for rows in per_course_lists):
        return 0, []
    day_names = {meeting.day for rows in per_course_lists for row in rows
                 for meeting in row["all_meetings"]}
    day_bits = {day: 1 << i for i, day in enumerate(sorted(day_names))}
    masks, matches, starts, ends = [], [], [], []
    for rows in per_course_lists:
        masks.append([sum(day_bits[day] for day in {m.day for m in row["all_meetings"]}) for row in rows])
        matches.append([int(section_matches_faculty_pref(row, prefs)) for row in rows])
        starts.append([min((m.start_minutes for m in row["all_meetings"]), default=None) for row in rows])
        ends.append([max((m.end_minutes for m in row["all_meetings"]), default=0) for row in rows])
    compatible = [[[0] * n for _ in rows] for rows in per_course_lists]
    for i in range(n):
        for j in range(i + 1, n):
            for a, first in enumerate(per_course_lists[i]):
                for b, second in enumerate(per_course_lists[j]):
                    clash = exam_conflict(first["exam"], second["exam"]) or any(
                        meetings_conflict(m1, m2)
                        for m1 in first["all_meetings"] for m2 in second["all_meetings"]
                    )
                    if not clash:
                        compatible[i][a][j] |= 1 << b
                        compatible[j][b][i] |= 1 << a
    course_days = []
    for course_masks in masks:
        union = 0
        for mask in course_masks:
            union |= mask
        course_days.append(union)
    indices = [-1] * n
    best = []
    total_valid = 0
    limit = max(0, max_results)
    needs_gap = "gap" in sort_keys

    # Counting a proven noncompetitive branch does not require scoring each leaf.
    # Memo keys contain only constraints that affect validity, not ranking data.
    enforce_days = exact_days and target_days is not None

    @lru_cache(maxsize=16384)
    def count_subtree(remaining, active_domains, used_days):
        if enforce_days:
            if used_days.bit_count() > target_days:
                return 0
            possible = used_days
            for course in remaining:
                possible |= course_days[course]
            if possible.bit_count() < target_days:
                return 0
        if not remaining:
            return int(not enforce_days or used_days.bit_count() == target_days)
        position = min(range(len(remaining)), key=lambda p: (active_domains[p].bit_count(), remaining[p]))
        course = remaining[position]
        others = tuple(i for i in remaining if i != course)
        other_domains = tuple(domain for p, domain in enumerate(active_domains) if p != position)
        candidates = active_domains[position]
        count = 0
        while candidates:
            bit = candidates & -candidates
            candidates ^= bit
            section = bit.bit_length() - 1
            next_domains = tuple(domain & compatible[course][section][other]
                                 for other, domain in zip(others, other_domains))
            if all(next_domains):
                next_days = (used_days | masks[course][section]) if enforce_days else 0
                count += count_subtree(others, next_domains, next_days)
        return count

    @lru_cache(maxsize=4096)
    def domain_summary(course, domain):
        mandatory_days = None
        possible_days = 0
        best_faculty = 0
        candidates = domain
        while candidates:
            bit = candidates & -candidates
            candidates ^= bit
            section = bit.bit_length() - 1
            days = masks[course][section]
            mandatory_days = days if mandatory_days is None else mandatory_days & days
            possible_days |= days
            best_faculty = max(best_faculty, matches[course][section])
        return mandatory_days or 0, possible_days, best_faculty

    bounded_keys = set(sort_keys) <= {"none", "faculty", "days", "target_days"}

    def visit(remaining, domains, used_days, faculty_count, first_start, last_end):
        nonlocal total_valid
        if exact_days and target_days is not None:
            if used_days.bit_count() > target_days:
                return
            possible_days = used_days
            for course in remaining:
                possible_days |= course_days[course]
            if possible_days.bit_count() < target_days:
                return
        if remaining and limit and len(best) == limit and bounded_keys:
            mandatory_days = used_days
            possible_days = used_days
            possible_faculty = faculty_count
            for course in remaining:
                must, possible, faculty = domain_summary(course, domains[course])
                mandatory_days |= must
                possible_days |= possible
                possible_faculty += faculty
            minimum_days = mandatory_days.bit_count()
            maximum_days = possible_days.bit_count()
            minimum_diff = 0 if target_days is None or minimum_days <= target_days <= maximum_days else min(
                abs(minimum_days - target_days), abs(maximum_days - target_days))
            bounds = {"none": 0, "faculty": -possible_faculty,
                      "days": minimum_days, "target_days": minimum_diff}
            earliest_indices = tuple(indices[i] if indices[i] >= 0 else (domains[i] & -domains[i]).bit_length() - 1
                                     for i in range(n))
            inverse_bound = tuple(-bounds[key] for key in sort_keys) + tuple(-i for i in earliest_indices)
            if inverse_bound <= best[0][0]:
                total_valid += count_subtree(remaining, tuple(domains[i] for i in remaining), used_days if enforce_days else 0)
                return
        if not remaining:
            total_valid += 1
            if not limit:
                return
            values = {
                "none": 0, "faculty": -faculty_count,
                "days": used_days.bit_count(),
                "target_days": abs(used_days.bit_count() - target_days) if target_days is not None else 0,
                "earliest": first_start if first_start is not None else 0,
                "latest": -last_end,
            }
            if needs_gap:
                values["gap"] = gap_score(tuple(per_course_lists[i][idx] for i, idx in enumerate(indices)))
            # Python has a min-heap: negation keeps the worst retained result at its root.
            inverse_rank = tuple(-values[key] for key in sort_keys) + tuple(-idx for idx in indices)
            entry = (inverse_rank, tuple(indices))
            if len(best) < limit:
                heapq.heappush(best, entry)
            elif inverse_rank > best[0][0]:
                heapq.heapreplace(best, entry)
            return
        course = min(remaining, key=lambda i: (domains[i].bit_count(), i))
        next_remaining = tuple(i for i in remaining if i != course)
        candidates = domains[course]
        while candidates:
            bit = candidates & -candidates
            candidates ^= bit
            section = bit.bit_length() - 1
            next_days = used_days | masks[course][section]
            if exact_days and target_days is not None and next_days.bit_count() > target_days:
                continue
            next_domains = list(domains)
            for other in next_remaining:
                next_domains[other] &= compatible[course][section][other]
                if not next_domains[other]:
                    break
            else:
                indices[course] = section
                start = starts[course][section]
                next_start = first_start if start is None else start if first_start is None else min(first_start, start)
                visit(next_remaining, next_domains, next_days,
                      faculty_count + matches[course][section], next_start,
                      max(last_end, ends[course][section]))
                indices[course] = -1

    visit(tuple(range(n)), [(1 << len(rows)) - 1 for rows in per_course_lists], 0, 0, None, 0)
    retained = []
    for inverse_rank, section_indices in sorted(best, key=lambda entry: tuple(-v for v in entry[0])):
        combo = tuple(per_course_lists[i][idx] for i, idx in enumerate(section_indices))
        stats = {
            "gap": gap_score(combo), "days": days_used_score(combo),
            "faculty_matches": faculty_match_count(combo, prefs),
        }
        if target_days is not None:
            stats["target_days_diff"] = target_days_score(combo, target_days)
        retained.append((combo, stats, tuple(-v for v in inverse_rank[:len(sort_keys)])))
    return total_valid, retained


# --------------------------------------------------------------------------
# Weekly grid layout (Time/Day rows x Sun-Sat columns, like the live site)
# --------------------------------------------------------------------------

# BracU's standard fixed class-time slots. Any actual meeting time that
# doesn't match one of these (rare, but happens) is added as an extra row
# in the right chronological spot, so the grid never silently drops a class.
_CANONICAL_SLOT_STRINGS = [
    ("08:00 AM", "09:20 AM"),
    ("09:30 AM", "10:50 AM"),
    ("11:00 AM", "12:20 PM"),
    ("12:30 PM", "01:50 PM"),
    ("02:00 PM", "03:20 PM"),
    ("03:30 PM", "04:50 PM"),
    ("05:00 PM", "06:20 PM"),
    ("06:30 PM", "07:50 PM"),
    ("08:00 PM", "09:20 PM"),
]


def build_weekly_grid(combo):
    """Returns a list of (time_label, {day: [cell_text, ...]}) rows, in
    chronological order, ready to drop straight into a table -- one column
    per day of the week, one row per class-time slot, matching the
    Time/Day x Sunday..Saturday layout of the live site."""
    tagged = []
    for r in combo:
        for m in r["theory_meetings"]:
            tagged.append((m, r))
        for m in r["lab_meetings"]:
            tagged.append((m, r))

    label_for_key = {}
    for s_str, e_str in _CANONICAL_SLOT_STRINGS:
        label_for_key[(_12h_to_minutes(s_str), _12h_to_minutes(e_str))] = (s_str, e_str)
    for m, _ in tagged:
        key = (m.start_minutes, m.end_minutes)
        label_for_key.setdefault(key, (m.start_str, m.end_str))

    slot_keys = sorted(label_for_key.keys())

    rows = []
    for key in slot_keys:
        s_str, e_str = label_for_key[key]
        by_day = {}
        for m, r in tagged:
            if (m.start_minutes, m.end_minutes) == key:
                by_day.setdefault(m.day, []).append(
                    f"{r['course_code']}-{r['sectionName']}-{r['faculty']}-{m.room or '-'}"
                )
        rows.append((f"{s_str}-{e_str}", by_day))
    return rows


# --------------------------------------------------------------------------
# Building per-course section lists
# --------------------------------------------------------------------------

def build_course_sections(all_sections, course_code):
    code = course_code.strip().upper()
    matches = [s for s in all_sections if (s.get("courseCode") or "").strip().upper() == code]
    if not matches:
        return None

    rows = []
    for s in matches:
        theory = get_theory_meetings(s)
        lab = get_lab_meetings(s)
        cap = s.get("capacity")
        cons = s.get("consumedSeat")
        remaining = cap - cons if isinstance(cap, int) and isinstance(cons, int) else None
        rows.append(
            {
                "course_code": code,
                "sectionName": s.get("sectionName") or "?",
                "faculty": (s.get("faculties") or "TBA").strip() or "TBA",
                "theory_meetings": theory,
                "lab_meetings": lab,
                "all_meetings": theory + lab,
                "capacity": cap,
                "consumedSeat": cons,
                "remaining": remaining,
                "exam": get_exam_window(s),
            }
        )
    course_title = matches[0].get("courseName") or ""
    return course_title, rows


# --------------------------------------------------------------------------
# Output: CSV
# --------------------------------------------------------------------------

def write_csv(valid_combos, path, sort_by, target_days=None, mandatory_summary=None):
    header = [
        "Option #",
        "Gap Score (min)",
        "Days Used",
    ]
    if target_days is not None:
        header += ["Desired Days", "Days Diff"]
    header += [
        "Preferred Faculty Matches",
        "Course Code",
        "Section",
        "Mandatory Section?",
        "Faculty",
        "Preferred Faculty?",
        "Class Time",
        "Lab Time",
        "Seats Remaining",
        "Final Exam (reference only)",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for idx, (combo, stats) in enumerate(valid_combos, start=1):
            for r in combo:
                row = [idx, stats["gap"], stats["days"]]
                if target_days is not None:
                    row += [target_days, stats.get("target_days_diff", "")]
                row += [
                    stats["faculty_matches"],
                    r["course_code"],
                    r["sectionName"],
                    "Yes" if r.get("_mandatory_match") else "",
                    r["faculty"],
                    "Yes" if r.get("_pref_match") else "",
                    format_meetings(r["theory_meetings"]),
                    format_meetings(r["lab_meetings"]) if r["lab_meetings"] else "-",
                    r["remaining"] if r["remaining"] is not None else "",
                    r["exam"]["raw"],
                ]
                writer.writerow(row)


# --------------------------------------------------------------------------
# Output: PDF
# --------------------------------------------------------------------------

def write_pdf(valid_combos, total_valid, path, last_updated, sort_keys, target_days=None, mandatory_summary=None):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        print(
            "ERROR: PDF output needs the 'reportlab' package, which isn't installed.\n"
            "  Install it with:   pip install reportlab\n"
            "  ...or re-run with --format csv to skip PDF output.",
            file=sys.stderr,
        )
        sys.exit(1)

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    meta_style = ParagraphStyle("meta", parent=styles["Normal"], textColor=colors.grey, fontSize=9)
    option_style = ParagraphStyle(
        "option", parent=styles["Heading2"], textColor=colors.HexColor("#16324f"), spaceBefore=4, spaceAfter=2
    )
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], textColor=colors.grey, fontSize=9, spaceAfter=8)
    section_style = ParagraphStyle(
        "section", parent=styles["Heading3"], textColor=colors.HexColor("#2563eb"), spaceBefore=10, spaceAfter=4, fontSize=11
    )
    exam_note_style = ParagraphStyle("examnote", parent=styles["Normal"], textColor=colors.grey, fontSize=8, spaceAfter=4)
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10)
    header_style = ParagraphStyle("cellhdr", parent=cell_style, textColor=colors.white, fontName="Helvetica-Bold")
    grid_cell_style = ParagraphStyle("gridcell", parent=styles["Normal"], fontSize=6.7, leading=8.2)
    grid_header_style = ParagraphStyle(
        "gridhdr", parent=grid_cell_style, textColor=colors.white, fontName="Helvetica-Bold", fontSize=8, alignment=1
    )

    def P(text, style=cell_style):
        return Paragraph(str(text).replace("\n", "<br/>"), style)

    doc = SimpleDocTemplate(
        str(path), pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch, leftMargin=0.5 * inch, rightMargin=0.5 * inch
    )

    story = [
        Paragraph("Schedule Combinator -- Conflict-Free Course Adjustments", title_style),
        Spacer(1, 4),
        Paragraph(f"Live feed last updated: {last_updated}", meta_style),
        Paragraph(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", meta_style),
        Paragraph(
            f"{total_valid} conflict-free combination(s) found in total; showing {len(valid_combos)}, "
            f"sorted by: {', '.join(sort_keys)}.",
            meta_style,
        ),
    ]
    if mandatory_summary:
        story.append(
            Paragraph(
                f"Mandatory section constraints applied: <b>{mandatory_summary}</b>",
                meta_style,
            )
        )
    if target_days is not None:
        story.append(
            Paragraph(
                f"Desired class days per week: {target_days}. Each option below shows how many "
                "distinct days it actually uses and how far that is from what you asked for.",
                meta_style,
            )
        )
    story += [
        Paragraph(
            "Final exam times are used only to filter out clashing combinations -- they are NOT part "
            "of the weekly class table below, since exams aren't a weekly recurring event. Each option's "
            "exam info is listed separately underneath for your own records.",
            meta_style,
        ),
        Spacer(1, 14),
    ]

    grid_days = list(DAY_ORDER)  # SUNDAY..SATURDAY
    grid_header = [P("Time/Day", grid_header_style)] + [P(d.title(), grid_header_style) for d in grid_days]
    time_col_width = 1.0 * inch
    grid_col_widths = [time_col_width] + [(6.5 * inch) / len(grid_days)] * len(grid_days)

    detail_header = [P(h, header_style) for h in ["Course", "Section", "Faculty", "Seats Remaining", "Status"]]
    detail_col_widths = [0.8 * inch, 0.6 * inch, 2.3 * inch, 1.1 * inch, 0.9 * inch]

    exam_header = [P(h, header_style) for h in ["Course", "Section", "Final Exam (reference only, not in weekly grid)"]]
    exam_col_widths = [0.9 * inch, 0.7 * inch, 4.6 * inch]

    for idx, (combo, stats) in enumerate(valid_combos):
        story.append(Paragraph(f"Option {idx + 1} of {len(valid_combos)}", option_style))
        days_line = f"Days with class: {stats['days']}"
        if target_days is not None:
            days_line += f" (desired: {target_days}, diff: {stats.get('target_days_diff', '?')})"
        story.append(
            Paragraph(
                f"Gap score: {stats['gap']} idle min &nbsp;|&nbsp; "
                f"{days_line} &nbsp;|&nbsp; "
                f"Preferred-faculty matches: {stats['faculty_matches']}/{len(combo)}",
                sub_style,
            )
        )

        # Weekly class schedule as a Time/Day grid (Sunday..Saturday columns),
        # matching the layout of the live prepreg site's routine view.
        story.append(Paragraph("Weekly Class Schedule", section_style))
        grid_rows = build_weekly_grid(combo)
        has_any_class = any(by_day for _, by_day in grid_rows)
        if has_any_class:
            table_data = [grid_header]
            for time_label, by_day in grid_rows:
                row = [P(time_label, grid_cell_style)]
                for day in grid_days:
                    cell_entries = by_day.get(day, [])
                    row.append(P("\n".join(cell_entries), grid_cell_style) if cell_entries else P("", grid_cell_style))
                table_data.append(row)
            gt = Table(table_data, colWidths=grid_col_widths, repeatRows=1)
            gt.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324f")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.append(gt)
        else:
            story.append(Paragraph("No scheduled class times for this option (all sections are Unscheduled/TBA).", meta_style))

        # Section details
        story.append(Paragraph("Section Details", section_style))
        detail_data = [detail_header]
        for r in combo:
            seats = str(r["remaining"]) if r["remaining"] is not None else "N/A"
            tags = []
            if r.get("_mandatory_match"):
                tags.append("Mandatory")
            if r.get("_pref_match"):
                tags.append("\u2605 Pref")
            tag_str = ", ".join(tags) if tags else "-"
            detail_data.append([P(r["course_code"]), P(r["sectionName"]), P(r["faculty"]), P(seats), P(tag_str)])
        dt = Table(detail_data, colWidths=detail_col_widths, repeatRows=1)
        dt.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324f")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
            )
        story.append(dt)

        # Final exams -- reference only, deliberately separate from the weekly grid above.
        story.append(Paragraph("Final Exams (reference only)", section_style))
        exam_data = [exam_header]
        for r in combo:
            exam_data.append([P(r["course_code"]), P(r["sectionName"]), P(r["exam"]["raw"])])
        et = Table(exam_data, colWidths=exam_col_widths, repeatRows=1)
        et.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6b7280")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(et)
        story.append(Paragraph(
            "Exam text is read straight from the feed and only used to auto-exclude clashing combinations "
            "when it could be confidently parsed as a date + time range -- always double check it yourself.",
            exam_note_style,
        ))

        if idx != len(valid_combos) - 1:
            story.append(PageBreak())

    doc.build(story)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Fetch live BracU course data for several courses and generate every conflict-free "
            "combination of sections (no overlapping class time, no overlapping final exam time)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python schedule_combinator.py CSE370 CSE470 EEE201
  python schedule_combinator.py CSE370:01 CSE470:02 MAT215
  python schedule_combinator.py CSE370 CSE470 MAT215 --mandatory-sections CSE370:01 MAT215:02,03
  python schedule_combinator.py CSE370 CSE470 EEE201 MAT361 --only-open
  python schedule_combinator.py --from-file my_courses.txt --max-results 20
  python schedule_combinator.py CSE370 CSE470 --format csv
  python schedule_combinator.py CSE370 CSE470 --avoid-faculty XYZ --prefer-faculty AIB --sort-by faculty,gap
  python schedule_combinator.py CSE370 CSE470 EEE201 --target-days 3 --sort-by target_days,gap
  python schedule_combinator.py CSE370 CSE470 EEE201 --target-days 3 --exact-days

Prefer a GUI? Run:  python schedule_gui.py
""",
    )
    parser.add_argument("courses", nargs="*", help="Course codes to combine, e.g. CSE370 CSE470 EEE201 or CSE370:01")
    parser.add_argument("--from-file", metavar="PATH", help="Text file with one course code per line (combined with any codes given directly)")
    parser.add_argument("--only-open", action="store_true", help="Ignore sections with 0 seats remaining")
    parser.add_argument(
        "--mandatory-sections",
        "--mandatory-section",
        "--sections",
        nargs="+",
        metavar="SEC",
        help=(
            "Mandatory section(s) required for courses -- only combinations with these sections will be generated. "
            "Syntax: 'COURSE:SEC1,SEC2' (e.g. --mandatory-sections CSE370:01 MAT215:02,03) or bare '01' for all courses."
        ),
    )
    parser.add_argument(
        "--sort-by",
        default="gap",
        help=(
            "Comma-separated list of sort keys, applied in order (later keys break ties). "
            f"Choices: {', '.join(SORT_KEY_CHOICES)}. "
            "'gap' = most compact schedule (least idle time) first. "
            "'days' = fewest distinct class-days per week first. "
            "'target_days' = closest match to --target-days first. "
            "'faculty' = most matches against --prefer-faculty first. "
            "'earliest'/'latest' = earliest/latest class time first. "
            "Default: gap. Example: --sort-by target_days,gap"
        ),
    )
    parser.add_argument(
        "--prefer-faculty",
        nargs="+",
        metavar="NAME",
        help=(
            "Faculty initials/names you'd prefer, used for --sort-by faculty. "
            "A bare name applies across all courses (e.g. --prefer-faculty AIB DZK); "
            "prefix with 'COURSE:' to restrict it to one course "
            "(e.g. --prefer-faculty CSE370:AIB,TAZ CSE260:DZK)."
        ),
    )
    parser.add_argument(
        "--mandatory-preferred-faculty",
        action="store_true",
        help=(
            "Hard filter: require sections to be taught by one of the preferred faculty "
            "(for courses where preferred faculty are specified). Non-matching sections are dropped."
        ),
    )
    parser.add_argument(
        "--avoid-faculty",
        nargs="+",
        metavar="NAME",
        help=(
            "Faculty initials/names to exclude entirely -- any section taught by them is dropped "
            "before combinations are even generated (unlike --prefer-faculty, which only ranks). "
            "Same syntax: a bare name applies to all courses, or prefix with 'COURSE:' to restrict "
            "it (e.g. --avoid-faculty XYZ CSE260:DZK)."
        ),
    )
    parser.add_argument(
        "--skip-times",
        nargs="+",
        metavar="TIME",
        help=(
            "Class times or time slots to skip/avoid -- any section with classes during these times is dropped. "
            "Examples: --skip-times '08:00 AM-09:20 AM' '05:00 PM-06:20 PM' 'Sun 08:00 AM-09:20 AM'"
        ),
    )
    parser.add_argument(
        "--target-days",
        type=int,
        choices=range(1, 8),
        metavar="N",
        help=(
            "How many days a week you'd like to have classes (1-7). Combinations are scored by how "
            "close they come to this if you include 'target_days' in --sort-by (e.g. "
            "--sort-by target_days,gap). By itself this does not remove any combinations -- add "
            "--exact-days for that."
        ),
    )
    parser.add_argument(
        "--exact-days",
        action="store_true",
        help=(
            "Hard filter: only keep combinations that use EXACTLY --target-days distinct class-days "
            "(dropped before sorting/output, not just ranked). Requires --target-days."
        ),
    )
    parser.add_argument("--max-results", type=int, default=30, help="Max number of combinations to include in the output (default: 30)")
    parser.add_argument("--format", choices=["csv", "pdf", "both"], default="pdf", help="Output format (default: pdf)")
    parser.add_argument("-o", "--output-dir", default="output", help="Directory to write output files into (default: ./output)")
    parser.add_argument("--url", default=DEFAULT_FEED_URL, help="Override the data feed URL (advanced use)")
    return parser.parse_args(argv)


# --------------------------------------------------------------------------
# Core pipeline (shared by the CLI and the GUI)
# --------------------------------------------------------------------------

def run_combinator(
    courses,
    from_file=None,
    only_open=False,
    sort_by="gap",
    prefer_faculty=None,
    avoid_faculty=None,
    mandatory_preferred_faculty=False,
    mandatory_sections=None,
    skip_times=None,
    target_days=None,
    exact_days=False,
    max_results=30,
    output_format="pdf",
    output_dir="output",
    url=DEFAULT_FEED_URL,
    log=print,
):
    """Runs the full fetch -> combine -> filter -> sort -> write pipeline."""
    if exact_days and target_days is None:
        raise CombinatorError("--exact-days requires --target-days to also be set.")
    if target_days is not None and not (1 <= target_days <= 7):
        raise CombinatorError("--target-days must be between 1 and 7.")

    raw_input_codes = list(courses or [])
    if from_file:
        try:
            with open(from_file, "r", encoding="utf-8") as f:
                raw_input_codes += [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        except OSError as e:
            raise CombinatorError(f"couldn't read --from-file {from_file}: {e}")

    ordered_codes, inline_sections = extract_course_codes_and_sections(raw_input_codes)

    if len(ordered_codes) < 2:
        raise CombinatorError("give at least two course codes to combine (as arguments or via --from-file).")

    log(f"Fetching live schedule data from {url} ...")
    try:
        feed = fetch_feed(url)
    except RuntimeError as e:
        raise CombinatorError(str(e))

    last_updated = (feed.get("metadata") or {}).get("lastUpdated", "Unknown")
    all_sections = feed.get("courses") or []
    log(f"  Feed last updated: {last_updated}")

    prefer_prefs = parse_faculty_preferences(prefer_faculty)
    avoid_prefs = parse_faculty_preferences(avoid_faculty)
    skip_rules = parse_skip_times(skip_times)
    mandatory_sec_prefs = parse_mandatory_sections(mandatory_sections)

    # Merge any inline course:sec (e.g. 'CSE370:01') into mandatory_sec_prefs
    for c_code, s_set in inline_sections.items():
        mandatory_sec_prefs["per_course"].setdefault(c_code, set()).update(s_set)

    # Build human-readable summary of mandatory sections for reports
    mand_parts = []
    if mandatory_sec_prefs["global"]:
        mand_parts.append(f"Global: {', '.join(sorted(mandatory_sec_prefs['global']))}")
    for c_code, s_set in sorted(mandatory_sec_prefs["per_course"].items()):
        mand_parts.append(f"{c_code}: {', '.join(sorted(s_set))}")
    mandatory_summary = "; ".join(mand_parts) if mand_parts else None
    if mandatory_summary:
        log(f"  Mandatory section constraints: {mandatory_summary}")

    if mandatory_preferred_faculty and not prefer_prefs["global"] and not prefer_prefs["per_course"]:
        log("  ! Mandatory preferred faculty is enabled, but no preferred faculty was specified.")

    per_course_lists = []
    for code in ordered_codes:
        result = build_course_sections(all_sections, code)
        if result is None:
            hint = suggest_similar(all_sections, code)
            msg = f"no sections found for '{code}'."
            if hint:
                msg += f" Codes in the feed starting the same way: {', '.join(hint)}"
            raise CombinatorError(msg)
        title, rows = result

        # 1. Mandatory section filtering (hard filter)
        course_target_secs = set(mandatory_sec_prefs["global"]) | mandatory_sec_prefs["per_course"].get(code.upper(), set())
        if course_target_secs:
            matched_rows, dropped_non_mand = filter_mandatory_sections(rows, course_target_secs, code)
            if not matched_rows:
                avail_secs = ", ".join(r["sectionName"] for r in rows)
                raise CombinatorError(
                    f"'{code.upper()}' has no section matching mandatory section(s) "
                    f"({', '.join(sorted(course_target_secs))}). Available sections in feed: {avail_secs}"
                )
            rows = matched_rows
            for r in rows:
                r["_mandatory_match"] = True
            matched_desc = ", ".join(sorted(set(r["sectionName"] for r in rows)))
            log(f"  - {code.upper()}: filtered to mandatory section(s) {matched_desc} ({len(rows)} candidate section(s))")

        # 2. Avoid faculty filter
        rows, dropped = filter_out_avoided_faculty(rows, avoid_prefs)
        if dropped:
            dropped_desc = ", ".join(f"Sec {r['sectionName']} ({r['faculty']})" for r in dropped)
            log(f"  - {code.upper()}: excluded {len(dropped)} section(s) taught by avoided faculty: {dropped_desc}")
        if not rows:
            raise CombinatorError(
                f"'{code}' has no sections left after applying --avoid-faculty -- every candidate section is "
                "taught by someone you're avoiding."
            )

        # 3. Mandatory preferred faculty filter
        if mandatory_preferred_faculty:
            names_set = set(prefer_prefs["global"]) | prefer_prefs["per_course"].get(code.upper(), set())
            if names_set:
                rows, dropped_pref = filter_non_preferred_faculty(rows, prefer_prefs, code)
                if dropped_pref:
                    dropped_desc = ", ".join(f"Sec {r['sectionName']} ({r['faculty']})" for r in dropped_pref)
                    log(f"  - {code.upper()}: excluded {len(dropped_pref)} section(s) not matching mandatory preferred faculty: {dropped_desc}")
                if not rows:
                    raise CombinatorError(
                        f"'{code}' has no sections left after applying Mandatory Preferred Faculty -- no candidate section "
                        f"is taught by your preferred faculty ({', '.join(sorted(names_set))})."
                    )
            else:
                log(f"  ! {code.upper()}: no preferred faculty specified -- keeping all candidate sections.")

        # 4. Skip class times filter
        rows, dropped_time = filter_out_skipped_times(rows, skip_rules)
        if dropped_time:
            dropped_desc = ", ".join(f"Sec {r['sectionName']} ({m.day.title()} {m.start_str}-{m.end_str})" for r, m in dropped_time)
            log(f"  - {code.upper()}: excluded {len(dropped_time)} section(s) overlapping skipped class times: {dropped_desc}")
        if not rows:
            raise CombinatorError(
                f"'{code}' has no sections left after applying --skip-times -- every candidate section has classes "
                "during the times you chose to skip."
            )

        # 5. Open seats filter
        if only_open:
            open_rows = [r for r in rows if r["remaining"] is None or r["remaining"] > 0]
            if not open_rows:
                if course_target_secs:
                    log(f"  ! '{code}' mandatory section(s) currently have 0 open seats -- keeping anyway so schedule combinations can still be generated.")
                else:
                    log(f"  ! '{code}' has no sections with open seats -- keeping all its sections instead so combinations can still be generated.")
            else:
                rows = open_rows

        if not course_target_secs:
            log(f"  - {code.upper()}: {len(rows)} candidate section(s)")
        per_course_lists.append(rows)

    total_raw = 1
    for rows in per_course_lists:
        total_raw *= len(rows)
    log(f"Checking {total_raw} raw section combination(s) for clashes...")
    prefs = parse_faculty_preferences(prefer_faculty)
    _, sort_keys = build_sort_key_fn(sort_by, prefs, target_days=target_days, on_warning=log)
    total_valid, valid = search_combinations(
        per_course_lists, sort_keys, prefs, target_days=target_days,
        exact_days=exact_days, max_results=max_results,
    )
    for combo, _, _ in valid:
        for row in combo:
            row["_pref_match"] = section_matches_faculty_pref(row, prefs)
    log(f"Found {total_valid} conflict-free combination(s).")

    if total_valid == 0:
        extra = f" (none matched --exact-days {target_days})" if exact_days else ""
        mand_extra = f" (enforcing mandatory section(s): {mandatory_summary})" if mandatory_summary else ""
        log(
            "No combination of the given sections avoids every class-time and exam clash"
            f"{extra}{mand_extra}. Try checking whether your mandatory sections clash with each other "
            "or with other courses, relax --exact-days, or toggle --only-open."
        )
        return {
            "total_valid": 0,
            "written_count": 0,
            "sort_keys": sort_keys,
            "last_updated": last_updated,
            "output_paths": [],
        }

    if sort_keys != ["none"]:
        valid.sort(key=lambda item: item[2])

    limited = [(combo, stats) for combo, stats, _ in valid[:max_results]]
    if total_valid > len(limited):
        log(f"Writing the top {len(limited)} (sorted by {', '.join(sort_keys)}); {total_valid - len(limited)} more exist -- raise max results to see them.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = "_".join(ordered_codes)[:80] or "combo"

    output_paths = []
    if output_format in ("csv", "both"):
        csv_path = out_dir / f"{slug}_combinations.csv"
        write_csv(limited, csv_path, ", ".join(sort_keys), target_days=target_days, mandatory_summary=mandatory_summary)
        log(f"CSV written: {csv_path}")
        output_paths.append(csv_path)

    if output_format in ("pdf", "both"):
        pdf_path = out_dir / f"{slug}_combinations.pdf"
        write_pdf(limited, total_valid, pdf_path, last_updated, sort_keys, target_days=target_days, mandatory_summary=mandatory_summary)
        log(f"PDF written: {pdf_path}")
        output_paths.append(pdf_path)

    return {
        "total_valid": total_valid,
        "written_count": len(limited),
        "sort_keys": sort_keys,
        "last_updated": last_updated,
        "output_paths": output_paths,
    }


def main(argv=None):
    args = parse_args(argv)
    try:
        run_combinator(
            courses=args.courses,
            from_file=args.from_file,
            only_open=args.only_open,
            sort_by=args.sort_by,
            prefer_faculty=args.prefer_faculty,
            avoid_faculty=args.avoid_faculty,
            mandatory_preferred_faculty=args.mandatory_preferred_faculty,
            mandatory_sections=args.mandatory_sections,
            skip_times=args.skip_times,
            target_days=args.target_days,
            exact_days=args.exact_days,
            max_results=args.max_results,
            output_format=args.format,
            output_dir=args.output_dir,
            url=args.url,
            log=print,
        )
    except CombinatorError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
