/**
 * BracU Course Combinator Web Application
 * Frontend JavaScript Engine
 */

document.addEventListener("DOMContentLoaded", () => {
  // Initialize Lucide icons
  lucide.createIcons();

  // State
  const state = {
    allCourses: [],
    allFaculties: [],
    selectedCourses: [],
    targetDays: 0, // 0 means 'Any'
    currentCombinations: [],
    currentIndex: 0,
    sortKeys: [],
    lastPayload: null,
    isDark: true,
  };

  // DOM Elements
  const feedStatusText = document.getElementById("feedStatusText");
  const refreshFeedBtn = document.getElementById("refreshFeedBtn");
  const courseInput = document.getElementById("courseInput");
  const addCourseBtn = document.getElementById("addCourseBtn");
  const courseSuggestions = document.getElementById("courseSuggestions");
  const selectedCoursesContainer = document.getElementById("selectedCoursesContainer");
  const noCoursesPlaceholder = document.getElementById("noCoursesPlaceholder");
  const selectedCoursesCount = document.getElementById("selectedCoursesCount");
  const courseMandatorySlots = document.getElementById("courseMandatorySlots");

  const onlyOpenCheckbox = document.getElementById("onlyOpenCheckbox");
  const targetDayButtons = document.querySelectorAll(".target-day-btn");
  const targetDaysValue = document.getElementById("targetDaysValue");
  const exactDaysCheckbox = document.getElementById("exactDaysCheckbox");
  const mandatorySectionsInput = document.getElementById("mandatorySectionsInput");
  const preferredFacultyInput = document.getElementById("preferredFacultyInput");
  const mandatoryFacultyCheckbox = document.getElementById("mandatoryFacultyCheckbox");
  const avoidFacultyInput = document.getElementById("avoidFacultyInput");
  const customSkipTimesInput = document.getElementById("customSkipTimesInput");
  const primarySortSelect = document.getElementById("primarySortSelect");
  const secondarySortSelect = document.getElementById("secondarySortSelect");
  const maxResultsSlider = document.getElementById("maxResultsSlider");
  const maxResultsValue = document.getElementById("maxResultsValue");
  const resetPrefsBtn = document.getElementById("resetPrefsBtn");
  const generateBtn = document.getElementById("generateBtn");

  const emptyState = document.getElementById("emptyState");
  const loadingState = document.getElementById("loadingState");
  const activeResultsView = document.getElementById("activeResultsView");
  const validCountBadge = document.getElementById("validCountBadge");
  const sortNotice = document.getElementById("sortNotice");
  const showingNotice = document.getElementById("showingNotice");
  const prevOptionBtn = document.getElementById("prevOptionBtn");
  const nextOptionBtn = document.getElementById("nextOptionBtn");
  const optionJumpInput = document.getElementById("optionJumpInput");
  const totalOptionsDisplay = document.getElementById("totalOptionsDisplay");

  const metricGap = document.getElementById("metricGap");
  const metricDays = document.getElementById("metricDays");
  const metricFaculty = document.getElementById("metricFaculty");
  const timetableGridBody = document.getElementById("timetableGridBody");
  const sectionsDetailsTableBody = document.getElementById("sectionsDetailsTableBody");
  const engineLogsPre = document.getElementById("engineLogsPre");

  const copyScheduleBtn = document.getElementById("copyScheduleBtn");
  const copyBtnText = document.getElementById("copyBtnText");
  const exportPdfBtn = document.getElementById("exportPdfBtn");
  const exportCsvBtn = document.getElementById("exportCsvBtn");
  const printBtn = document.getElementById("printBtn");

  const themeToggleBtn = document.getElementById("themeToggleBtn");
  const themeIconSun = document.getElementById("themeIconSun");
  const themeIconMoon = document.getElementById("themeIconMoon");

  const courseInspectorModal = document.getElementById("courseInspectorModal");
  const closeInspectorBtn = document.getElementById("closeInspectorBtn");
  const inspectorCourseTitle = document.getElementById("inspectorCourseTitle");
  const inspectorTableBody = document.getElementById("inspectorTableBody");

  const helpModal = document.getElementById("helpModal");
  const openHelpBtn = document.getElementById("openHelpBtn");
  const closeHelpBtn = document.getElementById("closeHelpBtn");

  // -----------------------------------------------------------------------
  // Toast Notifications
  // -----------------------------------------------------------------------
  function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    const bgColors = {
      info: "bg-slate-800 border-slate-700 text-slate-200",
      success: "bg-emerald-900/90 border-emerald-700 text-emerald-100",
      error: "bg-rose-900/90 border-rose-700 text-rose-100",
      warning: "bg-amber-900/90 border-amber-700 text-amber-100",
    };
    toast.className = `p-3 rounded-xl border shadow-xl text-xs font-medium max-w-sm flex items-center space-x-2 transition-all duration-300 transform translate-y-2 opacity-0 pointer-events-auto ${bgColors[type] || bgColors.info}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.remove("translate-y-2", "opacity-0");
    }, 10);

    setTimeout(() => {
      toast.classList.add("opacity-0", "translate-y-2");
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // -----------------------------------------------------------------------
  // Theme Management
  // -----------------------------------------------------------------------
  function initTheme() {
    const saved = localStorage.getItem("theme");
    state.isDark = saved ? saved === "dark" : true;
    applyTheme();
  }

  function applyTheme() {
    if (state.isDark) {
      document.documentElement.classList.add("dark");
      themeIconSun.classList.add("hidden");
      themeIconMoon.classList.remove("hidden");
    } else {
      document.documentElement.classList.remove("dark");
      themeIconSun.classList.remove("hidden");
      themeIconMoon.classList.add("hidden");
    }
    lucide.createIcons();
  }

  themeToggleBtn.addEventListener("click", () => {
    state.isDark = !state.isDark;
    localStorage.setItem("theme", state.isDark ? "dark" : "light");
    applyTheme();
  });

  // -----------------------------------------------------------------------
  // Initial Feed Info Fetch
  // -----------------------------------------------------------------------
  async function fetchFeedInfo(refresh = false) {
    try {
      feedStatusText.textContent = refresh ? "Refreshing feed..." : "Syncing live feed...";
      const endpoint = refresh ? "/api/feed/refresh" : "/api/info";
      const method = refresh ? "POST" : "GET";
      const resp = await fetch(endpoint, { method });
      if (!resp.ok) throw new Error("Could not load feed data");
      const data = await resp.json();

      if (!refresh) {
        state.allCourses = data.courses || [];
        state.allFaculties = data.faculties || [];
      } else {
        // Re-fetch info to update course list
        const infoResp = await fetch("/api/info");
        const infoData = await infoResp.json();
        state.allCourses = infoData.courses || [];
        state.allFaculties = infoData.faculties || [];
      }

      const totalSec = data.total_sections || 0;
      feedStatusText.textContent = `Synced (${totalSec.toLocaleString()} sections)`;
      showToast(refresh ? "Course feed refreshed from USIS!" : "Feed connected successfully", "success");
    } catch (err) {
      feedStatusText.textContent = "Feed offline (local fallback)";
      showToast(err.message, "error");
    }
  }

  refreshFeedBtn.addEventListener("click", () => fetchFeedInfo(true));

  // -----------------------------------------------------------------------
  // Autocomplete Search for Courses
  // -----------------------------------------------------------------------
  courseInput.addEventListener("input", (e) => {
    const val = e.target.value.trim().toUpperCase();
    if (!val || val.length < 2) {
      courseSuggestions.classList.add("hidden");
      courseSuggestions.innerHTML = "";
      return;
    }

    const matches = state.allCourses.filter(
      (c) => c.code.includes(val) || (c.title && c.title.toUpperCase().includes(val))
    ).slice(0, 10);

    if (matches.length === 0) {
      courseSuggestions.classList.add("hidden");
      return;
    }

    courseSuggestions.innerHTML = matches
      .map(
        (m) => `
        <div class="course-suggestion-item p-2.5 hover:bg-slate-800 cursor-pointer flex items-center justify-between transition" data-code="${m.code}">
          <div>
            <div class="flex items-center space-x-2">
              <span class="font-bold text-xs text-brand-300 font-mono">${m.code}</span>
              <span class="text-[11px] text-slate-300">${m.title || ""}</span>
            </div>
            <p class="text-[10px] text-slate-400 mt-0.5">${m.sections_count} section(s) available</p>
          </div>
          <button class="text-xs px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 hover:text-white">
            + Add
          </button>
        </div>
      `
      )
      .join("");

    courseSuggestions.classList.remove("hidden");

    // Click handler for suggestion item
    courseSuggestions.querySelectorAll(".course-suggestion-item").forEach((el) => {
      el.addEventListener("click", () => {
        addCourse(el.dataset.code);
        courseInput.value = "";
        courseSuggestions.classList.add("hidden");
      });
    });
  });

  document.addEventListener("click", (e) => {
    if (!courseInput.contains(e.target) && !courseSuggestions.contains(e.target)) {
      courseSuggestions.classList.add("hidden");
    }
  });

  // -----------------------------------------------------------------------
  // Adding & Removing Courses
  // -----------------------------------------------------------------------
  function addCourse(code) {
    const clean = code.trim().toUpperCase();
    if (!clean) return;
    if (state.selectedCourses.includes(clean)) {
      showToast(`${clean} is already added.`, "warning");
      return;
    }
    state.selectedCourses.push(clean);
    renderSelectedCourses();
  }

  function removeCourse(code) {
    state.selectedCourses = state.selectedCourses.filter((c) => c !== code);
    renderSelectedCourses();
  }

  addCourseBtn.addEventListener("click", () => {
    const val = courseInput.value.trim().toUpperCase();
    if (val) {
      addCourse(val);
      courseInput.value = "";
      courseSuggestions.classList.add("hidden");
    }
  });

  courseInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const val = courseInput.value.trim().toUpperCase();
      if (val) {
        addCourse(val);
        courseInput.value = "";
        courseSuggestions.classList.add("hidden");
      }
    }
  });

  document.querySelectorAll(".quick-add-btn").forEach((btn) => {
    btn.addEventListener("click", () => addCourse(btn.dataset.code));
  });

  function renderSelectedCourses() {
    selectedCoursesCount.textContent = `${state.selectedCourses.length} course${state.selectedCourses.length === 1 ? "" : "s"}`;
    if (state.selectedCourses.length === 0) {
      selectedCoursesContainer.innerHTML = "";
      selectedCoursesContainer.appendChild(noCoursesPlaceholder);
      noCoursesPlaceholder.classList.remove("hidden");
      courseMandatorySlots.innerHTML = "";
      return;
    }

    noCoursesPlaceholder.classList.add("hidden");
    selectedCoursesContainer.innerHTML = state.selectedCourses
      .map((code, idx) => {
        const colorIdx = idx % 7;
        return `
        <div class="course-chip flex items-center space-x-1.5 px-2.5 py-1 rounded-xl border text-xs font-medium shadow-sm course-color-${colorIdx}">
          <span class="font-mono font-bold">${code}</span>
          <button type="button" class="inspect-course-btn p-0.5 hover:opacity-80" data-code="${code}" title="Inspect Sections">
            <i data-lucide="info" class="w-3.5 h-3.5"></i>
          </button>
          <button type="button" class="remove-course-btn p-0.5 hover:text-red-400 transition" data-code="${code}" title="Remove">
            <i data-lucide="x" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      `;
      })
      .join("");

    // Recreate Lucide Icons in chips
    lucide.createIcons();

    // Attach listeners
    selectedCoursesContainer.querySelectorAll(".remove-course-btn").forEach((btn) => {
      btn.addEventListener("click", () => removeCourse(btn.dataset.code));
    });

    selectedCoursesContainer.querySelectorAll(".inspect-course-btn").forEach((btn) => {
      btn.addEventListener("click", () => openCourseInspector(btn.dataset.code));
    });

    // Update mandatory section helper labels
    courseMandatorySlots.innerHTML = state.selectedCourses
      .map(
        (code) => `
        <div class="flex items-center space-x-2 text-[11px]">
          <span class="w-16 font-mono font-semibold text-brand-300">${code}:</span>
          <input type="text" class="course-spec-mand px-2 py-1 bg-slate-900 border border-slate-700 rounded text-xs text-slate-100 placeholder-slate-500 w-full" data-code="${code}" placeholder="e.g. 01, 02 (optional)">
        </div>
      `
      )
      .join("");
  }

  // -----------------------------------------------------------------------
  // Target Days Buttons
  // -----------------------------------------------------------------------
  targetDayButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      targetDayButtons.forEach((b) => b.classList.remove("active-day"));
      btn.classList.add("active-day");
      const days = parseInt(btn.dataset.days, 10);
      state.targetDays = days;
      if (days === 0) {
        targetDaysValue.textContent = "Any";
        exactDaysCheckbox.disabled = true;
        exactDaysCheckbox.checked = false;
      } else {
        targetDaysValue.textContent = `${days} day${days > 1 ? "s" : ""}`;
        exactDaysCheckbox.disabled = false;
      }
    });
  });

  maxResultsSlider.addEventListener("input", (e) => {
    maxResultsValue.textContent = e.target.value;
  });

  resetPrefsBtn.addEventListener("click", () => {
    onlyOpenCheckbox.checked = false;
    exactDaysCheckbox.checked = false;
    exactDaysCheckbox.disabled = true;
    targetDayButtons.forEach((b) => b.classList.remove("active-day"));
    targetDayButtons[0].classList.add("active-day");
    state.targetDays = 0;
    targetDaysValue.textContent = "Any";
    mandatorySectionsInput.value = "";
    preferredFacultyInput.value = "";
    mandatoryFacultyCheckbox.checked = false;
    avoidFacultyInput.value = "";
    customSkipTimesInput.value = "";
    document.querySelectorAll(".skip-slot-checkbox").forEach((cb) => (cb.checked = false));
    primarySortSelect.value = "gap";
    secondarySortSelect.value = "none";
    maxResultsSlider.value = "30";
    maxResultsValue.textContent = "30";
    showToast("Preferences reset to default.", "info");
  });

  // -----------------------------------------------------------------------
  // Course Inspector Modal
  // -----------------------------------------------------------------------
  async function openCourseInspector(code) {
    try {
      inspectorCourseTitle.textContent = `${code} - Loading sections...`;
      inspectorTableBody.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-slate-400">Fetching section details...</td></tr>`;
      courseInspectorModal.classList.remove("hidden");

      const resp = await fetch(`/api/course/${code}`);
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Failed to load course details");
      }
      const data = await resp.json();

      inspectorCourseTitle.textContent = `${data.courseCode} - ${data.courseTitle}`;
      if (!data.sections || data.sections.length === 0) {
        inspectorTableBody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-slate-400">No sections found for this course.</td></tr>`;
        return;
      }

      inspectorTableBody.innerHTML = data.sections
        .map((s) => {
          const seatsClass = s.remaining !== null && s.remaining <= 0 ? "text-rose-400 font-semibold" : "text-emerald-400";
          const seatsDisplay = s.remaining !== null ? `${s.remaining} left (${s.consumedSeat}/${s.capacity})` : "TBA";
          const theoryStr = s.theory && s.theory.length > 0 ? s.theory.map((t) => `${t.day_abbr} ${t.start_str}-${t.end_str} (${t.room})`).join("<br/>") : "TBA";
          const labStr = s.lab && s.lab.length > 0 ? s.lab.map((l) => `${l.day_abbr} ${l.start_str}-${l.end_str} (${l.room})`).join("<br/>") : "None";

          return `
          <tr class="hover:bg-slate-800/60 transition">
            <td class="py-2.5 font-bold font-mono text-brand-300">Sec ${s.sectionName}</td>
            <td class="py-2.5 font-semibold text-slate-200">${s.faculty}</td>
            <td class="py-2.5 text-slate-300 leading-tight">${theoryStr}</td>
            <td class="py-2.5 text-slate-400 leading-tight">${labStr}</td>
            <td class="py-2.5 ${seatsClass}">${seatsDisplay}</td>
            <td class="py-2.5 text-slate-400">${s.examDetail || "N/A"}</td>
          </tr>
        `;
        })
        .join("");
    } catch (err) {
      inspectorTableBody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-rose-400 font-medium">${err.message}</td></tr>`;
    }
  }

  closeInspectorBtn.addEventListener("click", () => courseInspectorModal.classList.add("hidden"));
  openHelpBtn.addEventListener("click", () => helpModal.classList.remove("hidden"));
  closeHelpBtn.addEventListener("click", () => helpModal.classList.add("hidden"));

  // -----------------------------------------------------------------------
  // Generate Combinations
  // -----------------------------------------------------------------------
  generateBtn.addEventListener("click", async () => {
    if (state.selectedCourses.length < 2) {
      showToast("Please add at least 2 courses to generate combinations.", "warning");
      return;
    }

    // Collect mandatory sections
    const mandTokens = [];
    const rawGlobalMand = mandatorySectionsInput.value.trim();
    if (rawGlobalMand) mandTokens.push(rawGlobalMand);

    document.querySelectorAll(".course-spec-mand").forEach((inp) => {
      const val = inp.value.trim();
      const code = inp.dataset.code;
      if (val) {
        mandTokens.push(`${code}:${val}`);
      }
    });

    // Collect skip times
    const skipTimes = [];
    document.querySelectorAll(".skip-slot-checkbox:checked").forEach((cb) => {
      skipTimes.push(cb.value);
    });
    const customSkip = customSkipTimesInput.value.trim();
    if (customSkip) {
      customSkip.split(/[,;]/).forEach((t) => {
        if (t.trim()) skipTimes.push(t.trim());
      });
    }

    // Collect faculty preferences
    const preferFaculty = preferredFacultyInput.value.trim() ? preferredFacultyInput.value.trim().split(/[,; ]+/).filter(Boolean) : null;
    const avoidFaculty = avoidFacultyInput.value.trim() ? avoidFacultyInput.value.trim().split(/[,; ]+/).filter(Boolean) : null;

    const payload = {
      courses: state.selectedCourses,
      only_open: onlyOpenCheckbox.checked,
      target_days: state.targetDays > 0 ? state.targetDays : null,
      exact_days: exactDaysCheckbox.checked && state.targetDays > 0,
      prefer_faculty: preferFaculty,
      avoid_faculty: avoidFaculty,
      mandatory_preferred_faculty: mandatoryFacultyCheckbox.checked,
      mandatory_sections: mandTokens.length > 0 ? mandTokens : null,
      skip_times: skipTimes.length > 0 ? skipTimes : null,
      sort_by: primarySortSelect.value,
      secondary_sort_by: secondarySortSelect.value !== "none" ? secondarySortSelect.value : null,
      max_results: parseInt(maxResultsSlider.value, 10) || 30,
    };

    state.lastPayload = payload;

    // Show Loading
    emptyState.classList.add("hidden");
    activeResultsView.classList.add("hidden");
    loadingState.classList.remove("hidden");
    generateBtn.disabled = true;
    generateBtn.classList.add("opacity-60");

    try {
      const resp = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Failed to calculate schedules");
      }

      state.currentCombinations = data.combinations || [];
      state.sortKeys = data.sort_keys || [];
      state.currentIndex = 0;

      // Update engine logs
      engineLogsPre.textContent = (data.logs || []).join("\n");

      if (state.currentCombinations.length === 0) {
        loadingState.classList.add("hidden");
        emptyState.classList.remove("hidden");
        emptyState.innerHTML = `
          <div class="w-16 h-16 rounded-2xl bg-rose-500/20 border border-rose-500/30 flex items-center justify-center mx-auto text-rose-400">
            <i data-lucide="alert-circle" class="w-8 h-8"></i>
          </div>
          <div class="max-w-md mx-auto">
            <h3 class="text-base font-semibold text-white">No Clash-Free Schedules Found</h3>
            <p class="text-xs text-slate-300 mt-1">
              Every combination of the selected course sections has a class-time, lab, or exam clash.
            </p>
            <div class="mt-4 p-3 rounded-xl bg-slate-900 border border-slate-700/60 text-left text-xs text-slate-300 space-y-1.5">
              <p class="font-semibold text-brand-300">💡 Tips to resolve clashes:</p>
              <ul class="list-disc list-inside space-y-1 text-slate-400">
                <li>Check if mandatory sections clash with each other.</li>
                <li>Turn off <b>"Only Open Seats"</b> or <b>"Exact Days"</b> filter.</li>
                <li>Uncheck some <b>"Skip Class Times"</b> slots.</li>
              </ul>
            </div>
          </div>
        `;
        lucide.createIcons();
        showToast("0 conflict-free schedules found.", "warning");
        return;
      }

      // Show Results
      loadingState.classList.add("hidden");
      activeResultsView.classList.remove("hidden");
      validCountBadge.textContent = `${data.total_valid.toLocaleString()} clash-free schedule${data.total_valid > 1 ? "s" : ""} found`;
      sortNotice.textContent = `(Sorted by: ${state.sortKeys.join(", ")})`;

      renderCurrentSchedule();
      showToast(`Found ${data.total_valid} valid schedules!`, "success");
    } catch (err) {
      loadingState.classList.add("hidden");
      emptyState.classList.remove("hidden");
      showToast(err.message, "error");
    } finally {
      generateBtn.disabled = false;
      generateBtn.classList.remove("opacity-60");
    }
  });

  // -----------------------------------------------------------------------
  // Render Timetable & Details for Selected Schedule
  // -----------------------------------------------------------------------
  function renderCurrentSchedule() {
    const combos = state.currentCombinations;
    if (!combos || combos.length === 0) return;

    const idx = state.currentIndex;
    const current = combos[idx];
    const total = combos.length;

    showingNotice.textContent = `Option ${idx + 1} of ${total}`;
    optionJumpInput.value = idx + 1;
    optionJumpInput.max = total;
    totalOptionsDisplay.textContent = `/ ${total}`;

    prevOptionBtn.disabled = idx === 0;
    nextOptionBtn.disabled = idx === total - 1;

    // Metrics
    metricGap.textContent = `${current.stats.gap} mins`;
    metricDays.textContent = `${current.stats.days} Days (${current.stats.days_list ? current.stats.days_list.join(", ") : ""})`;
    metricFaculty.textContent = `${current.stats.faculty_matches} match(es)`;

    // Render Weekly Grid
    const dayOrder = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"];

    // Build course to color index map
    const courseColorMap = {};
    state.selectedCourses.forEach((code, i) => {
      courseColorMap[code] = i % 7;
    });

    timetableGridBody.innerHTML = current.grid
      .map((row) => {
        const timeCell = `<td class="p-2 font-mono text-[11px] text-slate-400 whitespace-nowrap bg-slate-950/40">${row.time_label}</td>`;
        const dayCells = dayOrder
          .map((day) => {
            const items = row.days[day] || [];
            if (items.length === 0) {
              return `<td class="p-1 text-center border-l border-slate-800/60 bg-slate-900/30"></td>`;
            }
            const blockContent = items
              .map((it) => {
                const isLab = it.type === "Lab" || it.course.endsWith("L");
                const colorIdx = courseColorMap[it.course] !== undefined ? courseColorMap[it.course] : 0;
                return `
                <div class="timetable-block p-1.5 rounded-lg border text-[11px] font-medium leading-tight course-color-${colorIdx} mb-1">
                  <div class="flex items-center justify-between space-x-1">
                    <span class="font-bold font-mono">${it.course}</span>
                    <span class="text-[9px] px-1 rounded ${isLab ? "bg-amber-500/20 text-amber-300" : "bg-brand-500/20 text-brand-300"}">${isLab ? "LAB" : "SEC " + it.section}</span>
                  </div>
                  <div class="text-[10px] opacity-90 mt-0.5 flex items-center justify-between">
                    <span>${it.faculty || "TBA"}</span>
                    <span>${it.room || "TBA"}</span>
                  </div>
                </div>
              `;
              })
              .join("");
            return `<td class="p-1 border-l border-slate-800/60 align-top">${blockContent}</td>`;
          })
          .join("");

        return `<tr>${timeCell}${dayCells}</tr>`;
      })
      .join("");

    // Render Selected Sections Breakdown Table
    sectionsDetailsTableBody.innerHTML = current.sections
      .map((s) => {
        const seatsClass = s.remaining !== null && s.remaining <= 0 ? "text-rose-400" : "text-emerald-400";
        const seatsText = s.remaining !== null ? `${s.remaining} left` : "TBA";
        const examText = s.exam && s.exam.raw ? s.exam.raw : "N/A";
        return `
        <tr class="hover:bg-slate-800/40 transition">
          <td class="py-2 font-bold font-mono text-brand-300">${s.courseCode}</td>
          <td class="py-2 font-semibold text-slate-200">Sec ${s.sectionName}</td>
          <td class="py-2 text-slate-200">${s.faculty} ${s.is_pref_match ? '<span class="text-amber-400">★</span>' : ""}</td>
          <td class="py-2 text-slate-400">${s.room || "TBA"}</td>
          <td class="py-2 ${seatsClass}">${seatsText}</td>
          <td class="py-2 text-slate-400 font-mono text-[11px]">${examText}</td>
        </tr>
      `;
      })
      .join("");

    lucide.createIcons();
  }

  // Carousel controls
  prevOptionBtn.addEventListener("click", () => {
    if (state.currentIndex > 0) {
      state.currentIndex--;
      renderCurrentSchedule();
    }
  });

  nextOptionBtn.addEventListener("click", () => {
    if (state.currentIndex < state.currentCombinations.length - 1) {
      state.currentIndex++;
      renderCurrentSchedule();
    }
  });

  optionJumpInput.addEventListener("change", (e) => {
    const val = parseInt(e.target.value, 10);
    if (!isNaN(val) && val >= 1 && val <= state.currentCombinations.length) {
      state.currentIndex = val - 1;
      renderCurrentSchedule();
    } else {
      e.target.value = state.currentIndex + 1;
    }
  });

  // Keyboard navigation
  document.addEventListener("keydown", (e) => {
    if (state.currentCombinations.length > 0 && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
      if (e.key === "ArrowLeft" && state.currentIndex > 0) {
        state.currentIndex--;
        renderCurrentSchedule();
      } else if (e.key === "ArrowRight" && state.currentIndex < state.currentCombinations.length - 1) {
        state.currentIndex++;
        renderCurrentSchedule();
      }
    }
  });

  // -----------------------------------------------------------------------
  // Export Handlers
  // -----------------------------------------------------------------------
  exportPdfBtn.addEventListener("click", async () => {
    if (!state.lastPayload) return;
    try {
      exportPdfBtn.disabled = true;
      exportPdfBtn.classList.add("opacity-60");
      showToast("Generating PDF report...", "info");

      const resp = await fetch("/api/export/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state.lastPayload),
      });

      if (!resp.ok) throw new Error("PDF generation failed");
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${state.selectedCourses.join("_")}_schedules.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast("PDF downloaded successfully!", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      exportPdfBtn.disabled = false;
      exportPdfBtn.classList.remove("opacity-60");
    }
  });

  exportCsvBtn.addEventListener("click", async () => {
    if (!state.lastPayload) return;
    try {
      exportCsvBtn.disabled = true;
      exportCsvBtn.classList.add("opacity-60");
      showToast("Exporting CSV...", "info");

      const resp = await fetch("/api/export/csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state.lastPayload),
      });

      if (!resp.ok) throw new Error("CSV generation failed");
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${state.selectedCourses.join("_")}_schedules.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast("CSV exported successfully!", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      exportCsvBtn.disabled = false;
      exportCsvBtn.classList.remove("opacity-60");
    }
  });

  copyScheduleBtn.addEventListener("click", () => {
    const current = state.currentCombinations[state.currentIndex];
    if (!current) return;

    let text = `=== BracU Schedule (Option ${state.currentIndex + 1} of ${state.currentCombinations.length}) ===\n`;
    text += `Days: ${current.stats.days} (${current.stats.days_list.join(", ")}) | Idle Gap: ${current.stats.gap} mins\n\n`;
    current.sections.forEach((s) => {
      text += `${s.courseCode} (Sec ${s.sectionName}) - Faculty: ${s.faculty} | Room: ${s.room}\n`;
      if (s.theory_meetings.length > 0) {
        text += `  Class: ${s.theory_meetings.map((m) => `${m.day_abbr} ${m.start_str}-${m.end_str}`).join(", ")}\n`;
      }
      if (s.lab_meetings.length > 0) {
        text += `  Lab: ${s.lab_meetings.map((m) => `${m.day_abbr} ${m.start_str}-${m.end_str}`).join(", ")}\n`;
      }
      text += `  Exam: ${s.exam.raw || "N/A"}\n\n`;
    });

    navigator.clipboard.writeText(text).then(() => {
      copyBtnText.textContent = "Copied!";
      showToast("Schedule copied to clipboard!", "success");
      setTimeout(() => {
        copyBtnText.textContent = "Copy Text";
      }, 2000);
    });
  });

  printBtn.addEventListener("click", () => {
    window.print();
  });

  // Start app
  initTheme();
  fetchFeedInfo();
});
