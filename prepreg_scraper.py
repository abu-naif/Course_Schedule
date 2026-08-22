#!/usr/bin/env python3
"""
PrePreReg Course Section Organizer
-----------------------------------

Pulls live BracU course-offering data (the same public JSON feed that powers
https://preprereg.vercel.app/) and, for one or more course codes you give it,
organizes every section into a clean CSV and/or PDF.

Sections are grouped by their *class* day-pattern (e.g. Sun+Tue, Mon+Wed, or
any other combination) -- lab days are ignored for grouping purposes, though
lab timing is still shown for reference. Inside each group, sections are
sorted earliest class time first.

Data source
-----------
The live site (prepreg.vercel.app / the prepre_reg repo) doesn't scrape HTML
at all -- it reads a public JSON feed maintained by the same author:

    https://usis-cdn.eniamza.com/connect-migrate.json

That feed is refreshed periodically from BRACU's USIS and is exactly what
this script reads too, which is faster and far more reliable than parsing
rendered HTML would be.

Usage
-----
    python prepreg_scraper.py CSE370 CSE470
    python prepreg_scraper.py CSE370 --format csv
    python prepreg_scraper.py CSE370 CSE470 EEE201 --format pdf -o my_output
    python prepreg_scraper.py --from-file courses.txt

Run `python prepreg_scraper.py --help` for all options.

Dependencies
------------
- Standard library only for CSV output.
- `reportlab` is required only if you want PDF output (pip install reportlab).
"""

import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.request
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

DEFAULT_FEED_URL = "https://usis-cdn.eniamza.com/connect-migrate.json"

DAY_ORDER = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
DAY_INDEX = {day: i for i, day in enumerate(DAY_ORDER)}
DAY_ABBR = {day: day[:3].capitalize() for day in DAY_ORDER}

# Fallback parser for the pre-formatted "preRegSchedule" / "preRegLabSchedule"
# strings, used only when the structured schedule fields aren't present, e.g.:
#   "Sunday(09:30 AM-10:50 AM-07F-22C)"
SCHEDULE_STR_RE = re.compile(
    r"(?P<day>Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)"
    r"\("
    r"(?P<start>\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(?P<end>\d{1,2}:\d{2}\s*[AP]M)"
    r"(?:-(?P<room>[^)]*))?"
    r"\)",
    re.IGNORECASE,
)


class Meeting:
    """One weekly meeting block: a single day + start/end time (+ room)."""

    __slots__ = ("day", "start_minutes", "end_minutes", "start_str", "end_str", "room")

    def __init__(self, day, start_minutes, end_minutes, start_str, end_str, room=None):
        self.day = day  # e.g. "SUNDAY"
        self.start_minutes = start_minutes
        self.end_minutes = end_minutes
        self.start_str = start_str  # friendly "09:30 AM"
        self.end_str = end_str
        self.room = room

    def __repr__(self):
        return f"{self.day.title()} {self.start_str}-{self.end_str}"


# --------------------------------------------------------------------------
# Time helpers
# --------------------------------------------------------------------------

def _12h_to_minutes(time_str):
    """'09:30 AM' -> minutes since midnight."""
    dt = datetime.strptime(time_str.strip().upper(), "%I:%M %p")
    return dt.hour * 60 + dt.minute


def _24h_to_minutes_and_display(time_str):
    """'13:50:00' -> (830, '01:50 PM')"""
    hour, minute = int(time_str.split(":")[0]), int(time_str.split(":")[1])
    display = datetime(2000, 1, 1, hour, minute).strftime("%I:%M %p")
    return hour * 60 + minute, display


# --------------------------------------------------------------------------
# Schedule extraction (structured fields first, string fields as fallback)
# --------------------------------------------------------------------------

def extract_meetings_from_structured(schedule_list, room):
    """schedule_list: [{"day": "MONDAY", "startTime": "12:30:00", "endTime": "13:50:00"}, ...]"""
    meetings = []
    for item in schedule_list or []:
        day = (item.get("day") or "").upper()
        if day not in DAY_INDEX or not item.get("startTime") or not item.get("endTime"):
            continue
        start_min, start_disp = _24h_to_minutes_and_display(item["startTime"])
        end_min, end_disp = _24h_to_minutes_and_display(item["endTime"])
        meetings.append(Meeting(day, start_min, end_min, start_disp, end_disp, room))
    return meetings


def extract_meetings_from_string(schedule_str):
    """Fallback for the preformatted 'Day(start-end-room)' style strings."""
    meetings = []
    if not schedule_str:
        return meetings
    for m in SCHEDULE_STR_RE.finditer(schedule_str):
        day = m.group("day").upper()
        start_str = m.group("start").strip().upper()
        end_str = m.group("end").strip().upper()
        meetings.append(
            Meeting(
                day,
                _12h_to_minutes(start_str),
                _12h_to_minutes(end_str),
                start_str,
                end_str,
                (m.group("room") or "").strip() or None,
            )
        )
    return meetings


def get_theory_meetings(section):
    """The main class schedule -- this is what grouping/sorting is based on."""
    sched = section.get("sectionSchedule") or {}
    structured = sched.get("classSchedules")
    if structured:
        return extract_meetings_from_structured(structured, section.get("roomName"))
    return extract_meetings_from_string(section.get("preRegSchedule"))


def get_lab_meetings(section):
    """Lab schedule -- shown for reference only, never used for grouping."""
    structured = section.get("labSchedules")
    if structured:
        return extract_meetings_from_structured(structured, section.get("labRoomName"))
    return extract_meetings_from_string(section.get("preRegLabSchedule"))


def format_meetings(meetings):
    """Turn a list of Meetings into one readable string, e.g.
    'Sun/Tue 09:30 AM-10:50 AM (07F-22C)'. Days sharing an identical time
    range are merged onto one line; mixed patterns get multiple lines."""
    if not meetings:
        return "TBA"
    buckets = OrderedDict()
    for m in sorted(meetings, key=lambda x: DAY_INDEX[x.day]):
        key = (m.start_minutes, m.end_minutes, m.room)
        if key not in buckets:
            buckets[key] = {"days": [], "start_str": m.start_str, "end_str": m.end_str, "room": m.room}
        buckets[key]["days"].append(m.day)

    lines = []
    for b in buckets.values():
        days_str = "/".join(DAY_ABBR[d] for d in b["days"])
        room_str = f" ({b['room']})" if b["room"] else ""
        lines.append(f"{days_str} {b['start_str']}-{b['end_str']}{room_str}")
    return "; ".join(lines)


def group_key_for_section(theory_meetings):
    """Tuple of unique weekday indices, e.g. (0, 2) for Sun+Tue. None means
    'no class schedule available' -- these get bucketed at the end."""
    if not theory_meetings:
        return None
    return tuple(sorted({DAY_INDEX[m.day] for m in theory_meetings}))


def earliest_start(meetings):
    if not meetings:
        return float("inf")
    return min(m.start_minutes for m in meetings)


def group_label(group_key):
    if group_key is None:
        return "Unscheduled / TBA"
    return " & ".join(DAY_ABBR[DAY_ORDER[i]] for i in group_key)


# --------------------------------------------------------------------------
# Feed fetching
# --------------------------------------------------------------------------

def fetch_feed(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "prepreg-scraper/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Server returned HTTP {e.code} for {url}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Couldn't reach {url} ({e.reason}). Check your internet connection."
        ) from e

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError("The feed did not return valid JSON.") from e


# --------------------------------------------------------------------------
# Core processing
# --------------------------------------------------------------------------

def build_course_report(all_sections, course_code):
    """Returns (course_title, [(group_label, [row, ...]), ...]) or None if
    the course code has no sections in the feed."""
    code = course_code.strip().upper()
    matches = [s for s in all_sections if (s.get("courseCode") or "").strip().upper() == code]
    if not matches:
        return None

    rows = []
    for s in matches:
        theory = get_theory_meetings(s)
        lab = get_lab_meetings(s)
        capacity = s.get("capacity")
        consumed = s.get("consumedSeat")
        rows.append(
            {
                "sectionName": s.get("sectionName") or "?",
                "faculty": (s.get("faculties") or "TBA").strip() or "TBA",
                "theory_meetings": theory,
                "lab_meetings": lab,
                "capacity": capacity,
                "consumedSeat": consumed,
                "examDetail": (s.get("sectionSchedule") or {}).get("finalExamDetail") or "N/A",
                "group_key": group_key_for_section(theory),
                "sort_key": earliest_start(theory),
            }
        )

    groups = OrderedDict()
    for r in sorted(rows, key=lambda r: (r["group_key"] is None, r["group_key"] or ())):
        groups.setdefault(r["group_key"], []).append(r)

    result = []
    for gk, section_rows in groups.items():
        section_rows.sort(key=lambda r: (r["sort_key"], str(r["sectionName"])))
        result.append((group_label(gk), section_rows))

    course_title = matches[0].get("courseName") or ""
    return course_title, result


def suggest_similar(all_sections, course_code):
    """A small 'did you mean' helper for typo'd course codes."""
    prefix = re.match(r"[A-Za-z]+", course_code.strip())
    if not prefix:
        return []
    prefix = prefix.group(0).upper()
    codes = sorted({(s.get("courseCode") or "").upper() for s in all_sections if (s.get("courseCode") or "").upper().startswith(prefix)})
    return codes[:8]


# --------------------------------------------------------------------------
# Output: CSV
# --------------------------------------------------------------------------

def write_csv(reports, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Course Code",
                "Course Title",
                "Day Group",
                "Section",
                "Faculty",
                "Class Time",
                "Lab Time",
                "Room",
                "Seats Booked",
                "Seats Total",
                "Seats Remaining",
                "Final Exam",
            ]
        )
        for code, title, groups in reports:
            for label, section_rows in groups:
                for r in section_rows:
                    room = next((m.room for m in r["theory_meetings"] if m.room), "")
                    cap, cons = r["capacity"], r["consumedSeat"]
                    remaining = cap - cons if isinstance(cap, int) and isinstance(cons, int) else ""
                    writer.writerow(
                        [
                            code,
                            title,
                            label,
                            r["sectionName"],
                            r["faculty"],
                            format_meetings(r["theory_meetings"]),
                            format_meetings(r["lab_meetings"]) if r["lab_meetings"] else "-",
                            room,
                            cons if cons is not None else "",
                            cap if cap is not None else "",
                            remaining,
                            r["examDetail"],
                        ]
                    )


# --------------------------------------------------------------------------
# Output: PDF
# --------------------------------------------------------------------------

def write_pdf(reports, path, last_updated):
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
    course_style = ParagraphStyle(
        "course", parent=styles["Heading2"], textColor=colors.HexColor("#16324f"), spaceBefore=16, spaceAfter=4
    )
    group_style = ParagraphStyle(
        "group", parent=styles["Heading3"], textColor=colors.HexColor("#2563eb"), spaceBefore=10, spaceAfter=4, fontSize=11
    )
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10)
    header_style = ParagraphStyle("cellhdr", parent=cell_style, textColor=colors.white, fontName="Helvetica-Bold")

    def P(text, style=cell_style):
        return Paragraph(str(text).replace("\n", "<br/>"), style)

    doc = SimpleDocTemplate(
        str(path), pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch, leftMargin=0.5 * inch, rightMargin=0.5 * inch
    )

    story = [
        Paragraph("PrePreReg -- Organized Course Sections", title_style),
        Spacer(1, 4),
        Paragraph(f"Live feed last updated: {last_updated}", meta_style),
        Paragraph(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", meta_style),
        Paragraph(
            "Sections are grouped by class day-pattern (lab days are ignored for grouping) "
            "and sorted earliest class time first within each group.",
            meta_style,
        ),
        Spacer(1, 14),
    ]

    col_widths = [0.55 * inch, 0.85 * inch, 1.55 * inch, 1.55 * inch, 0.75 * inch, 1.55 * inch]
    header_row = [P(h, header_style) for h in ["Sec", "Faculty", "Class Time", "Lab Time", "Seats", "Final Exam"]]

    for idx, (code, title, groups) in enumerate(reports):
        heading = f"{code}" + (f" -- {title}" if title else "")
        story.append(Paragraph(heading, course_style))
        for label, section_rows in groups:
            story.append(Paragraph(label, group_style))
            table_data = [header_row]
            for r in section_rows:
                cap, cons = r["capacity"], r["consumedSeat"]
                seats = f"{cons}/{cap}" if cap is not None and cons is not None else "N/A"
                table_data.append(
                    [
                        P(r["sectionName"]),
                        P(r["faculty"]),
                        P(format_meetings(r["theory_meetings"])),
                        P(format_meetings(r["lab_meetings"]) if r["lab_meetings"] else "-"),
                        P(seats),
                        P(r["examDetail"]),
                    ]
                )
            t = Table(table_data, colWidths=col_widths, repeatRows=1)
            t.setStyle(
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
            story.append(t)
        if idx != len(reports) - 1:
            story.append(PageBreak())

    doc.build(story)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Fetch live BracU course data and organize selected courses' sections by day-pattern and time.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python prepreg_scraper.py CSE370
  python prepreg_scraper.py CSE370 CSE470 --format csv
  python prepreg_scraper.py CSE370 -o exports --format pdf
  python prepreg_scraper.py --from-file my_courses.txt
""",
    )
    parser.add_argument("courses", nargs="*", help="Course codes to organize, e.g. CSE370 CSE470")
    parser.add_argument("--from-file", metavar="PATH", help="Text file with one course code per line (combined with any codes given directly)")
    parser.add_argument("--format", choices=["csv", "pdf", "both"], default="both", help="Output format (default: both)")
    parser.add_argument("-o", "--output-dir", default="output", help="Directory to write output files into (default: ./output)")
    parser.add_argument("--url", default=DEFAULT_FEED_URL, help="Override the data feed URL (advanced use)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    codes = list(args.courses)
    if args.from_file:
        try:
            with open(args.from_file, "r", encoding="utf-8") as f:
                codes += [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        except OSError as e:
            print(f"ERROR: couldn't read --from-file {args.from_file}: {e}", file=sys.stderr)
            sys.exit(1)

    # de-dupe, case-insensitive, preserve order
    seen = set()
    ordered_codes = []
    for c in codes:
        key = c.strip().upper()
        if key and key not in seen:
            seen.add(key)
            ordered_codes.append(c.strip())

    if not ordered_codes:
        print("ERROR: no course codes given. Pass them as arguments or via --from-file.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching live schedule data from {args.url} ...")
    try:
        feed = fetch_feed(args.url)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    last_updated = (feed.get("metadata") or {}).get("lastUpdated", "Unknown")
    all_sections = feed.get("courses") or []
    print(f"  Feed last updated: {last_updated}")
    print(f"  Total sections in feed: {len(all_sections)}")

    reports = []
    for code in ordered_codes:
        result = build_course_report(all_sections, code)
        if result is None:
            hint = suggest_similar(all_sections, code)
            msg = f"  ! No sections found for '{code}'."
            if hint:
                msg += f" Codes in the feed starting the same way: {', '.join(hint)}"
            print(msg)
            continue
        title, groups = result
        total_sections = sum(len(rows) for _, rows in groups)
        print(f"  - {code.upper()}: {total_sections} section(s) found across {len(groups)} day-group(s)")
        reports.append((code.upper(), title, groups))

    if not reports:
        print("Nothing to write -- none of the given course codes matched. Exiting.", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = "_".join(code for code, _, _ in reports)[:80] or "courses"

    if args.format in ("csv", "both"):
        csv_path = output_dir / f"{slug}_sections.csv"
        write_csv(reports, csv_path)
        print(f"CSV written: {csv_path}")

    if args.format in ("pdf", "both"):
        pdf_path = output_dir / f"{slug}_sections.pdf"
        write_pdf(reports, pdf_path, last_updated)
        print(f"PDF written: {pdf_path}")


if __name__ == "__main__":
    main()
