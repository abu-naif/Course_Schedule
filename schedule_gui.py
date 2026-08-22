#!/usr/bin/env python3
"""
Schedule Combinator -- GUI
--------------------------

A single-window desktop front end for schedule_combinator.py. Every
preference (courses, open-seats filter, desired class days per week,
faculty preferences, sort order, output format/folder) lives on one form --
there are no chained popup dialogs. Progress and results are shown in the
same window.

Run it with:
    python schedule_gui.py

Requires: this file, schedule_combinator.py, and prepreg_scraper.py all in
the same folder (same as the CLI tool). Uses only the Python standard
library (tkinter) plus whatever schedule_combinator.py itself needs
(reportlab, only if you use PDF output).

Note for Linux users: if you get "No module named tkinter", install it
with your package manager, e.g. `sudo apt install python3-tk`.
"""

import queue
import re
import subprocess
import sys
import threading
import traceback
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    print(
        "ERROR: tkinter isn't available in this Python install.\n"
        "  - On Ubuntu/Debian: sudo apt install python3-tk\n"
        "  - On Fedora:        sudo dnf install python3-tkinter\n"
        "  - On macOS/Windows: tkinter ships with the standard python.org installer.",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    import schedule_combinator as sc
except ImportError as e:
    # Only tkinter is up yet, so a single native error dialog is fine here --
    # this isn't a chain of preference prompts, just a one-time setup problem.
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Missing files",
        "Couldn't import schedule_combinator.py (and, through it, "
        f"prepreg_scraper.py).\n\nMake sure schedule_gui.py sits in the same "
        f"folder as both of those files.\n\nDetails: {e}",
    )
    sys.exit(1)


# Display label -> internal sort key understood by schedule_combinator.
SORT_LABELS = [
    ("Most compact schedule (least idle time)", "gap"),
    ("Fewest days used", "days"),
    ("Closest to my desired days/week", "target_days"),
    ("Earliest class start time", "earliest"),
    ("Latest class start time", "latest"),
    ("Preferred-faculty matches", "faculty"),
    ("No further sorting", "none"),
]
SORT_LABEL_TO_KEY = dict(SORT_LABELS)
SECONDARY_SORT_LABELS = ["(none)"] + [lbl for lbl, _ in SORT_LABELS]


class ScheduleGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Schedule Combinator")
        self.geometry("880x820")
        self.minsize(760, 640)

        self._worker = None
        self._queue = queue.Queue()
        self._last_output_dir = None

        self._build_form()
        self._poll_queue()

    # ------------------------------------------------------------------
    # UI construction -- everything lives in this one window.
    # ------------------------------------------------------------------
    def _build_form(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0, yscrollincrement=1)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)

        outer = ttk.Frame(self.canvas, padding=12)
        outer.columnconfigure(0, weight=1)

        self._canvas_frame_id = self.canvas.create_window((0, 0), window=outer, anchor="nw")

        outer.bind("<Configure>", self._on_outer_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Smooth scrolling bindings
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>", self._on_mousewheel)
        self.bind_all("<Button-5>", self._on_mousewheel)
        self.bind_all("<Prior>", self._on_page_up)
        self.bind_all("<Next>", self._on_page_down)

        # --- Courses -----------------------------------------------------
        courses_frame = ttk.LabelFrame(outer, text="Courses", padding=10)
        courses_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        courses_frame.columnconfigure(1, weight=1)

        ttk.Label(courses_frame, text="Course codes (comma or space separated):").grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        self.courses_var = tk.StringVar()
        self.courses_var.trace_add("write", self._update_course_slot_labels)
        ttk.Entry(courses_frame, textvariable=self.courses_var).grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=(2, 8)
        )
        ttk.Label(courses_frame, text="e.g.  CSE370, CSE470, EEE201", foreground="#666").grid(
            row=2, column=0, columnspan=3, sticky="w"
        )

        ttk.Label(courses_frame, text="Or load codes from a text file:").grid(
            row=3, column=0, sticky="w", pady=(8, 0)
        )
        self.from_file_var = tk.StringVar()
        ttk.Entry(courses_frame, textvariable=self.from_file_var, state="readonly").grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(2, 0)
        )
        ttk.Button(courses_frame, text="Browse...", command=self._pick_course_file).grid(
            row=4, column=2, sticky="e", padx=(6, 0), pady=(2, 0)
        )
        ttk.Button(courses_frame, text="Clear file", command=lambda: self.from_file_var.set("")).grid(
            row=5, column=2, sticky="e", pady=(4, 0)
        )

        # --- Preferences ---------------------------------------------------
        # --- Preferences ---------------------------------------------------
        prefs_frame = ttk.LabelFrame(outer, text="Preferences & Constraints", padding=10)
        prefs_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        prefs_frame.columnconfigure(1, weight=1)

        self.only_open_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            prefs_frame, text="Only show sections with open seats", variable=self.only_open_var
        ).grid(row=0, column=0, columnspan=3, sticky="w")

        ttk.Separator(prefs_frame).grid(row=1, column=0, columnspan=3, sticky="ew", pady=8)

        self.use_target_days_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            prefs_frame,
            text="I want classes on a specific number of days per week:",
            variable=self.use_target_days_var,
            command=self._on_target_days_toggle,
        ).grid(row=2, column=0, sticky="w")

        self.target_days_var = tk.IntVar(value=3)
        self.target_days_spin = ttk.Spinbox(
            prefs_frame, from_=1, to=7, width=4, textvariable=self.target_days_var, state="disabled"
        )
        self.target_days_spin.grid(row=2, column=1, sticky="w", padx=(6, 0))
        ttk.Label(prefs_frame, text="day(s)/week").grid(row=2, column=2, sticky="w")

        self.exact_days_var = tk.BooleanVar(value=False)
        self.exact_days_check = ttk.Checkbutton(
            prefs_frame,
            text="Require exactly that many days (hard filter -- otherwise it's just a sorting preference)",
            variable=self.exact_days_var,
            state="disabled",
        )
        self.exact_days_check.grid(row=3, column=0, columnspan=3, sticky="w", padx=(20, 0))

        ttk.Separator(prefs_frame).grid(row=4, column=0, columnspan=3, sticky="ew", pady=8)

        # Mandatory Section Preferences Sub-Section
        sec_header = ttk.Label(prefs_frame, text="Mandatory Section Preferences & Constraints", font=("TkDefaultFont", 9, "bold"))
        sec_header.grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 4))

        ttk.Label(
            prefs_frame,
            text="Mandatory Section(s) for Individual Courses (only combinations with these sections will be generated):",
            foreground="#333",
        ).grid(row=6, column=0, columnspan=3, sticky="w", padx=(6, 0), pady=(2, 2))

        self.per_course_sec_vars = []
        for i in range(5):
            lbl = ttk.Label(prefs_frame, text=f"Course {i+1} Mandatory Sec:", width=22, anchor="w")
            lbl.grid(row=7 + i, column=0, sticky="w", padx=(12, 0), pady=1)
            var = tk.StringVar()
            entry = ttk.Entry(prefs_frame, textvariable=var)
            entry.grid(row=7 + i, column=1, columnspan=2, sticky="ew", padx=(6, 0), pady=1)
            self.per_course_sec_vars.append((lbl, var))

        ttk.Label(prefs_frame, text="Global (All/Multi-Course):", width=22, anchor="w").grid(
            row=12, column=0, sticky="w", padx=(12, 0), pady=(4, 0)
        )
        self.global_section_var = tk.StringVar()
        ttk.Entry(prefs_frame, textvariable=self.global_section_var).grid(
            row=12, column=1, columnspan=2, sticky="ew", padx=(6, 0), pady=(4, 0)
        )
        ttk.Label(
            prefs_frame,
            text="e.g. CSE370:01, MAT215:02 or 01 (restricts candidate combinations)",
            foreground="#666",
        ).grid(row=13, column=1, columnspan=2, sticky="w", padx=(6, 0))

        ttk.Separator(prefs_frame).grid(row=14, column=0, columnspan=3, sticky="ew", pady=8)

        # Faculty Preferences Sub-Section
        fac_header = ttk.Label(prefs_frame, text="Faculty Preferences & Constraints", font=("TkDefaultFont", 9, "bold"))
        fac_header.grid(row=15, column=0, columnspan=3, sticky="w", pady=(0, 4))

        self.mandatory_faculty_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            prefs_frame,
            text="Mandatory faculty from pref (strictly exclude any section not taught by preferred faculty)",
            variable=self.mandatory_faculty_var,
        ).grid(row=16, column=0, columnspan=3, sticky="w", padx=(6, 0), pady=(0, 4))

        ttk.Label(prefs_frame, text="Preferred Faculty for Individual Courses:", foreground="#333").grid(
            row=17, column=0, columnspan=3, sticky="w", padx=(6, 0), pady=(2, 2)
        )

        self.per_course_fac_vars = []
        for i in range(5):
            lbl = ttk.Label(prefs_frame, text=f"Course {i+1} Preferred Fac:", width=22, anchor="w")
            lbl.grid(row=18 + i, column=0, sticky="w", padx=(12, 0), pady=1)
            var = tk.StringVar()
            entry = ttk.Entry(prefs_frame, textvariable=var)
            entry.grid(row=18 + i, column=1, columnspan=2, sticky="ew", padx=(6, 0), pady=1)
            self.per_course_fac_vars.append((lbl, var))

        ttk.Label(prefs_frame, text="Global (All courses):", width=22, anchor="w").grid(
            row=23, column=0, sticky="w", padx=(12, 0), pady=(4, 0)
        )
        self.global_faculty_var = tk.StringVar()
        ttk.Entry(prefs_frame, textvariable=self.global_faculty_var).grid(
            row=23, column=1, columnspan=2, sticky="ew", padx=(6, 0), pady=(4, 0)
        )
        ttk.Label(prefs_frame, text="e.g. AIB, DZK (applies to any course)", foreground="#666").grid(
            row=24, column=1, columnspan=2, sticky="w", padx=(6, 0)
        )

        ttk.Label(prefs_frame, text="Avoid faculty (optional):", width=22, anchor="w").grid(
            row=25, column=0, sticky="w", padx=(6, 0), pady=(6, 0)
        )
        self.avoid_faculty_var = tk.StringVar()
        ttk.Entry(prefs_frame, textvariable=self.avoid_faculty_var).grid(
            row=25, column=1, columnspan=2, sticky="ew", padx=(6, 0), pady=(6, 0)
        )
        ttk.Label(
            prefs_frame, text="Sections taught by these are dropped entirely.", foreground="#666"
        ).grid(row=26, column=1, columnspan=2, sticky="w", padx=(6, 0))

        ttk.Separator(prefs_frame).grid(row=27, column=0, columnspan=3, sticky="ew", pady=8)

        ttk.Label(prefs_frame, text="Skip class times (optional):").grid(row=28, column=0, sticky="w")
        skip_slots_frame = ttk.Frame(prefs_frame)
        skip_slots_frame.grid(row=28, column=1, columnspan=2, sticky="w", padx=(6, 0))

        self.skip_slot_vars = {}
        common_slots = [
            ("08:00 AM - 09:20 AM", "08:00 AM"),
            ("05:00 PM - 06:20 PM", "05:00 PM"),
            ("06:30 PM - 07:50 PM", "06:30 PM"),
            ("08:00 PM - 09:20 PM", "08:00 PM"),
        ]
        for slot_val, slot_lbl in common_slots:
            var = tk.BooleanVar(value=False)
            self.skip_slot_vars[slot_val] = var
            ttk.Checkbutton(skip_slots_frame, text=slot_lbl, variable=var).pack(side="left", padx=(0, 10))

        ttk.Label(prefs_frame, text="Custom skip times:").grid(row=29, column=0, sticky="w", pady=(6, 0))
        self.skip_times_var = tk.StringVar()
        ttk.Entry(prefs_frame, textvariable=self.skip_times_var).grid(
            row=29, column=1, columnspan=2, sticky="ew", padx=(6, 0), pady=(6, 0)
        )
        ttk.Label(
            prefs_frame,
            text="e.g.  08:00 AM - 09:20 AM, Sun 05:00 PM - 06:20 PM, 08:00 AM - 11:00 AM",
            foreground="#666",
        ).grid(row=30, column=1, columnspan=2, sticky="w", padx=(6, 0))

        # --- Sort & output ---------------------------------------------
        out_frame = ttk.LabelFrame(outer, text="Sorting & Output", padding=10)
        out_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        out_frame.columnconfigure(1, weight=1)

        ttk.Label(out_frame, text="Sort primarily by:").grid(row=0, column=0, sticky="w")
        self.primary_sort_var = tk.StringVar(value=SORT_LABELS[0][0])
        ttk.Combobox(
            out_frame, textvariable=self.primary_sort_var, values=[l for l, _ in SORT_LABELS],
            state="readonly", width=38,
        ).grid(row=0, column=1, sticky="w", padx=(6, 0))

        ttk.Label(out_frame, text="Then break ties by:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.secondary_sort_var = tk.StringVar(value="(none)")
        ttk.Combobox(
            out_frame, textvariable=self.secondary_sort_var, values=SECONDARY_SORT_LABELS,
            state="readonly", width=38,
        ).grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(4, 0))

        ttk.Label(out_frame, text="Max results to write:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.max_results_var = tk.IntVar(value=30)
        ttk.Spinbox(out_frame, from_=1, to=500, width=6, textvariable=self.max_results_var).grid(
            row=2, column=1, sticky="w", padx=(6, 0), pady=(8, 0)
        )

        ttk.Label(out_frame, text="Output format:").grid(row=3, column=0, sticky="w", pady=(8, 0))
        fmt_row = ttk.Frame(out_frame)
        fmt_row.grid(row=3, column=1, sticky="w", padx=(6, 0), pady=(8, 0))
        self.format_var = tk.StringVar(value="pdf")
        for label, val in [("PDF", "pdf"), ("CSV", "csv"), ("Both", "both")]:
            ttk.Radiobutton(fmt_row, text=label, value=val, variable=self.format_var).pack(side="left", padx=(0, 10))

        ttk.Label(out_frame, text="Output folder:").grid(row=4, column=0, sticky="w", pady=(8, 0))
        out_dir_row = ttk.Frame(out_frame)
        out_dir_row.grid(row=4, column=1, sticky="ew", padx=(6, 0), pady=(8, 0))
        out_dir_row.columnconfigure(0, weight=1)
        self.output_dir_var = tk.StringVar(value=str(Path("output").resolve()))
        ttk.Entry(out_dir_row, textvariable=self.output_dir_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(out_dir_row, text="Browse...", command=self._pick_output_dir).grid(row=0, column=1, padx=(6, 0))

        # --- Run controls ------------------------------------------------
        run_row = ttk.Frame(outer)
        run_row.grid(row=3, column=0, sticky="ew", pady=(4, 8))
        self.run_button = ttk.Button(run_row, text="Find Schedules", command=self._on_run)
        self.run_button.pack(side="left")
        self.open_folder_button = ttk.Button(
            run_row, text="Open Output Folder", command=self._open_output_folder, state="disabled"
        )
        self.open_folder_button.pack(side="left", padx=(8, 0))
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(run_row, textvariable=self.status_var, foreground="#444").pack(side="left", padx=(14, 0))

        # --- Log / results -------------------------------------------------
        log_frame = ttk.LabelFrame(outer, text="Progress & Results", padding=6)
        log_frame.grid(row=4, column=0, sticky="nsew")
        outer.rowconfigure(4, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, wrap="word", height=14, state="disabled", font=("Courier New", 10))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)

    # ------------------------------------------------------------------
    # Small interaction handlers
    # ------------------------------------------------------------------
    def _on_outer_configure(self, event=None):
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._canvas_frame_id, width=event.width)

    def _on_mousewheel(self, event):
        widget = getattr(event, "widget", None)
        is_log = False
        if hasattr(self, "log_text"):
            if widget == self.log_text or str(widget) == str(self.log_text) or (widget and "log_text" in str(widget)):
                is_log = True

        if is_log:
            if sys.platform == "darwin":
                if event.delta:
                    delta = -1 * (1 if event.delta > 0 else -1) if abs(event.delta) < 120 else -1 * int(event.delta / 120)
                    self.log_text.yview_scroll(delta, "units")
            elif sys.platform.startswith("win"):
                if event.delta:
                    self.log_text.yview_scroll(-1 * int(event.delta / 120), "units")
            else:
                if getattr(event, "num", None) == 4:
                    self.log_text.yview_scroll(-1, "units")
                elif getattr(event, "num", None) == 5:
                    self.log_text.yview_scroll(1, "units")
                elif event.delta:
                    self.log_text.yview_scroll(-1 * int(event.delta / 120), "units")
            return "break"

        if sys.platform == "darwin":
            if event.delta:
                if abs(event.delta) >= 120:
                    self.canvas.yview_scroll(-1 * int(event.delta / 120) * 35, "units")
                else:
                    self.canvas.yview_scroll(-1 * int(event.delta * 2), "units")
        elif sys.platform.startswith("win"):
            if event.delta:
                self.canvas.yview_scroll(-1 * int(event.delta / 120) * 35, "units")
        else:
            if getattr(event, "num", None) == 4:
                self.canvas.yview_scroll(-25, "units")
            elif getattr(event, "num", None) == 5:
                self.canvas.yview_scroll(25, "units")
            elif event.delta:
                self.canvas.yview_scroll(-1 * int(event.delta / 120) * 35, "units")

    def _on_page_up(self, event):
        if isinstance(event.widget, (ttk.Entry, tk.Entry, tk.Text, ttk.Spinbox, ttk.Combobox)):
            return
        self.canvas.yview_scroll(-1, "pages")

    def _on_page_down(self, event):
        if isinstance(event.widget, (ttk.Entry, tk.Entry, tk.Text, ttk.Spinbox, ttk.Combobox)):
            return
        self.canvas.yview_scroll(1, "pages")

    def _on_target_days_toggle(self):
        enabled = self.use_target_days_var.get()
        self.target_days_spin.configure(state="normal" if enabled else "disabled")
        self.exact_days_check.configure(state="normal" if enabled else "disabled")
        if not enabled:
            self.exact_days_var.set(False)
        elif self.primary_sort_var.get() == SORT_LABELS[0][0]:
            # Nudge the sort order toward the preference the user just turned
            # on -- they can still change it manually afterward.
            self.primary_sort_var.set("Closest to my desired days/week")

    def _pick_course_file(self):
        path = filedialog.askopenfilename(
            title="Choose a text file of course codes", filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.from_file_var.set(path)

    def _pick_output_dir(self):
        path = filedialog.askdirectory(title="Choose output folder")
        if path:
            self.output_dir_var.set(path)

    def _open_output_folder(self):
        if not self._last_output_dir:
            return
        path = str(self._last_output_dir)
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showinfo("Output folder", f"Files are in:\n{path}\n\n(Couldn't auto-open it: {e})")

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------
    def _log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", str(msg) + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def _collect_sort_by(self):
        keys = [SORT_LABEL_TO_KEY[self.primary_sort_var.get()]]
        sec_label = self.secondary_sort_var.get()
        if sec_label != "(none)":
            sec_key = SORT_LABEL_TO_KEY[sec_label]
            if sec_key not in keys:
                keys.append(sec_key)
        return ",".join(keys)

    def _update_course_slot_labels(self, *args):
        raw_courses = self.courses_var.get().replace(",", " ").split()
        for i in range(len(self.per_course_fac_vars)):
            if i < len(raw_courses):
                code = raw_courses[i].strip().split(":")[0].strip().upper()
                if i < len(self.per_course_fac_vars):
                    self.per_course_fac_vars[i][0].configure(text=f"{code} Preferred Fac:")
                if i < len(self.per_course_sec_vars):
                    self.per_course_sec_vars[i][0].configure(text=f"{code} Mandatory Sec:")
            else:
                if i < len(self.per_course_fac_vars):
                    self.per_course_fac_vars[i][0].configure(text=f"Course {i+1} Preferred Fac:")
                if i < len(self.per_course_sec_vars):
                    self.per_course_sec_vars[i][0].configure(text=f"Course {i+1} Mandatory Sec:")

    def _collect_mandatory_sections(self):
        raw_courses = self.courses_var.get().replace(",", " ").split()
        tokens = []
        for i, (lbl, var) in enumerate(self.per_course_sec_vars):
            secs = var.get().strip()
            if not secs:
                continue
            if i < len(raw_courses):
                code = raw_courses[i].strip().split(":")[0].strip().upper()
                tokens.append(f"{code}:{secs}")
            else:
                parsed = self._split_names(secs)
                if parsed:
                    tokens.extend(parsed)

        global_secs = self.global_section_var.get().strip()
        if global_secs:
            parsed_global = self._split_names(global_secs)
            if parsed_global:
                tokens.extend(parsed_global)

        return tokens or None

    def _collect_prefer_faculty(self):
        raw_courses = self.courses_var.get().replace(",", " ").split()
        tokens = []
        for i, (lbl, var) in enumerate(self.per_course_fac_vars):
            names = var.get().strip()
            if not names:
                continue
            if i < len(raw_courses):
                code = raw_courses[i].strip().split(":")[0].strip().upper()
                tokens.append(f"{code}:{names}")
            else:
                parsed = self._split_names(names)
                if parsed:
                    tokens.extend(parsed)

        global_names = self.global_faculty_var.get().strip()
        if global_names:
            parsed_global = self._split_names(global_names)
            if parsed_global:
                tokens.extend(parsed_global)

        return tokens or None

    def _on_run(self):
        if self._worker and self._worker.is_alive():
            return  # already running

        raw_courses = self.courses_var.get().replace(",", " ").split()
        from_file = self.from_file_var.get().strip() or None

        if not raw_courses and not from_file:
            messagebox.showwarning("No courses", "Enter at least two course codes, or load them from a file.")
            return

        target_days = self.target_days_var.get() if self.use_target_days_var.get() else None
        exact_days = bool(self.exact_days_var.get()) and target_days is not None

        skip_times_list = [slot for slot, var in self.skip_slot_vars.items() if var.get()]
        custom_skip = self.skip_times_var.get().strip()
        if custom_skip:
            skip_times_list.extend([t.strip() for t in re.split(r"[,;]", custom_skip) if t.strip()])

        kwargs = dict(
            courses=raw_courses,
            from_file=from_file,
            only_open=self.only_open_var.get(),
            sort_by=self._collect_sort_by(),
            prefer_faculty=self._collect_prefer_faculty(),
            avoid_faculty=self._split_names(self.avoid_faculty_var.get()),
            mandatory_preferred_faculty=self.mandatory_faculty_var.get(),
            mandatory_sections=self._collect_mandatory_sections(),
            skip_times=skip_times_list,
            target_days=target_days,
            exact_days=exact_days,
            max_results=self.max_results_var.get(),
            output_format=self.format_var.get(),
            output_dir=self.output_dir_var.get().strip() or "output",
        )

        self._clear_log()
        self.status_var.set("Working...")
        self.run_button.configure(state="disabled")
        self.open_folder_button.configure(state="disabled")

        # Scroll down so the progress and log area is brought into view
        self.after(50, lambda: self.canvas.yview_moveto(1.0))

        self._worker = threading.Thread(target=self._worker_run, args=(kwargs,), daemon=True)
        self._worker.start()

    @staticmethod
    def _split_names(text):
        """Turns free-typed text into the token list schedule_combinator
        expects (same shape as the CLI's --prefer-faculty/--avoid-faculty
        nargs='+'): bare names are their own token ('AIB'), while a
        'COURSE:NAME1,NAME2' group stays together as one token.

        Accepts commas and/or spaces between bare names, e.g. all of
        'AIB, DZK', 'AIB DZK', and 'AIB,DZK' parse to ['AIB', 'DZK'];
        'CSE370:AIB,TAZ CSE260:DZK' parses to ['CSE370:AIB,TAZ', 'CSE260:DZK']
        with the commas inside each group preserved."""
        text = text.strip()
        if not text:
            return None
        result = []
        for tok in text.split():
            if ":" in tok:
                cleaned = tok.strip(",")
                if cleaned:
                    result.append(cleaned)
            else:
                for piece in tok.split(","):
                    piece = piece.strip()
                    if piece:
                        result.append(piece)
        return result or None

    def _worker_run(self, kwargs):
        def log_cb(msg):
            self._queue.put(("log", msg))

        try:
            result = sc.run_combinator(log=log_cb, **kwargs)
            self._queue.put(("done", result))
        except sc.CombinatorError as e:
            self._queue.put(("error", str(e)))
        except Exception:
            self._queue.put(("error", "Unexpected error:\n" + traceback.format_exc()))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "done":
                    self._on_done(payload)
                elif kind == "error":
                    self._on_error(payload)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _on_done(self, result):
        self.run_button.configure(state="normal")
        if result["total_valid"] == 0:
            self.status_var.set("No conflict-free combinations found.")
        else:
            self.status_var.set(
                f"Done -- {result['total_valid']} combination(s) found, "
                f"{result['written_count']} written."
            )
            if result["output_paths"]:
                self._last_output_dir = result["output_paths"][0].parent
                self.open_folder_button.configure(state="normal")
                self._log("\nFiles:")
                for p in result["output_paths"]:
                    self._log(f"  {p.resolve()}")

    def _on_error(self, message):
        self.run_button.configure(state="normal")
        self.status_var.set("Error -- see log below.")
        self._log("\nERROR: " + message)


def main():
    app = ScheduleGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
