#!/usr/bin/env python3
"""
Course Combinator Web Application
---------------------------------
FastAPI backend powering the web interface for Course Combinator.
Provides REST API endpoints for course search, real-time schedule combination,
timetable grid formatting, and PDF/CSV export.
"""

import io
import os
import re
import tempfile
import time
from datetime import datetime
from collections import OrderedDict
from threading import Lock
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import prepreg_scraper as ps
import schedule_combinator as sc

# Initialize FastAPI App
app = FastAPI(
    title="BracU Course Combinator Web",
    description="Intelligent schedule planner and conflict-free combination generator for BRAC University students.",
    version="2.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# --------------------------------------------------------------------------
# Feed Cache
# --------------------------------------------------------------------------
class FeedCache:
    def __init__(self, ttl_seconds: int = 600):
        self.ttl = ttl_seconds
        self.last_fetched: float = 0
        self.feed_data: Optional[Dict[str, Any]] = None
        self.courses_summary: List[Dict[str, Any]] = []
        self.faculties: List[str] = []
        self.time_slots: List[Dict[str, Any]] = []

    def get_feed(self, force_refresh: bool = False) -> Dict[str, Any]:
        now = time.time()
        if self.feed_data is None or force_refresh or (now - self.last_fetched > self.ttl):
            try:
                data = ps.fetch_feed(ps.DEFAULT_FEED_URL)
                self.feed_data = data
                self.last_fetched = now
                self._reindex()
            except Exception as e:
                if self.feed_data is not None:
                    # Fallback to existing cache if network fails
                    return self.feed_data
                raise HTTPException(status_code=502, detail=f"Failed to fetch live course feed: {e}")
        return self.feed_data

    def _reindex(self):
        if not self.feed_data:
            return
        courses_raw = self.feed_data.get("courses", [])
        by_code: Dict[str, Dict[str, Any]] = {}
        faculties_set = set()
        time_slots_map = {}

        for s in courses_raw:
            code = (s.get("courseCode") or "").strip().upper()
            if not code:
                continue
            title = (s.get("courseName") or "").strip()
            fac = (s.get("faculties") or "").strip()
            sec_name = str(s.get("sectionName") or "").strip()

            clean_facs = []
            if fac:
                for f in re.split(r"[,/ ]+", fac):
                    f_clean = f.strip().upper()
                    if f_clean and len(f_clean) >= 2 and f_clean not in ("TBA", "NONE", "N/A", "TBD"):
                        faculties_set.add(f_clean)
                        clean_facs.append(f_clean)

            if code not in by_code:
                by_code[code] = {
                    "code": code,
                    "title": title,
                    "sections_count": 0,
                    "faculties": set(),
                    "faculty_sections": {},
                }
            by_code[code]["sections_count"] += 1
            for f_clean in clean_facs:
                by_code[code]["faculties"].add(f_clean)
                by_code[code]["faculty_sections"].setdefault(f_clean, []).append(sec_name)

            # Collect time slots
            for m in ps.get_theory_meetings(s):
                key = (m.start_minutes, m.end_minutes, m.start_str, m.end_str)
                if key not in time_slots_map:
                    time_slots_map[key] = {"type": "Theory", "count": 0}
                time_slots_map[key]["count"] += 1

            for m in ps.get_lab_meetings(s):
                key = (m.start_minutes, m.end_minutes, m.start_str, m.end_str)
                if key not in time_slots_map:
                    time_slots_map[key] = {"type": "Lab", "count": 0}
                time_slots_map[key]["count"] += 1

        summary = []
        for code, info in sorted(by_code.items()):
            fac_sec_map = {
                f: sorted(list(set(secs))) for f, secs in info["faculty_sections"].items()
            }
            summary.append({
                "code": code,
                "title": info["title"],
                "sections_count": info["sections_count"],
                "faculties": sorted(info["faculties"]),
                "faculty_sections": fac_sec_map,
            })
        self.courses_summary = summary
        self.faculties = sorted(faculties_set)

        sorted_slots = []
        for (s_min, e_min, s_str, e_str), meta in sorted(time_slots_map.items(), key=lambda x: (x[0][0], x[0][1])):
            sorted_slots.append({
                "label": f"{s_str} - {e_str}",
                "start_str": s_str,
                "end_str": e_str,
                "start_minutes": s_min,
                "end_minutes": e_min,
                "type": meta["type"],
                "count": meta["count"],
            })
        self.time_slots = sorted_slots


cache = FeedCache()

class ExactAnalysisCache:
    """Reuse only identical requests against the same live feed object."""
    def __init__(self, capacity=16):
        self.capacity = capacity
        self.feed = None
        self.results = OrderedDict()
        self.lock = Lock()

    def get(self, feed, key):
        with self.lock:
            if self.feed is not feed:
                self.feed = feed
                self.results.clear()
            result = self.results.get(key)
            if result is not None:
                self.results.move_to_end(key)
            return result

    def put(self, feed, key, result):
        with self.lock:
            # An older in-flight search must not replace a refreshed feed's cache.
            if self.feed is not feed:
                return
            self.results[key] = result
            self.results.move_to_end(key)
            while len(self.results) > self.capacity:
                self.results.popitem(last=False)


analysis_cache = ExactAnalysisCache()

# --------------------------------------------------------------------------
# Request / Response Models
# --------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    courses: List[str] = Field(..., description="List of course codes, e.g. ['CSE110', 'MAT110']")
    only_open: bool = False
    target_days: Optional[int] = Field(default=None, ge=1, le=7)
    exact_days: bool = False
    prefer_faculty: Optional[List[str]] = None
    avoid_faculty: Optional[List[str]] = None
    mandatory_preferred_faculty: bool = False
    mandatory_sections: Optional[List[str]] = None
    skip_times: Optional[List[str]] = None
    sort_by: str = "faculty"
    secondary_sort_by: Optional[str] = "days"
    max_results: int = Field(default=30, ge=1, le=100)


# --------------------------------------------------------------------------
# Helpers: Serialize Combinator Objects
# --------------------------------------------------------------------------
def serialize_meeting(m: ps.Meeting) -> Dict[str, Any]:
    return {
        "day": m.day,
        "day_abbr": m.day[:3].capitalize(),
        "start_minutes": m.start_minutes,
        "end_minutes": m.end_minutes,
        "start_str": m.start_str,
        "end_str": m.end_str,
        "room": m.room or "TBA",
    }


def serialize_exam(exam: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not exam:
        return {"raw": "N/A", "parsed": False, "date": None, "start_str": None, "end_str": None}
    return {
        "raw": exam.get("raw", "N/A"),
        "parsed": exam.get("parsed", False),
        "date": str(exam.get("date")) if exam.get("date") else None,
        "start_minutes": exam.get("start"),
        "end_minutes": exam.get("end"),
    }


def serialize_section_row(r: Dict[str, Any]) -> Dict[str, Any]:
    code = r.get("course_code") or r.get("courseCode") or ""
    all_meetings = r.get("all_meetings", [])
    
    # Extract unique room numbers from meetings
    rooms = []
    for m in all_meetings:
        room_val = getattr(m, "room", None)
        if room_val and str(room_val).strip() and str(room_val).strip() != "-":
            rooms.append(str(room_val).strip())
    room_str = ", ".join(dict.fromkeys(rooms)) if rooms else "TBA"

    cap = r.get("capacity")
    cons = r.get("consumedSeat")
    rem = r.get("remaining")
    if rem is None and isinstance(cap, int) and isinstance(cons, int):
        rem = cap - cons

    return {
        "courseCode": code,
        "course_code": code,
        "sectionName": r.get("sectionName") or "?",
        "faculty": (r.get("faculty") or "TBA").strip() or "TBA",
        "capacity": cap,
        "consumedSeat": cons,
        "remaining": rem,
        "room": room_str,
        "theory_meetings": [serialize_meeting(m) for m in r.get("theory_meetings", [])],
        "lab_meetings": [serialize_meeting(m) for m in r.get("lab_meetings", [])],
        "all_meetings": [serialize_meeting(m) for m in all_meetings],
        "exam": serialize_exam(r.get("exam")),
        "is_pref_match": bool(r.get("_pref_match", False)),
        "is_mandatory": bool(r.get("_mandatory_match", False)),
    }


def build_json_weekly_grid(combo: tuple) -> List[Dict[str, Any]]:
    """Builds a structured grid array matching the exact routine table of the PDF."""
    grid_rows = sc.build_weekly_grid(combo)
    result = []
    for time_label, day_map in grid_rows:
        day_dict = {}
        for day in sc.DAY_ORDER:
            cell_items = []
            for item in day_map.get(day, []):
                if isinstance(item, str):
                    parts = item.split("-")
                    course = parts[0] if len(parts) > 0 else ""
                    section = parts[1] if len(parts) > 1 else ""
                    faculty = parts[2] if len(parts) > 2 else "TBA"
                    room = "-".join(parts[3:]) if len(parts) > 3 else "TBA"
                    cell_items.append({
                        "course": course,
                        "section": section,
                        "faculty": faculty,
                        "room": room,
                        "type": "Lab" if (course.endswith("L") or "LAB" in course.upper()) else "Theory",
                    })
                elif isinstance(item, dict):
                    cell_items.append(item)
            day_dict[day] = cell_items
        result.append({
            "time_label": time_label,
            "days": day_dict,
        })
    return result


def extract_active_days(combo: tuple) -> List[str]:
    days_set = set()
    for r in combo:
        for m in r["all_meetings"]:
            days_set.add(m.day)
    return [d.capitalize() for d in sc.DAY_ORDER if d in days_set]


# --------------------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------------------
@app.get("/", response_class=FileResponse)
def get_home():
    return FileResponse(BASE_DIR / "templates" / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def get_favicon():
    return FileResponse(
        BASE_DIR / "static" / "icons" / "favicon.ico",
        media_type="image/vnd.microsoft.icon",
    )


@app.get("/sw.js", include_in_schema=False)
def get_service_worker():
    return FileResponse(
        BASE_DIR / "static" / "sw.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/api/info")
def get_feed_info():
    feed = cache.get_feed()
    metadata = feed.get("metadata") or {}
    last_updated = metadata.get("lastUpdated", "Unknown")
    return {
        "last_updated": last_updated,
        "total_sections": len(feed.get("courses", [])),
        "courses": cache.courses_summary,
        "faculties": cache.faculties,
        "time_slots": cache.time_slots,
    }


@app.post("/api/feed/refresh")
def refresh_feed():
    feed = cache.get_feed(force_refresh=True)
    metadata = feed.get("metadata") or {}
    return {
        "success": True,
        "message": "Feed refreshed successfully.",
        "last_updated": metadata.get("lastUpdated", "Unknown"),
        "total_sections": len(feed.get("courses", [])),
    }


@app.get("/api/course/{code}")
def get_course_details(code: str):
    feed = cache.get_feed()
    all_sections = feed.get("courses", [])
    report = ps.build_course_report(all_sections, code)
    if not report:
        similar = ps.suggest_similar(all_sections, code)
        raise HTTPException(
            status_code=404,
            detail=f"Course '{code.upper()}' not found." + (f" Did you mean: {', '.join(similar)}?" if similar else ""),
        )
    course_title, groups = report

    flat_sections = []
    for grp_label, rows in groups:
        for r in rows:
            flat_sections.append({
                "sectionName": r["sectionName"],
                "faculty": r["faculty"],
                "capacity": r["capacity"],
                "consumedSeat": r["consumedSeat"],
                "remaining": (r["capacity"] - r["consumedSeat"]) if (r["capacity"] is not None and r["consumedSeat"] is not None) else None,
                "group_label": grp_label,
                "theory": [serialize_meeting(m) for m in r["theory_meetings"]],
                "lab": [serialize_meeting(m) for m in r["lab_meetings"]],
                "examDetail": r["examDetail"],
            })

    return {
        "courseCode": code.upper(),
        "courseTitle": course_title,
        "sections": flat_sections,
    }


@app.post("/api/generate")
def generate_schedules(req: GenerateRequest):
    feed = cache.get_feed()
    request_key = req.model_dump_json()
    reused = analysis_cache.get(feed, request_key)
    if reused is not None:
        return {**reused, "logs": [*reused["logs"], "Reused an identical analysis for the current feed."]}
    all_sections = feed.get("courses", [])
    last_updated = (feed.get("metadata") or {}).get("lastUpdated", "Unknown")

    logs: List[str] = []
    def log(msg: str):
        logs.append(str(msg))

    # Parse and extract course codes
    ordered_codes, inline_sections = sc.extract_course_codes_and_sections(req.courses)
    if len(ordered_codes) < 2:
        raise HTTPException(
            status_code=400,
            detail="Please provide at least two distinct course codes to combine.",
        )

    log(f"Processing {len(ordered_codes)} course(s): {', '.join(ordered_codes)}")

    # Parse constraints
    prefer_prefs = sc.parse_faculty_preferences(req.prefer_faculty)
    avoid_prefs = sc.parse_faculty_preferences(req.avoid_faculty)
    skip_rules = sc.parse_skip_times(req.skip_times)
    mandatory_sec_prefs = sc.parse_mandatory_sections(req.mandatory_sections)

    for c_code, s_set in inline_sections.items():
        mandatory_sec_prefs["per_course"].setdefault(c_code, set()).update(s_set)

    per_course_lists = []
    for code in ordered_codes:
        res = sc.build_course_sections(all_sections, code)
        if res is None:
            hint = ps.suggest_similar(all_sections, code)
            hint_str = f" Did you mean: {', '.join(hint)}?" if hint else ""
            raise HTTPException(status_code=404, detail=f"No sections found for '{code}'.{hint_str}")
        title, rows = res

        # 1. Mandatory sections filter
        course_target_secs = set(mandatory_sec_prefs["global"]) | mandatory_sec_prefs["per_course"].get(code.upper(), set())
        if course_target_secs:
            matched_rows, dropped_non_mand = sc.filter_mandatory_sections(rows, course_target_secs, code)
            if not matched_rows:
                avail_secs = ", ".join(r["sectionName"] for r in rows)
                raise HTTPException(
                    status_code=400,
                    detail=f"'{code.upper()}' has no section matching mandatory section(s) ({', '.join(sorted(course_target_secs))}). Available sections: {avail_secs}",
                )
            rows = matched_rows
            for r in rows:
                r["_mandatory_match"] = True
            log(f"  - {code.upper()}: filtered to mandatory section(s) ({len(rows)} candidate(s))")

        # 2. Avoid faculty filter
        rows, dropped_avoid = sc.filter_out_avoided_faculty(rows, avoid_prefs)
        if dropped_avoid:
            log(f"  - {code.upper()}: excluded {len(dropped_avoid)} section(s) taught by avoided faculty")
        if not rows:
            raise HTTPException(
                status_code=400,
                detail=f"'{code}' has no sections left after applying avoided faculty filter.",
            )

        # 3. Mandatory preferred faculty filter
        if req.mandatory_preferred_faculty:
            names_set = set(prefer_prefs["global"]) | prefer_prefs["per_course"].get(code.upper(), set())
            if names_set:
                rows, dropped_pref = sc.filter_non_preferred_faculty(rows, prefer_prefs, code)
                if not rows:
                    raise HTTPException(
                        status_code=400,
                        detail=f"'{code}' has no sections left matching mandatory preferred faculty ({', '.join(sorted(names_set))}).",
                    )
                log(f"  - {code.upper()}: filtered to mandatory preferred faculty ({len(rows)} candidate(s))")

        # 4. Skip class times filter
        rows, dropped_time = sc.filter_out_skipped_times(rows, skip_rules)
        if dropped_time:
            log(f"  - {code.upper()}: excluded {len(dropped_time)} section(s) matching skip times")
        if not rows:
            raise HTTPException(
                status_code=400,
                detail=f"'{code}' has no sections left after applying skip times filter.",
            )

        # 5. Open seats filter
        if req.only_open:
            open_rows = [r for r in rows if r["remaining"] is None or r["remaining"] > 0]
            if open_rows:
                rows = open_rows
            else:
                log(f"  ! {code.upper()}: no open seats found; keeping full sections to allow schedule generation.")

        per_course_lists.append(rows)

    total_raw = 1
    for rows in per_course_lists:
        total_raw *= len(rows)
    log(f"Searching {total_raw:,} potential combinations with reusable conflict checks...")
    sort_keys_combined = req.sort_by
    if req.secondary_sort_by and req.secondary_sort_by != "none" and req.secondary_sort_by != req.sort_by:
        sort_keys_combined += f",{req.secondary_sort_by}"
    _, sort_keys = sc.build_sort_key_fn(sort_keys_combined, prefer_prefs, target_days=req.target_days, on_warning=log)
    started = time.perf_counter()
    total_valid, valid = sc.search_combinations(
        per_course_lists, sort_keys, prefer_prefs, target_days=req.target_days,
        exact_days=req.exact_days, max_results=req.max_results,
    )
    for combo, stats, _ in valid:
        stats["days_list"] = extract_active_days(combo)
        stats.setdefault("target_days_diff", 0)
        for row in combo:
            row["_pref_match"] = sc.section_matches_faculty_pref(row, prefer_prefs)
    log(f"Found {total_valid:,} conflict-free combinations in {time.perf_counter() - started:.2f}s (complete search).")

    if total_valid == 0:
        result = {
            "success": True,
            "total_valid": 0,
            "count": 0,
            "sort_keys": sort_keys,
            "last_updated": last_updated,
            "logs": logs,
            "combinations": [],
        }

        analysis_cache.put(feed, request_key, result)
        return result

    if sort_keys != ["none"]:
        valid.sort(key=lambda item: item[2])

    limited = valid[: req.max_results]
    serialized_combos = []
    for idx, (combo, stats, _) in enumerate(limited, 1):
        serialized_combos.append({
            "index": idx,
            "stats": stats,
            "sections": [serialize_section_row(r) for r in combo],
            "grid": build_json_weekly_grid(combo),
        })

    result = {
        "success": True,
        "total_valid": total_valid,
        "count": len(serialized_combos),
        "sort_keys": sort_keys,
        "last_updated": last_updated,
        "logs": logs,
        "combinations": serialized_combos,
    }

    analysis_cache.put(feed, request_key, result)
    return result


@app.post("/api/export/pdf")
def export_pdf(req: GenerateRequest):
    with tempfile.TemporaryDirectory() as temp_dir:
        res = sc.run_combinator(
            courses=req.courses,
            only_open=req.only_open,
            target_days=req.target_days,
            exact_days=req.exact_days,
            prefer_faculty=req.prefer_faculty,
            avoid_faculty=req.avoid_faculty,
            mandatory_preferred_faculty=req.mandatory_preferred_faculty,
            mandatory_sections=req.mandatory_sections,
            skip_times=req.skip_times,
            sort_by=req.sort_by + (f",{req.secondary_sort_by}" if req.secondary_sort_by and req.secondary_sort_by != "none" else ""),
            max_results=req.max_results,
            output_format="pdf",
            output_dir=temp_dir,
            log=lambda _: None,
        )
        if not res["output_paths"]:
            raise HTTPException(status_code=400, detail="No conflict-free schedules found to export.")

        pdf_path = res["output_paths"][0]
        content = pdf_path.read_bytes()
        filename = pdf_path.name

    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/api/preview/pdf")
def preview_pdf(req: GenerateRequest):
    with tempfile.TemporaryDirectory() as temp_dir:
        res = sc.run_combinator(
            courses=req.courses,
            only_open=req.only_open,
            target_days=req.target_days,
            exact_days=req.exact_days,
            prefer_faculty=req.prefer_faculty,
            avoid_faculty=req.avoid_faculty,
            mandatory_preferred_faculty=req.mandatory_preferred_faculty,
            mandatory_sections=req.mandatory_sections,
            skip_times=req.skip_times,
            sort_by=req.sort_by + (f",{req.secondary_sort_by}" if req.secondary_sort_by and req.secondary_sort_by != "none" else ""),
            max_results=req.max_results,
            output_format="pdf",
            output_dir=temp_dir,
            log=lambda _: None,
        )
        if not res["output_paths"]:
            raise HTTPException(status_code=400, detail="No conflict-free schedules found to preview.")

        pdf_path = res["output_paths"][0]
        content = pdf_path.read_bytes()
        filename = pdf_path.name

    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"},
    )


@app.post("/api/export/csv")
def export_csv(req: GenerateRequest):
    with tempfile.TemporaryDirectory() as temp_dir:
        res = sc.run_combinator(
            courses=req.courses,
            only_open=req.only_open,
            target_days=req.target_days,
            exact_days=req.exact_days,
            prefer_faculty=req.prefer_faculty,
            avoid_faculty=req.avoid_faculty,
            mandatory_preferred_faculty=req.mandatory_preferred_faculty,
            mandatory_sections=req.mandatory_sections,
            skip_times=req.skip_times,
            sort_by=req.sort_by + (f",{req.secondary_sort_by}" if req.secondary_sort_by and req.secondary_sort_by != "none" else ""),
            max_results=req.max_results,
            output_format="csv",
            output_dir=temp_dir,
            log=lambda _: None,
        )
        if not res["output_paths"]:
            raise HTTPException(status_code=400, detail="No conflict-free schedules found to export.")

        csv_path = res["output_paths"][0]
        content = csv_path.read_text(encoding="utf-8")
        filename = csv_path.name

    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
