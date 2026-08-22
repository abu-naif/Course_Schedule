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
    allTimeSlots: [],
    selectedCourses: [],
    skipTimes: [], // array of skip rule strings e.g. ["08:00 AM - 09:20 AM", "Sun 05:00 PM - 06:20 PM"]
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
  const courseFacultySlots = document.getElementById("courseFacultySlots");

  const onlyOpenCheckbox = document.getElementById("onlyOpenCheckbox");
  const targetDayButtons = document.querySelectorAll(".target-day-btn");
  const targetDaysValue = document.getElementById("targetDaysValue");
  const exactDaysCheckbox = document.getElementById("exactDaysCheckbox");
  const mandatorySectionsInput = document.getElementById("mandatorySectionsInput");
  const preferredFacultyInput = document.getElementById("preferredFacultyInput");
  const preferredFacultySuggestions = document.getElementById("preferredFacultySuggestions");
  const mandatoryFacultyCheckbox = document.getElementById("mandatoryFacultyCheckbox");
  const avoidFacultyInput = document.getElementById("avoidFacultyInput");
  const avoidFacultySuggestions = document.getElementById("avoidFacultySuggestions");

  const skipDaySelect = document.getElementById("skipDaySelect");
  const customSkipTimesInput = document.getElementById("customSkipTimesInput");
  const skipTimesSuggestions = document.getElementById("skipTimesSuggestions");
  const addSkipTimeBtn = document.getElementById("addSkipTimeBtn");
  const activeSkipRulesCount = document.getElementById("activeSkipRulesCount");
  const noSkipRulesPlaceholder = document.getElementById("noSkipRulesPlaceholder");
  const skipRulesChipsList = document.getElementById("skipRulesChipsList");
  const quickSkipPresets = document.querySelectorAll(".quick-skip-preset");

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
  const sidebarPanel = document.getElementById("sidebarPanel");
  const resultsPanel = document.getElementById("resultsPanel");
  const toggleSidebarBtn = document.getElementById("toggleSidebarBtn");
  const toggleFullscreenBtn = document.getElementById("toggleFullscreenBtn");
  const toggleFullscreenText = document.getElementById("toggleFullscreenText");
  const showSidebarFab = document.getElementById("showSidebarFab");

  const optionJumpInput = document.getElementById("optionJumpInput");
  const totalOptionsDisplay = document.getElementById("totalOptionsDisplay");

  const metricGap = document.getElementById("metricGap");
  const metricDays = document.getElementById("metricDays");
  const metricFaculty = document.getElementById("metricFaculty");
  const timetableGrid = document.getElementById("timetableGrid");
  const timetableGridBody = document.getElementById("timetableGridBody");
  const sectionsDetailsTableBody = document.getElementById("sectionsDetailsTableBody");
  const examsDetailsTableBody = document.getElementById("examsDetailsTableBody");
  const engineLogsPre = document.getElementById("engineLogsPre");

  const routineScrollContainer = document.getElementById("routineScrollContainer");
  const routineZoomWrapper = document.getElementById("routineZoomWrapper");
  const routineZoomOutBtn = document.getElementById("routineZoomOutBtn");
  const routineZoomInBtn = document.getElementById("routineZoomInBtn");
  const routineZoomSelect = document.getElementById("routineZoomSelect");
  const routineZoomResetBtn = document.getElementById("routineZoomResetBtn");

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
        state.allTimeSlots = data.time_slots || [];
      } else {
        // Re-fetch info to update course list
        const infoResp = await fetch("/api/info");
        const infoData = await infoResp.json();
        state.allCourses = infoData.courses || [];
        state.allFaculties = infoData.faculties || [];
        state.allTimeSlots = infoData.time_slots || [];
      }

      const totalSec = data.total_sections || 0;
      feedStatusText.textContent = `Synced (${totalSec.toLocaleString()} sections)`;
      if (state.selectedCourses.length > 0) {
        renderSelectedCourses();
      }
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

  // -----------------------------------------------------------------------
  // Faculty Autocomplete & Suggestions Engine
  // -----------------------------------------------------------------------

  /**
   * Helper to parse comma/space separated input tokens and identify active token
   */
  function getActiveTokenInfo(inputElement) {
    const val = inputElement.value || "";
    const cursorPos =
      inputElement.selectionStart !== null && inputElement.selectionStart !== undefined
        ? inputElement.selectionStart
        : val.length;
    const textBeforeCursor = val.slice(0, cursorPos);
    const lastCommaIndex = textBeforeCursor.lastIndexOf(",");

    const activeTokenRaw = (lastCommaIndex === -1 ? textBeforeCursor : textBeforeCursor.slice(lastCommaIndex + 1)).trim();
    const activeToken = activeTokenRaw.toUpperCase();

    const allTokens = val
      .split(/[,;]+/)
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean);

    return {
      val,
      cursorPos,
      activeToken,
      allTokens,
    };
  }

  /**
   * Toggles or inserts a faculty initial cleanly into the input
   */
  function toggleFacultyToken(inputElement, facInitial) {
    const info = getActiveTokenInfo(inputElement);
    const targetFac = facInitial.trim().toUpperCase();
    let currentTokens = inputElement.value
      .split(/[,;]+/)
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean);

    if (currentTokens.includes(targetFac)) {
      // Toggle off: remove
      currentTokens = currentTokens.filter((t) => t !== targetFac);
    } else {
      // If user was typing a partial token that matches the beginning of targetFac, replace it
      if (info.activeToken && info.activeToken !== targetFac && targetFac.startsWith(info.activeToken)) {
        const partialIdx = currentTokens.indexOf(info.activeToken);
        if (partialIdx !== -1) {
          currentTokens[partialIdx] = targetFac;
        } else {
          currentTokens.push(targetFac);
        }
      } else {
        currentTokens.push(targetFac);
      }
    }

    // Deduplicate
    currentTokens = Array.from(new Set(currentTokens));

    inputElement.value = currentTokens.length > 0 ? currentTokens.join(", ") + ", " : "";
    inputElement.focus();
    inputElement.dispatchEvent(new Event("input", { bubbles: true }));
  }

  /**
   * Setup interactive faculty suggestions dropdown for an input element
   * @param {HTMLInputElement} inputEl
   * @param {HTMLElement} dropdownEl
   * @param {string|null} courseCode - If specified, scopes to course's specific faculties
   */
  function setupFacultyAutocomplete(inputEl, dropdownEl, courseCode = null) {
    if (!inputEl || !dropdownEl) return;
    let highlightedIndex = -1;

    function getFacultyData() {
      if (courseCode) {
        const cObj = state.allCourses.find((c) => c.code.toUpperCase() === courseCode.toUpperCase());
        if (cObj) {
          return {
            faculties: cObj.faculties || [],
            sections: cObj.faculty_sections || {},
            title: cObj.title || "",
            isCourseSpecific: true,
          };
        }
        return { faculties: [], sections: {}, title: "", isCourseSpecific: true };
      }

      // Global faculty list - prioritize faculties who teach selected courses
      const selectedCourseFaculties = new Set();
      const facCourseMap = {};
      state.selectedCourses.forEach((code) => {
        const c = state.allCourses.find((x) => x.code === code);
        if (c && c.faculties) {
          c.faculties.forEach((f) => {
            selectedCourseFaculties.add(f);
            if (!facCourseMap[f]) facCourseMap[f] = [];
            if (!facCourseMap[f].includes(code)) facCourseMap[f].push(code);
          });
        }
      });

      return {
        faculties: state.allFaculties || [],
        sections: {},
        facCourseMap,
        selectedCourseFaculties,
        isCourseSpecific: false,
      };
    }

    function renderSuggestions() {
      const { faculties, sections, facCourseMap, selectedCourseFaculties, isCourseSpecific } = getFacultyData();
      const tokenInfo = getActiveTokenInfo(inputEl);
      const query = tokenInfo.activeToken;
      const currentSelected = new Set(tokenInfo.allTokens);

      if (!faculties || faculties.length === 0) {
        if (isCourseSpecific) {
          dropdownEl.innerHTML = `
            <div class="p-3 text-center text-xs text-slate-400">
              <p class="font-medium text-slate-300">No individual faculties listed</p>
              <p class="text-[10px] text-slate-500 mt-0.5">Faculty may be TBA in current USIS course feed.</p>
            </div>`;
          dropdownEl.classList.remove("hidden");
        } else {
          dropdownEl.classList.add("hidden");
        }
        return;
      }

      // Filter faculties
      let matches = [];
      if (!query) {
        matches = [...faculties];
      } else {
        const startsWith = faculties.filter((f) => f.toUpperCase().startsWith(query));
        const contains = faculties.filter((f) => !f.toUpperCase().startsWith(query) && f.toUpperCase().includes(query));
        matches = [...startsWith, ...contains];
      }

      // For global input: prioritize faculties from selected courses
      if (!isCourseSpecific && selectedCourseFaculties && selectedCourseFaculties.size > 0) {
        matches.sort((a, b) => {
          const aIn = selectedCourseFaculties.has(a) ? 0 : 1;
          const bIn = selectedCourseFaculties.has(b) ? 0 : 1;
          if (aIn !== bIn) return aIn - bIn;
          return a.localeCompare(b);
        });
      }

      // Limit to 25 items
      const displayMatches = matches.slice(0, 25);

      if (displayMatches.length === 0) {
        dropdownEl.innerHTML = `
          <div class="p-2.5 text-center text-xs text-slate-400 italic">
            No faculties found matching <span class="font-mono text-purple-300 font-semibold">"${query}"</span>
          </div>`;
        dropdownEl.classList.remove("hidden");
        highlightedIndex = -1;
        return;
      }

      const headerText = isCourseSpecific
        ? `<span>Available Faculty for <span class="font-mono font-bold text-purple-300">${courseCode}</span> (${faculties.length})</span>`
        : `<span>Faculty Initials (${matches.length} match${matches.length === 1 ? "" : "es"})</span>`;

      const headerHtml = `
        <div class="px-3 py-1.5 bg-purple-950/60 border-b border-purple-800/40 text-[10px] font-semibold text-purple-300 flex items-center justify-between sticky top-0 backdrop-blur z-10">
          ${headerText}
          <span class="text-[9px] text-slate-400 font-normal">Click or Enter to toggle</span>
        </div>`;

      const itemsHtml = displayMatches
        .map((fac, idx) => {
          const isSelected = currentSelected.has(fac);
          const secList = sections && sections[fac] ? sections[fac] : [];
          const secStr = secList.length > 0 ? `Sec ${secList.join(", ")}` : "";
          const courseList = facCourseMap && facCourseMap[fac] ? facCourseMap[fac] : [];
          const courseStr = courseList.length > 0 ? courseList.join(", ") : "";

          const badgeHtml = isSelected
            ? `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">✓ Added</span>`
            : `<span class="text-[10px] text-slate-400 opacity-0 group-hover:opacity-100 transition font-medium text-purple-300">+ Add</span>`;

          const detailsHtml =
            isCourseSpecific && secStr
              ? `<span class="text-[10px] text-slate-400 font-mono">${secStr}</span>`
              : !isCourseSpecific && courseStr
              ? `<span class="text-[10px] text-purple-400/80 font-mono">${courseStr}</span>`
              : "";

          return `
            <div class="fac-suggestion-item group px-3 py-2 hover:bg-purple-900/40 cursor-pointer flex items-center justify-between transition ${idx === highlightedIndex ? "bg-purple-900/50" : ""}" data-faculty="${fac}" data-index="${idx}">
              <div class="flex items-center space-x-2.5">
                <div class="w-6 h-6 rounded-md bg-purple-500/20 border border-purple-500/30 flex items-center justify-center font-mono font-bold text-xs text-purple-200">
                  ${fac.slice(0, 2)}
                </div>
                <div>
                  <div class="flex items-center space-x-2">
                    <span class="font-mono font-bold text-xs text-purple-200">${fac}</span>
                    ${detailsHtml}
                  </div>
                </div>
              </div>
              <div>${badgeHtml}</div>
            </div>`;
        })
        .join("");

      dropdownEl.innerHTML = headerHtml + itemsHtml;
      dropdownEl.classList.remove("hidden");

      // Attach click listeners
      dropdownEl.querySelectorAll(".fac-suggestion-item").forEach((item) => {
        item.addEventListener("mousedown", (e) => {
          e.preventDefault(); // Prevent input blur before click
          const fac = item.dataset.faculty;
          toggleFacultyToken(inputEl, fac);
          renderSuggestions();
        });
      });
    }

    inputEl.addEventListener("focus", () => {
      renderSuggestions();
    });

    inputEl.addEventListener("input", () => {
      highlightedIndex = -1;
      renderSuggestions();
    });

    inputEl.addEventListener("keydown", (e) => {
      if (dropdownEl.classList.contains("hidden")) {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
          renderSuggestions();
        }
        return;
      }

      const items = dropdownEl.querySelectorAll(".fac-suggestion-item");
      if (items.length === 0) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        highlightedIndex = (highlightedIndex + 1) % items.length;
        updateHighlight(items);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        highlightedIndex = (highlightedIndex - 1 + items.length) % items.length;
        updateHighlight(items);
      } else if (e.key === "Enter" || e.key === "Tab") {
        if (highlightedIndex >= 0 && highlightedIndex < items.length) {
          e.preventDefault();
          const selectedFac = items[highlightedIndex].dataset.faculty;
          toggleFacultyToken(inputEl, selectedFac);
          renderSuggestions();
        } else if (items.length > 0 && inputEl.value.trim().length > 0 && e.key === "Enter") {
          e.preventDefault();
          const firstFac = items[0].dataset.faculty;
          toggleFacultyToken(inputEl, firstFac);
          renderSuggestions();
        }
      } else if (e.key === "Escape") {
        dropdownEl.classList.add("hidden");
      }
    });

    function updateHighlight(items) {
      items.forEach((it, idx) => {
        if (idx === highlightedIndex) {
          it.classList.add("bg-purple-900/50");
          it.scrollIntoView({ block: "nearest" });
        } else {
          it.classList.remove("bg-purple-900/50");
        }
      });
    }
  }

  // -----------------------------------------------------------------------
  // Skip Times Autocomplete & Filter Management Engine
  // -----------------------------------------------------------------------

  const DEFAULT_BRACU_TIME_SLOTS = [
    { label: "08:00 AM - 09:20 AM", type: "Theory Slot 1" },
    { label: "08:00 AM - 10:50 AM", type: "Lab Morning" },
    { label: "09:30 AM - 10:50 AM", type: "Theory Slot 2" },
    { label: "11:00 AM - 12:20 PM", type: "Theory Slot 3" },
    { label: "11:00 AM - 01:50 PM", type: "Lab Midday" },
    { label: "12:30 PM - 01:50 PM", type: "Theory Slot 4" },
    { label: "02:00 PM - 03:20 PM", type: "Theory Slot 5" },
    { label: "02:00 PM - 04:50 PM", type: "Lab Afternoon" },
    { label: "03:30 PM - 04:50 PM", type: "Theory Slot 6" },
    { label: "05:00 PM - 06:20 PM", type: "Theory Slot 7 (Evening)" },
    { label: "06:30 PM - 07:50 PM", type: "Theory Slot 8 (Night)" },
    { label: "08:00 PM - 09:20 PM", type: "Theory Slot 9 (Late Night)" },
  ];

  function parseSkipRule(ruleStr) {
    const clean = ruleStr.trim();
    const firstWord = clean.split(/\s+/)[0].toUpperCase();
    const dayMap = {
      SUN: "Sunday",
      SUNDAY: "Sunday",
      MON: "Monday",
      MONDAY: "Monday",
      TUE: "Tuesday",
      TUESDAY: "Tuesday",
      WED: "Wednesday",
      WEDNESDAY: "Wednesday",
      THU: "Thursday",
      THURSDAY: "Thursday",
      FRI: "Friday",
      FRIDAY: "Friday",
      SAT: "Saturday",
      SATURDAY: "Saturday",
    };
    if (dayMap[firstWord]) {
      const timePart = clean.slice(firstWord.length).trim();
      return {
        raw: clean,
        dayKey: firstWord.slice(0, 3).charAt(0).toUpperCase() + firstWord.slice(1, 3).toLowerCase(),
        dayLabel: dayMap[firstWord],
        time: timePart,
        displayText: `${dayMap[firstWord]} • ${timePart}`,
      };
    }
    return {
      raw: clean,
      dayKey: "ALL",
      dayLabel: "All Days",
      time: clean,
      displayText: `All Days • ${clean}`,
    };
  }

  function addSkipRule(ruleStr) {
    const clean = ruleStr.trim();
    if (!clean) return;
    if (!state.skipTimes.includes(clean)) {
      state.skipTimes.push(clean);
      renderSkipRules();
    }
  }

  function removeSkipRule(ruleStr) {
    state.skipTimes = state.skipTimes.filter((r) => r !== ruleStr);
    renderSkipRules();
  }

  function toggleSkipRule(ruleStr) {
    if (state.skipTimes.includes(ruleStr)) {
      removeSkipRule(ruleStr);
    } else {
      addSkipRule(ruleStr);
    }
  }

  function renderSkipRules() {
    if (!skipRulesChipsList || !noSkipRulesPlaceholder) return;

    if (state.skipTimes.length === 0) {
      noSkipRulesPlaceholder.classList.remove("hidden");
      skipRulesChipsList.innerHTML = "";
      if (activeSkipRulesCount) activeSkipRulesCount.classList.add("hidden");
    } else {
      noSkipRulesPlaceholder.classList.add("hidden");
      if (activeSkipRulesCount) {
        activeSkipRulesCount.textContent = `${state.skipTimes.length} active`;
        activeSkipRulesCount.classList.remove("hidden");
      }

      skipRulesChipsList.innerHTML = state.skipTimes
        .map((r) => {
          const parsed = parseSkipRule(r);
          return `
          <div class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-medium shadow-sm transition hover:bg-rose-500/20">
            <i data-lucide="clock" class="w-3.5 h-3.5 text-rose-400"></i>
            <span class="font-mono text-[11px] font-semibold">${parsed.displayText}</span>
            <button type="button" class="remove-skip-rule-btn p-0.5 hover:text-white transition ml-1" data-rule="${r}" title="Remove rule">
              <i data-lucide="x" class="w-3.5 h-3.5"></i>
            </button>
          </div>
        `;
        })
        .join("");

      lucide.createIcons();

      skipRulesChipsList.querySelectorAll(".remove-skip-rule-btn").forEach((btn) => {
        btn.addEventListener("click", () => removeSkipRule(btn.dataset.rule));
      });
    }

    // Update Quick Presets visual state
    quickSkipPresets.forEach((btn) => {
      const timeVal = btn.dataset.time;
      const dayVal = skipDaySelect ? skipDaySelect.value : "ALL";
      const expectedRule = dayVal === "ALL" ? timeVal : `${dayVal} ${timeVal}`;
      const isExactActive = state.skipTimes.includes(expectedRule);
      const isAnyActive = state.skipTimes.some((r) => r.includes(timeVal));

      const statusSpan = btn.querySelector(".preset-status");
      if (isExactActive || isAnyActive) {
        btn.classList.add("bg-rose-950/40", "border-rose-500/60", "text-rose-200");
        btn.classList.remove("bg-slate-900", "border-slate-700/70", "text-slate-300");
        if (statusSpan) statusSpan.textContent = "✓ Active";
      } else {
        btn.classList.remove("bg-rose-950/40", "border-rose-500/60", "text-rose-200");
        btn.classList.add("bg-slate-900", "border-slate-700/70", "text-slate-300");
        if (statusSpan) statusSpan.textContent = "+ Skip";
      }
    });
  }

  function setupSkipTimesAutocomplete() {
    if (!customSkipTimesInput || !skipTimesSuggestions) return;
    let highlightedIndex = -1;

    function getTimeSlotsData() {
      if (state.allTimeSlots && state.allTimeSlots.length > 0) {
        return state.allTimeSlots;
      }
      return DEFAULT_BRACU_TIME_SLOTS;
    }

    function renderSuggestions() {
      const slots = getTimeSlotsData();
      const query = customSkipTimesInput.value.trim().toUpperCase();
      const dayVal = skipDaySelect ? skipDaySelect.value : "ALL";
      const dayLabel = skipDaySelect ? skipDaySelect.options[skipDaySelect.selectedIndex].text : "All Days";

      let matches = [];
      if (!query) {
        matches = [...slots];
      } else {
        matches = slots.filter((s) => {
          const l = (s.label || "").toUpperCase();
          const t = (s.type || "").toUpperCase();
          return l.includes(query) || t.includes(query);
        });
      }

      if (matches.length === 0) {
        skipTimesSuggestions.innerHTML = `
          <div class="p-2.5 text-center text-xs text-slate-400 italic">
            No standard time slots matching "${customSkipTimesInput.value.trim()}"
          </div>`;
        skipTimesSuggestions.classList.remove("hidden");
        highlightedIndex = -1;
        return;
      }

      const headerHtml = `
        <div class="px-3 py-1.5 bg-rose-950/60 border-b border-rose-800/40 text-[10px] font-semibold text-rose-300 flex items-center justify-between sticky top-0 backdrop-blur z-10">
          <span>Targeting: <span class="text-white font-bold">${dayLabel}</span></span>
          <span class="text-[9px] text-slate-400 font-normal">Click or Enter to add</span>
        </div>`;

      const itemsHtml = matches
        .map((s, idx) => {
          const timeLabel = s.label;
          const targetRule = dayVal === "ALL" ? timeLabel : `${dayVal} ${timeLabel}`;
          const isAdded = state.skipTimes.includes(targetRule);
          const typeStr = s.type || "Class";
          const countStr = s.count ? `${s.count} secs` : "";

          const badgeHtml = isAdded
            ? `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-rose-500/20 text-rose-300 border border-rose-500/30">✓ Active</span>`
            : `<span class="text-[10px] text-slate-400 opacity-0 group-hover:opacity-100 transition font-medium text-rose-300">+ Skip</span>`;

          return `
            <div class="time-suggestion-item group px-3 py-2 hover:bg-rose-900/40 cursor-pointer flex items-center justify-between transition ${idx === highlightedIndex ? "bg-rose-900/50" : ""}" data-time="${timeLabel}" data-index="${idx}">
              <div class="flex items-center space-x-2.5">
                <div class="w-6 h-6 rounded-md bg-rose-500/20 border border-rose-500/30 flex items-center justify-center text-rose-300">
                  <i data-lucide="clock" class="w-3.5 h-3.5"></i>
                </div>
                <div>
                  <div class="flex items-center space-x-2">
                    <span class="font-mono font-bold text-xs text-rose-200">${timeLabel}</span>
                    <span class="text-[10px] text-slate-400">${typeStr} ${countStr ? `(${countStr})` : ""}</span>
                  </div>
                </div>
              </div>
              <div>${badgeHtml}</div>
            </div>`;
        })
        .join("");

      skipTimesSuggestions.innerHTML = headerHtml + itemsHtml;
      skipTimesSuggestions.classList.remove("hidden");
      lucide.createIcons();

      // Attach click listeners
      skipTimesSuggestions.querySelectorAll(".time-suggestion-item").forEach((item) => {
        item.addEventListener("mousedown", (e) => {
          e.preventDefault();
          const timeLabel = item.dataset.time;
          const currentDay = skipDaySelect ? skipDaySelect.value : "ALL";
          const rule = currentDay === "ALL" ? timeLabel : `${currentDay} ${timeLabel}`;
          toggleSkipRule(rule);
          customSkipTimesInput.value = "";
          renderSuggestions();
        });
      });
    }

    customSkipTimesInput.addEventListener("focus", () => {
      renderSuggestions();
    });

    customSkipTimesInput.addEventListener("input", () => {
      highlightedIndex = -1;
      renderSuggestions();
    });

    if (skipDaySelect) {
      skipDaySelect.addEventListener("change", () => {
        renderSkipRules();
        if (!skipTimesSuggestions.classList.contains("hidden")) {
          renderSuggestions();
        }
      });
    }

    customSkipTimesInput.addEventListener("keydown", (e) => {
      if (skipTimesSuggestions.classList.contains("hidden")) {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
          renderSuggestions();
        }
        return;
      }

      const items = skipTimesSuggestions.querySelectorAll(".time-suggestion-item");
      if (items.length === 0) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        highlightedIndex = (highlightedIndex + 1) % items.length;
        updateTimeHighlight(items);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        highlightedIndex = (highlightedIndex - 1 + items.length) % items.length;
        updateTimeHighlight(items);
      } else if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        const currentDay = skipDaySelect ? skipDaySelect.value : "ALL";
        if (highlightedIndex >= 0 && highlightedIndex < items.length) {
          const timeLabel = items[highlightedIndex].dataset.time;
          const rule = currentDay === "ALL" ? timeLabel : `${currentDay} ${timeLabel}`;
          toggleSkipRule(rule);
        } else if (items.length > 0) {
          const firstTime = items[0].dataset.time;
          const rule = currentDay === "ALL" ? firstTime : `${currentDay} ${firstTime}`;
          toggleSkipRule(rule);
        } else if (customSkipTimesInput.value.trim()) {
          const rawVal = customSkipTimesInput.value.trim();
          const rule = currentDay === "ALL" ? rawVal : `${currentDay} ${rawVal}`;
          addSkipRule(rule);
        }
        customSkipTimesInput.value = "";
        renderSuggestions();
      } else if (e.key === "Escape") {
        skipTimesSuggestions.classList.add("hidden");
      }
    });

    function updateTimeHighlight(items) {
      items.forEach((it, idx) => {
        if (idx === highlightedIndex) {
          it.classList.add("bg-rose-900/50");
          it.scrollIntoView({ block: "nearest" });
        } else {
          it.classList.remove("bg-rose-900/50");
        }
      });
    }

    if (addSkipTimeBtn) {
      addSkipTimeBtn.addEventListener("click", () => {
        const val = customSkipTimesInput.value.trim();
        const currentDay = skipDaySelect ? skipDaySelect.value : "ALL";
        if (val) {
          val.split(/[,;]/).forEach((t) => {
            if (t.trim()) {
              const rule = currentDay === "ALL" ? t.trim() : `${currentDay} ${t.trim()}`;
              addSkipRule(rule);
            }
          });
          customSkipTimesInput.value = "";
          skipTimesSuggestions.classList.add("hidden");
        } else {
          renderSuggestions();
          customSkipTimesInput.focus();
        }
      });
    }

    quickSkipPresets.forEach((btn) => {
      btn.addEventListener("click", () => {
        const timeVal = btn.dataset.time;
        const currentDay = skipDaySelect ? skipDaySelect.value : "ALL";
        const rule = currentDay === "ALL" ? timeVal : `${currentDay} ${timeVal}`;
        toggleSkipRule(rule);
      });
    });
  }

  // Global click to close any open suggestions dropdown
  document.addEventListener("click", (e) => {
    document
      .querySelectorAll(
        ".faculty-suggestions-dropdown, #preferredFacultySuggestions, #avoidFacultySuggestions, #skipTimesSuggestions"
      )
      .forEach((dd) => {
        const container = dd.parentElement;
        if (container && !container.contains(e.target)) {
          dd.classList.add("hidden");
        }
      });
  });

  // Initialize Global Preferred and Avoid Faculty autocomplete
  if (preferredFacultyInput && preferredFacultySuggestions) {
    setupFacultyAutocomplete(preferredFacultyInput, preferredFacultySuggestions, null);
  }
  if (avoidFacultyInput && avoidFacultySuggestions) {
    setupFacultyAutocomplete(avoidFacultyInput, avoidFacultySuggestions, null);
  }

  // Initialize Skip Times Engine
  setupSkipTimesAutocomplete();
  renderSkipRules();

  function renderSelectedCourses() {
    selectedCoursesCount.textContent = `${state.selectedCourses.length} course${state.selectedCourses.length === 1 ? "" : "s"}`;
    if (state.selectedCourses.length === 0) {
      selectedCoursesContainer.innerHTML = "";
      selectedCoursesContainer.appendChild(noCoursesPlaceholder);
      noCoursesPlaceholder.classList.remove("hidden");
      if (courseMandatorySlots) courseMandatorySlots.innerHTML = "";
      if (courseFacultySlots)
        courseFacultySlots.innerHTML = `<p class="text-[11px] text-slate-500 italic">Add courses above to set specific faculty preferences per course.</p>`;
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

    // Save existing mandatory section values before re-rendering
    const savedMandatory = {};
    if (courseMandatorySlots) {
      courseMandatorySlots.querySelectorAll(".course-spec-mand").forEach((inp) => {
        if (inp.dataset.code) savedMandatory[inp.dataset.code] = inp.value;
      });
      courseMandatorySlots.innerHTML = state.selectedCourses
        .map(
          (code) => `
          <div class="flex items-center space-x-2 text-[11px]">
            <span class="w-16 font-mono font-semibold text-brand-300 shrink-0">${code}:</span>
            <input type="text" class="course-spec-mand px-2 py-1 bg-slate-900 border border-slate-700 rounded text-xs text-slate-100 placeholder-slate-500 w-full" data-code="${code}" placeholder="e.g. 01, 02 (optional)" value="${savedMandatory[code] || ""}">
          </div>
        `
        )
        .join("");
    }

    // Save existing faculty preference values before re-rendering
    const savedFaculty = {};
    if (courseFacultySlots) {
      courseFacultySlots.querySelectorAll(".course-spec-faculty").forEach((inp) => {
        if (inp.dataset.code) savedFaculty[inp.dataset.code] = inp.value;
      });

      courseFacultySlots.innerHTML = state.selectedCourses
        .map((code) => {
          const cObj = state.allCourses.find((c) => c.code.toUpperCase() === code.toUpperCase());
          const facCount = cObj && cObj.faculties ? cObj.faculties.length : 0;
          const facHint = facCount > 0 ? `${facCount} faculties available` : "Click for suggestions";

          return `
          <div class="faculty-slot-item relative">
            <div class="flex items-center space-x-2 text-[11px]">
              <span class="w-16 font-mono font-semibold text-purple-300 shrink-0">${code}:</span>
              <div class="relative flex-1">
                <input
                  type="text"
                  class="course-spec-faculty px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-100 placeholder-slate-500 w-full focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition"
                  data-code="${code}"
                  placeholder="e.g. AIB, TAZ (${facHint})"
                  autocomplete="off"
                  value="${savedFaculty[code] || ""}"
                >
                <div class="faculty-suggestions-dropdown hidden absolute top-full left-0 right-0 mt-1 max-h-52 overflow-y-auto bg-slate-900/95 backdrop-blur-md border border-purple-500/30 rounded-xl shadow-2xl z-50 divide-y divide-slate-800/80"></div>
              </div>
            </div>
          </div>
        `;
        })
        .join("");

      // Setup autocomplete for each course slot
      courseFacultySlots.querySelectorAll(".faculty-slot-item").forEach((item) => {
        const inputEl = item.querySelector(".course-spec-faculty");
        const dropdownEl = item.querySelector(".faculty-suggestions-dropdown");
        const code = inputEl.dataset.code;
        if (inputEl && dropdownEl && code) {
          setupFacultyAutocomplete(inputEl, dropdownEl, code);
        }
      });
    }
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
    state.skipTimes = [];
    if (skipDaySelect) skipDaySelect.value = "ALL";
    if (customSkipTimesInput) customSkipTimesInput.value = "";
    renderSkipRules();
    document.querySelectorAll(".course-spec-faculty").forEach((inp) => (inp.value = ""));
    document.querySelectorAll(".course-spec-mand").forEach((inp) => (inp.value = ""));
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
    const skipTimes = [...state.skipTimes];
    const customSkip = customSkipTimesInput ? customSkipTimesInput.value.trim() : "";
    if (customSkip) {
      const currentDay = skipDaySelect ? skipDaySelect.value : "ALL";
      customSkip.split(/[,;]/).forEach((t) => {
        if (t.trim()) {
          const rule = currentDay === "ALL" ? t.trim() : `${currentDay} ${t.trim()}`;
          if (!skipTimes.includes(rule)) skipTimes.push(rule);
        }
      });
    }

    // Collect faculty preferences (Global + Per-Course)
    const preferFacultyTokens = [];
    if (preferredFacultyInput && preferredFacultyInput.value.trim()) {
      preferredFacultyInput.value.trim().split(/[,; ]+/).forEach((tok) => {
        if (tok.trim()) preferFacultyTokens.push(tok.trim());
      });
    }
    document.querySelectorAll(".course-spec-faculty").forEach((inp) => {
      const code = inp.dataset.code;
      const val = inp.value.trim();
      if (val) {
        val.split(/[,; ]+/).forEach((init) => {
          if (init.trim()) {
            preferFacultyTokens.push(`${code}:${init.trim().toUpperCase()}`);
          }
        });
      }
    });

    const avoidFacultyTokens = avoidFacultyInput && avoidFacultyInput.value.trim() ? avoidFacultyInput.value.trim().split(/[,; ]+/).filter(Boolean) : null;

    const payload = {
      courses: state.selectedCourses,
      only_open: onlyOpenCheckbox.checked,
      target_days: state.targetDays > 0 ? state.targetDays : null,
      exact_days: exactDaysCheckbox.checked && state.targetDays > 0,
      prefer_faculty: preferFacultyTokens.length > 0 ? preferFacultyTokens : null,
      avoid_faculty: avoidFacultyTokens,
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

    if (showingNotice) showingNotice.textContent = `Option ${idx + 1} of ${total}`;
    if (optionJumpInput) {
      optionJumpInput.value = idx + 1;
      optionJumpInput.max = total;
    }
    if (totalOptionsDisplay) totalOptionsDisplay.textContent = `/ ${total}`;

    if (prevOptionBtn) prevOptionBtn.disabled = idx === 0;
    if (nextOptionBtn) nextOptionBtn.disabled = idx === total - 1;

    // Metrics
    if (metricGap) metricGap.textContent = `${current.stats.gap} mins`;
    if (metricDays) metricDays.textContent = `${current.stats.days} Days (${current.stats.days_list ? current.stats.days_list.join(", ") : ""})`;
    if (metricFaculty) metricFaculty.textContent = `${current.stats.faculty_matches} match(es)`;

    // Render Weekly Routine Matrix (Matching PDF Layout)
    const dayOrder = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"];

    // Build course to color index map
    const courseColorMap = {};
    state.selectedCourses.forEach((code, i) => {
      courseColorMap[code] = i % 7;
    });

    if (timetableGridBody) {
      timetableGridBody.innerHTML = current.grid
        .map((row, rIdx) => {
          const bgClass = rIdx % 2 === 0 ? "bg-slate-900/60" : "bg-slate-950/40";
          const timeCell = `<td class="p-2 font-bold font-mono text-[10.5px] text-slate-300 border-r border-slate-700 whitespace-nowrap bg-[#16324f]/30 leading-snug">${row.time_label}</td>`;
          const dayCells = dayOrder
            .map((day) => {
              const items = row.days[day] || [];
              if (items.length === 0) {
                return `<td class="p-1 border-r border-slate-800/80 text-center"></td>`;
              }
              const blockContent = items
                .map((it) => {
                  const isLab = it.type === "Lab" || it.course.endsWith("L");
                  const colorIdx = courseColorMap[it.course] !== undefined ? courseColorMap[it.course] : 0;
                  return `
                  <div class="timetable-block p-1.5 rounded-lg border text-xs font-medium leading-snug course-color-${colorIdx} mb-1 shadow-sm">
                    <div class="flex items-center justify-between space-x-1">
                      <span class="font-bold font-mono text-xs">${it.course}</span>
                      <span class="text-[9px] px-1.5 py-0.2 rounded font-semibold ${isLab ? "bg-amber-500/20 text-amber-300 border border-amber-500/30" : "bg-brand-500/20 text-brand-300 border border-brand-500/30"}">
                        ${isLab ? "LAB" : "Sec " + it.section}
                      </span>
                    </div>
                    <div class="text-[10px] opacity-90 mt-0.5 flex items-center justify-between">
                      <span class="font-medium text-slate-300">${it.faculty || "TBA"}</span>
                      <span class="font-mono text-slate-400">🏢 ${it.room || "TBA"}</span>
                    </div>
                  </div>
                `;
                })
                .join("");
              return `<td class="p-1 border-r border-slate-800/80 align-top">${blockContent}</td>`;
            })
            .join("");

          return `<tr class="${bgClass}">${timeCell}${dayCells}</tr>`;
        })
        .join("");
    }

    // Render Section Details Table
    if (sectionsDetailsTableBody) {
      sectionsDetailsTableBody.innerHTML = current.sections
        .map((s, rIdx) => {
          const bgClass = rIdx % 2 === 0 ? "bg-slate-900/40" : "bg-slate-800/20";
          const courseName = s.courseCode || s.course_code || s.course || "-";
          const cap = s.capacity !== undefined && s.capacity !== null ? s.capacity : null;
          const cons = s.consumedSeat !== undefined && s.consumedSeat !== null ? s.consumedSeat : null;
          let rem = s.remaining;
          if ((rem === null || rem === undefined) && cap !== null && cons !== null) {
            rem = cap - cons;
          }
          const seatsClass = rem !== null && rem <= 0 ? "text-rose-400 font-semibold" : "text-emerald-400 font-medium";
          const seatsText = rem !== null ? (cap !== null ? `${rem} left (${cons}/${cap})` : `${rem} seats left`) : "Available";
          const roomText = s.room && s.room !== "None" && s.room !== "null" ? s.room : "TBA";
          const facultyText = s.faculty && s.faculty !== "None" ? s.faculty : "TBA";

          return `
          <tr class="${bgClass} hover:bg-slate-800/50 transition">
            <td class="p-1.5 font-bold font-mono text-brand-300">${courseName} ${s.is_mandatory ? '<span class="text-[9px] px-1 py-0.2 rounded bg-brand-500/30 text-brand-300 border border-brand-500/40">Mand</span>' : ''}</td>
            <td class="p-1.5 font-semibold text-slate-200">Sec ${s.sectionName || "?"}</td>
            <td class="p-1.5 text-slate-200">${facultyText} ${s.is_pref_match ? '<span class="text-amber-400 font-bold" title="Preferred Faculty">★</span>' : ''}</td>
            <td class="p-1.5 text-slate-300 font-mono text-[10px]">${roomText}</td>
            <td class="p-1.5 ${seatsClass}">${seatsText}</td>
          </tr>
        `;
        })
        .join("");
    }

    // Render Final Exam Schedule Table
    if (examsDetailsTableBody) {
      examsDetailsTableBody.innerHTML = current.sections
        .map((s, rIdx) => {
          const bgClass = rIdx % 2 === 0 ? "bg-slate-900/40" : "bg-slate-800/20";
          const courseName = s.courseCode || s.course_code || s.course || "-";
          const examText = s.exam && s.exam.raw && s.exam.raw !== "None" && s.exam.raw !== "null" ? s.exam.raw : "No clash recorded (N/A)";
          return `
          <tr class="${bgClass} hover:bg-slate-800/50 transition">
            <td class="p-2 font-bold font-mono text-brand-300">${courseName}</td>
            <td class="p-2 font-semibold text-slate-200">Sec ${s.sectionName || "?"}</td>
            <td class="p-2 text-slate-300 font-mono text-xs">${examText}</td>
          </tr>
        `;
        })
        .join("");
    }

    lucide.createIcons();
    applyRoutineZoom(currentRoutineZoom);
  }

  // Carousel controls
  if (prevOptionBtn) {
    prevOptionBtn.addEventListener("click", () => {
      if (state.currentIndex > 0) {
        state.currentIndex--;
        renderCurrentSchedule();
      }
    });
  }

  if (nextOptionBtn) {
    nextOptionBtn.addEventListener("click", () => {
      if (state.currentIndex < state.currentCombinations.length - 1) {
        state.currentIndex++;
        renderCurrentSchedule();
      }
    });
  }

  if (optionJumpInput) {
    optionJumpInput.addEventListener("change", (e) => {
      const val = parseInt(e.target.value, 10);
      if (!isNaN(val) && val >= 1 && val <= state.currentCombinations.length) {
        state.currentIndex = val - 1;
        renderCurrentSchedule();
      } else {
        e.target.value = state.currentIndex + 1;
      }
    });
  }

  // -----------------------------------------------------------------------
  // Routine Zoom Controls
  // -----------------------------------------------------------------------
  let currentRoutineZoom = 0.85;

  function applyRoutineZoom(zoomLevel) {
    currentRoutineZoom = Math.min(Math.max(zoomLevel, 0.5), 1.5);
    if (routineZoomWrapper) {
      routineZoomWrapper.style.transform = `scale(${currentRoutineZoom})`;
      routineZoomWrapper.style.transformOrigin = "top left";
      routineZoomWrapper.style.width = `${100 / currentRoutineZoom}%`;

      // Eliminate dead vertical space from transform scale
      setTimeout(() => {
        if (timetableGrid && routineScrollContainer) {
          const h = timetableGrid.offsetHeight;
          if (h > 0) {
            routineScrollContainer.style.height = `${Math.ceil(h * currentRoutineZoom) + 4}px`;
          }
        }
      }, 20);
    }
    if (routineZoomSelect) {
      for (const opt of routineZoomSelect.options) {
        if (Math.abs(parseFloat(opt.value) - currentRoutineZoom) < 0.04) {
          routineZoomSelect.value = opt.value;
          break;
        }
      }
    }
  }

  if (routineZoomOutBtn) {
    routineZoomOutBtn.addEventListener("click", () => {
      applyRoutineZoom(currentRoutineZoom - 0.1);
    });
  }

  if (routineZoomInBtn) {
    routineZoomInBtn.addEventListener("click", () => {
      applyRoutineZoom(currentRoutineZoom + 0.1);
    });
  }

  if (routineZoomSelect) {
    routineZoomSelect.addEventListener("change", (e) => {
      applyRoutineZoom(parseFloat(e.target.value));
    });
  }

  if (routineZoomResetBtn) {
    routineZoomResetBtn.addEventListener("click", () => {
      applyRoutineZoom(0.85);
    });
  }

  // Apply default comfortable 85% zoom on load
  applyRoutineZoom(0.85);

  // -----------------------------------------------------------------------
  // Sidebar Hide / Unhide (3-Dots Fullscreen Routine Toggle)
  // -----------------------------------------------------------------------
  let isSidebarHidden = false;

  function toggleSidebar(hide = null) {
    if (hide !== null) {
      isSidebarHidden = hide;
    } else {
      isSidebarHidden = !isSidebarHidden;
    }

    if (isSidebarHidden) {
      if (sidebarPanel) sidebarPanel.classList.add("hidden");
      if (resultsPanel) {
        resultsPanel.classList.remove("lg:col-span-7");
        resultsPanel.classList.add("lg:col-span-12");
      }
      if (showSidebarFab) showSidebarFab.classList.remove("hidden");
      if (toggleFullscreenText) toggleFullscreenText.textContent = "Exit Fullscreen";
      showToast("Course Selection hidden. Routine is now Full Screen!", "info");
    } else {
      if (sidebarPanel) sidebarPanel.classList.remove("hidden");
      if (resultsPanel) {
        resultsPanel.classList.remove("lg:col-span-12");
        resultsPanel.classList.add("lg:col-span-7");
      }
      if (showSidebarFab) showSidebarFab.classList.add("hidden");
      if (toggleFullscreenText) toggleFullscreenText.textContent = "Fullscreen";
      showToast("Course Selection panel restored.", "info");
    }
    lucide.createIcons();
  }

  if (toggleSidebarBtn) {
    toggleSidebarBtn.addEventListener("click", () => toggleSidebar(true));
  }

  if (toggleFullscreenBtn) {
    toggleFullscreenBtn.addEventListener("click", () => toggleSidebar());
  }

  if (showSidebarFab) {
    showSidebarFab.addEventListener("click", () => toggleSidebar(false));
  }

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
