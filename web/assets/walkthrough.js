"use strict";
// The generated HTML remains readable without JavaScript; enhance it into a lesson reader.
(() => {
  const all = (selector, root = document) => [...root.querySelectorAll(selector)];
  const panels = all(".walkthrough-section .code-panel");
  const tabs = all(".code-tab");
  const lessons = all(".lesson-card");
  const storageKey = "drugbank-lab-v2-read-functions";
  const knownIds = new Set(lessons.map(lesson => lesson.id));
  let read = new Set(), storageAvailable = true;
  try {
    const stored = JSON.parse(localStorage.getItem(storageKey) || "[]");
    if (Array.isArray(stored)) read = new Set(stored.filter(id => knownIds.has(id)));
    localStorage.setItem(storageKey, JSON.stringify([...read]));
  } catch { storageAvailable = false; }
  const motion = () => matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth";

  function updateProgress(save = false) {
    if (save && storageAvailable) {
      try { localStorage.setItem(storageKey, JSON.stringify([...read])); }
      catch { storageAvailable = false; }
    }
    document.getElementById("reading-count").textContent = read.size;
    document.getElementById("reading-progress").value = read.size;
    document.getElementById("reading-storage-note").textContent = storageAvailable
      ? "ทำเครื่องหมายเมื่ออ่านจบ · สถานะเก็บไว้ในเบราว์เซอร์นี้"
      : "ทำเครื่องหมายเมื่ออ่านจบ · สถานะจะอยู่จนกว่าจะปิดหรือโหลดหน้านี้ใหม่";
    for (const lesson of lessons) {
      const done = read.has(lesson.id);
      const button = lesson.querySelector("[data-mark-read]");
      button.setAttribute("aria-pressed", String(done));
      button.innerHTML = done ? '<span aria-hidden="true">✓</span> อ่านแล้ว' : '<span aria-hidden="true">○</span> ทำเครื่องหมายอ่านแล้ว';
      const nav = document.getElementById(lesson.id + "-tab");
      nav.classList.toggle("is-read", done);
      nav.querySelector(".function-read-indicator").hidden = !done;
    }
  }

  function setView(panel, view) {
    panel.dataset.view = view;
    all("[data-reader-view]", panel).forEach(button => button.setAttribute("aria-pressed", String(button.dataset.readerView === view)));
    if (view === "file") panel.querySelector(".full-source").open = true;
  }

  function activateTab(tab, focus = false) {
    if (!tab) return;
    tabs.forEach(item => {
      const selected = item === tab;
      item.setAttribute("aria-selected", String(selected));
      item.tabIndex = selected ? 0 : -1;
      document.getElementById(item.getAttribute("aria-controls")).classList.toggle("is-active", selected);
    });
    updateRoute();
    if (focus) tab.focus();
  }

  function updateRoute() {
    const selectedId = document.querySelector(".code-panel.is-active .lesson-card.is-active")?.id;
    all(".code-route [data-open-lesson]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.openLesson === selectedId)));
  }

  function focusStep(button, scroll = false) {
    const lesson = button.closest(".lesson-card");
    const code = document.getElementById(button.getAttribute("aria-controls"));
    const start = Number(button.dataset.lineStart), end = Number(button.dataset.lineEnd);
    all(".lesson-step-button", lesson).forEach(item => item.setAttribute("aria-pressed", String(item === button)));
    all(".source-line", code).forEach(line => line.classList.toggle("is-highlighted", Number(line.dataset.line) >= start && Number(line.dataset.line) <= end));
    lesson.querySelector(".focus-range").textContent = `L${start}–${end}`;
    if (!scroll) return;
    lesson.querySelector(".source-reveal").open = true;
    const firstLine = code.querySelector(`.source-line[data-line="${start}"]`);
    const pre = code.closest("pre");
    if (firstLine) pre.scrollTo({top: Math.max(0, firstLine.offsetTop - 18), behavior: motion()});
    const source = lesson.querySelector(".lesson-source");
    if (matchMedia("(max-width: 780px)").matches) source.scrollIntoView({behavior: motion(), block: "start"});
  }

  function openLesson(id, {scroll = false, focus = false, hash = false} = {}) {
    const lesson = document.getElementById(id);
    if (!lesson?.matches(".lesson-card")) return;
    const panel = lesson.closest(".code-panel");
    activateTab(tabs.find(tab => tab.getAttribute("aria-controls") === panel.id));
    setView(panel, "lesson");
    const filter = panel.querySelector(".function-filter");
    filter.value = "";
    filterFunctions(panel);
    all(".lesson-card", panel).forEach(item => item.classList.toggle("is-active", item === lesson));
    all(".function-nav-button", panel).forEach(button => {
      const selected = button.getAttribute("aria-controls") === id;
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
    });
    panel.querySelector(".module-position").textContent = `บทเรียน ${lesson.dataset.position} / ${all(".lesson-card", panel).length}`;
    updateRoute();
    if (hash) history.replaceState(null, "", "#" + id);
    if (focus) lesson.focus({preventScroll: true});
    if (scroll) lesson.scrollIntoView({behavior: motion(), block: "start"});
  }

  function filterFunctions(panel) {
    const query = panel.querySelector(".function-filter").value.trim().toLocaleLowerCase();
    const buttons = all(".function-nav-button", panel);
    for (const button of buttons) {
      const lesson = document.getElementById(button.getAttribute("aria-controls"));
      button.hidden = !(button.textContent + " " + lesson.dataset.functionName).toLocaleLowerCase().includes(query);
    }
    const visible = buttons.filter(button => !button.hidden);
    const firstTab = visible.find(button => button.getAttribute("aria-selected") === "true") || visible[0];
    buttons.forEach(button => { button.tabIndex = button === firstTab ? 0 : -1; });
    panel.querySelector(".function-filter-empty").hidden = visible.length > 0;
  }

  function reveal(element) {
    const panel = element?.closest(".code-panel");
    if (!panel) return;
    activateTab(tabs.find(tab => tab.getAttribute("aria-controls") === panel.id));
    const lesson = element.closest(".lesson-card");
    if (lesson) openLesson(lesson.id);
    else if (element.closest(".full-source")) setView(panel, "file");
    for (let parent = element.parentElement; parent && parent !== panel; parent = parent.parentElement) {
      if (parent.tagName === "DETAILS") parent.open = true;
    }
  }

  tabs.forEach((tab, index) => {
    const changeFile = (target, focus = false) => {
      activateTab(target, focus);
      document.getElementById(target.getAttribute("aria-controls")).scrollIntoView({behavior: motion(), block: "start"});
    };
    tab.addEventListener("click", () => changeFile(tab));
    tab.addEventListener("keydown", event => {
      const targets = {ArrowRight: tabs[(index + 1) % tabs.length], ArrowLeft: tabs[(index - 1 + tabs.length) % tabs.length], Home: tabs[0], End: tabs.at(-1)};
      if (targets[event.key]) { event.preventDefault(); changeFile(targets[event.key], true); }
    });
  });
  for (const panel of panels) {
    all(".function-nav-button", panel).forEach(button => {
      button.tabIndex = button.getAttribute("aria-selected") === "true" ? 0 : -1;
      button.addEventListener("click", () => openLesson(button.getAttribute("aria-controls"), {hash: true, scroll: true}));
      button.addEventListener("keydown", event => {
        const visible = all(".function-nav-button", panel).filter(item => !item.hidden);
        const index = visible.indexOf(button);
        const targets = {ArrowDown: visible[(index + 1) % visible.length], ArrowUp: visible[(index - 1 + visible.length) % visible.length], Home: visible[0], End: visible.at(-1)};
        const target = targets[event.key];
        if (target) { event.preventDefault(); openLesson(target.getAttribute("aria-controls"), {hash: true, scroll: true}); target.focus({preventScroll: true}); }
      });
    });
    panel.querySelector(".function-filter").addEventListener("input", () => filterFunctions(panel));
    all("[data-reader-view]", panel).forEach(button => button.addEventListener("click", () => setView(panel, button.dataset.readerView)));
    const first = panel.querySelector(".lesson-card");
    first.classList.add("is-active");
  }
  all("[data-open-lesson]").forEach(button => button.addEventListener("click", () => openLesson(button.dataset.openLesson, {scroll: true, focus: true, hash: true})));
  for (const lesson of lessons) {
    all(".lesson-step-button", lesson).forEach(button => {
      button.disabled = false;
      button.addEventListener("click", () => focusStep(button, true));
    });
    focusStep(lesson.querySelector(".lesson-step-button"));
    lesson.querySelector("[data-back-to-explanation]").addEventListener("click", () => lesson.querySelector(".lesson-copy").scrollIntoView({behavior: motion(), block: "start"}));
    lesson.querySelector("[data-mark-read]").addEventListener("click", () => {
      if (read.has(lesson.id)) read.delete(lesson.id); else read.add(lesson.id);
      updateProgress(true);
    });
  }
  all("[data-wrap-target]").forEach(button => button.addEventListener("click", () => {
    const wrapped = document.getElementById(button.dataset.wrapTarget).classList.toggle("is-wrapped");
    button.setAttribute("aria-pressed", String(wrapped));
  }));
  document.getElementById("reset-reading").addEventListener("click", () => { read.clear(); updateProgress(true); });
  function revealHash() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const element = document.getElementById(id);
    if (!element?.closest(".code-panel")) return;
    reveal(element);
    requestAnimationFrame(() => element.scrollIntoView({block: "start"}));
  }
  window.CodeReader = {activateTab, reveal};
  document.documentElement.classList.add("js");
  activateTab(tabs[0]);
  updateProgress();
  revealHash();
  addEventListener("hashchange", revealHash);
})();
