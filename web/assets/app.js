"use strict";
document.documentElement.classList.add("js");
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHTML = value => String(value).replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[character]));
const format = number => Number(number).toLocaleString("en-US");
let toastTimer;
function toast(message) {
  $("#toast").textContent = message;
  $("#toast").classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $("#toast").classList.remove("visible"), 2400);
}
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast("คัดลอกแล้ว"); }
  catch { toast("คัดลอกอัตโนมัติไม่ได้ กรุณาเลือกข้อความแล้วกดคัดลอก"); }
}
$$('[data-copy-target]').forEach(button => button.addEventListener("click", () => copyText(document.getElementById(button.dataset.copyTarget).textContent)));

// Tabs progressively enhance the full static guide; without JS all modules remain visible.
function activateTab(tab, focus = false) {
  $$(".code-tab").forEach(item => {
    const selected = item === tab;
    item.setAttribute("aria-selected", String(selected));
    item.tabIndex = selected ? 0 : -1;
    document.getElementById(item.getAttribute("aria-controls")).classList.toggle("is-active", selected);
  });
  if (focus) tab.focus();
}
$$(".code-tab").forEach((tab, index, tabs) => {
  tab.addEventListener("click", () => activateTab(tab));
  tab.addEventListener("keydown", event => {
    let target;
    if (event.key === "ArrowRight") target = tabs[(index + 1) % tabs.length];
    if (event.key === "ArrowLeft") target = tabs[(index - 1 + tabs.length) % tabs.length];
    if (event.key === "Home") target = tabs[0];
    if (event.key === "End") target = tabs[tabs.length - 1];
    if (target) { event.preventDefault(); activateTab(target, true); }
  });
});
activateTab($(".code-tab"));
const linkedCodePanel = document.getElementById(location.hash.slice(1))?.closest(".code-panel");
if (linkedCodePanel) activateTab($(`[aria-controls="${linkedCodePanel.id}"]`));

const shade = document.createElement("button");
shade.className = "nav-shade";
shade.setAttribute("aria-label", "ปิดสารบัญ");
document.body.append(shade);
const mobileMedia = matchMedia("(max-width: 950px)");
function toggleMenu(open) {
  document.body.classList.toggle("menu-open", open);
  $("#menu-toggle").setAttribute("aria-expanded", String(open));
  $("#navigation").inert = mobileMedia.matches && !open;
}
$("#menu-toggle").addEventListener("click", () => toggleMenu(!document.body.classList.contains("menu-open")));
shade.addEventListener("click", () => toggleMenu(false));
mobileMedia.addEventListener("change", () => toggleMenu(false));
toggleMenu(false);
$$("nav a").forEach(link => link.addEventListener("click", () => toggleMenu(false)));
const sections = $$("main > section");
const observer = new IntersectionObserver(entries => {
  const visible = entries.filter(entry => entry.isIntersecting);
  if (visible.length) {
    const id = visible[0].target.id;
    $$("nav a").forEach(link => {
      const active = link.getAttribute("href") === "#" + id;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "location"); else link.removeAttribute("aria-current");
    });
  }
}, {rootMargin: "-80px 0px -65% 0px"});
sections.forEach(section => observer.observe(section));

// Documentation search includes inactive code tabs and expands the selected explanation.
const searchItems = $$(".section-heading, .function-card, .module-heading").map(element => {
  const title = $("h2, h3, h4", element)?.textContent || "";
  const detail = element.matches(".function-card") ? $("p", element)?.textContent || "" : element.parentElement.querySelector("p")?.textContent || "";
  return {element, title, detail, key: (title + " " + detail).toLocaleLowerCase()};
});
const dialog = $("#guide-search-dialog");
function renderGuideSearch() {
  const query = $("#guide-search").value.trim().toLocaleLowerCase();
  const results = searchItems.filter(item => !query || item.key.includes(query)).slice(0, 25);
  $("#guide-results").replaceChildren();
  for (const item of results) {
    const link = document.createElement("a");
    link.className = "guide-result";
    link.href = "#" + (item.element.id || item.element.closest("section").id);
    link.innerHTML = escapeHTML(item.title) + "<small>" + escapeHTML(item.detail.slice(0, 170)) + "</small>";
    link.addEventListener("click", event => {
      event.preventDefault();
      const panel = item.element.closest(".code-panel");
      if (panel) activateTab($(`[aria-controls="${panel.id}"]`));
      dialog.close();
      item.element.setAttribute("tabindex", "-1");
      item.element.focus({preventScroll: true});
      item.element.scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "start"});
      history.replaceState(null, "", link.hash);
    });
    $("#guide-results").append(link);
  }
  if (!results.length) $("#guide-results").textContent = "ไม่พบหัวข้อที่ตรงกับคำค้น ลองใช้ชื่อฟังก์ชันหรือคำสั้น ๆ";
}
$("#search-trigger").addEventListener("click", () => { dialog.showModal(); renderGuideSearch(); $("#guide-search").focus(); });
$("#close-search").addEventListener("click", () => dialog.close());
$("#guide-search").addEventListener("input", renderGuideSearch);
dialog.addEventListener("click", event => { if (event.target === dialog && (event.offsetX < 0 || event.offsetX > dialog.clientWidth || event.offsetY < 0 || event.offsetY > dialog.clientHeight)) dialog.close(); });
document.addEventListener("keydown", event => {
  if (event.key === "Escape") {
    toggleMenu(false);
    if (dialog.open) { event.preventDefault(); dialog.close(); }
  }
  if (event.key === "/" && !event.ctrlKey && !event.metaKey && !/INPUT|TEXTAREA/.test(document.activeElement.tagName) && !dialog.open) { event.preventDefault(); $("#search-trigger").click(); }
});

// Drug data is generated from verified CSV. Small index first; load one shard on selection.
let drugIndex = [], filteredDrugs = [], selectedId = "", visibleLimit = 30, selectionToken = 0;
const shardCache = new Map();
const categoryLabels = ["Targets", "Enzymes", "Carriers*", "Transporters"];
async function getJSON(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error("HTTP " + response.status);
  return response.json();
}
function renderDrugList() {
  const query = $("#drug-search").value.trim().toLocaleLowerCase();
  filteredDrugs = drugIndex.filter(drug => !query || drug.id.toLocaleLowerCase().includes(query) || drug.name.toLocaleLowerCase().includes(query));
  $("#drug-result-count").textContent = `พบ ${format(filteredDrugs.length)} ยา · แสดง ${Math.min(visibleLimit, filteredDrugs.length)}`;
  $("#drug-list").replaceChildren();
  for (const drug of filteredDrugs.slice(0, visibleLimit)) {
    const button = document.createElement("button");
    button.className = "drug-choice" + (drug.id === selectedId ? " selected" : "");
    button.setAttribute("aria-pressed", String(drug.id === selectedId));
    button.innerHTML = `<code>${escapeHTML(drug.id)}</code><span>${escapeHTML(drug.name)}</span>`;
    button.addEventListener("click", () => selectDrug(drug.id));
    $("#drug-list").append(button);
  }
  if (!filteredDrugs.length) $("#drug-list").innerHTML = '<p class="empty-state">ไม่พบยา ลองรหัส DB หรือชื่อภาษาอังกฤษ</p>';
  $("#load-more").hidden = filteredDrugs.length <= visibleLimit;
}
function proteinTable(proteins) {
  const fields = ["number", "name", "organism", "actions", "uniprot", "gene"];
  return '<div class="table-wrap"><table class="protein-table"><thead><tr><th>#</th><th>ชื่อเป้าหมาย / โปรตีน</th><th>Organism</th><th>Actions</th><th>UniProt</th><th>Gene</th></tr></thead><tbody>' + proteins.map(protein => '<tr>' + fields.map(field => '<td>' + escapeHTML(protein[field]) + '</td>').join("") + '</tr>').join("") + '</tbody></table></div>';
}
function renderDrug(drug) {
  let html = `<div class="drug-title-row"><div><code>${escapeHTML(drug.id)}</code><h3>${escapeHTML(drug.name)}</h3></div><button class="share-button" id="share-drug">คัดลอกลิงก์ ↗</button></div>`;
  html += '<div class="drug-counts">' + drug.counts.map((count, index) => `<div><span>${categoryLabels[index]}</span><strong>${format(count)}</strong></div>`).join("") + '</div>';
  html += '<p class="small-note">* Carriers = ค่าที่ใช้ใน Total-IonChannel ตามสมมติฐาน · เลขเริ่มใหม่ทุกหมวด</p>';
  if (!drug.proteins.length) html += '<div class="empty-state">XML ของยานี้ไม่มี entries ทั้ง 4 หมวด แถว CSV จึงมีเพียง 6 cells และ counts เป็น 0</div>';
  for (let category = 0; category < 4; category++) {
    const proteins = drug.proteins.filter(protein => protein.category === category);
    if (proteins.length) html += `<div class="protein-group"><h4>${categoryLabels[category]} · ${format(proteins.length)} entries</h4>${proteinTable(proteins)}</div>`;
  }
  for (const complex of drug.complexes || []) {
    html += `<details class="complex-detail"><summary>Subunits: ${escapeHTML(complex.entry_name)} (${complex.polypeptides.length})</summary><ul>`;
    html += complex.polypeptides.map(peptide => `<li>${escapeHTML(peptide.name)} · ${escapeHTML(peptide.organism)}<br><code>${escapeHTML(peptide.Uniprot_ID)}</code> / ${escapeHTML(peptide.gene_name)} · ${escapeHTML(peptide.source)}</li>`).join("");
    html += '</ul></details>';
  }
  $("#drug-detail").innerHTML = html;
  $("#share-drug").addEventListener("click", () => {
    const url = new URL(location.href);
    url.searchParams.set("drug", drug.id); url.hash = "data";
    copyText(url.href);
  });
}
async function selectDrug(id) {
  if (!/^DB\d{5,}$/.test(id) || !drugIndex.some(drug => drug.id === id)) { toast("ไม่พบรหัสยานี้ในข้อมูล"); return; }
  selectedId = id;
  renderDrugList();
  const token = ++selectionToken;
  $("#drug-detail").innerHTML = '<div class="empty-state">กำลังโหลดรายละเอียด…</div>';
  try {
    const shardName = id.slice(0, 5);
    if (!shardCache.has(shardName)) shardCache.set(shardName, getJSON(`data/drugs/${shardName}.json`));
    const shard = await shardCache.get(shardName);
    if (!shard[id]) throw new Error("Missing drug record");
    if (token !== selectionToken) return;
    renderDrug(shard[id]);
    const url = new URL(location.href); url.searchParams.set("drug", id);
    history.replaceState(null, "", url);
  } catch {
    shardCache.delete(id.slice(0, 5));
    if (token === selectionToken) $("#drug-detail").innerHTML = '<div class="empty-state">โหลดรายละเอียดไม่สำเร็จ ลองเลือกยาอีกครั้ง หรือ <a href="downloads/Drug_Target.csv">ดาวน์โหลด CSV</a></div>';
  }
}
$("#drug-search").addEventListener("input", () => { visibleLimit = 30; renderDrugList(); });
$("#load-more").addEventListener("click", () => { visibleLimit += 30; renderDrugList(); });
$$('[data-drug]').forEach(button => button.addEventListener("click", () => { $("#drug-search").value = button.dataset.drug; visibleLimit = 30; selectDrug(button.dataset.drug); }));
getJSON("data/index.json").then(index => {
  drugIndex = index.map(([id, name, counts]) => ({id, name, counts}));
  renderDrugList();
  const requestedId = new URL(location.href).searchParams.get("drug");
  selectDrug(requestedId && drugIndex.some(drug => drug.id === requestedId) ? requestedId : "DB00001");
}).catch(() => {
  $("#drug-result-count").textContent = "โหลดดัชนีไม่สำเร็จ";
  $("#drug-list").innerHTML = '<p class="empty-state">เปิดเว็บผ่าน HTTP/HTTPS และลองโหลดใหม่ หรือดาวน์โหลด CSV ด้านล่าง</p>';
});
