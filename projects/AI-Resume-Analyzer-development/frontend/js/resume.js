let currentResumeId = null;
let currentJobId = null;

 document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.isLoggedIn()) {
    window.location.href = "login.html";
    return;
  }
  const params = new URLSearchParams(window.location.search);
  const persistedResumeId = AppState.getResumeId();
  const requestedResumeId = params.get("id");
  const requestedJobId = Number.parseInt(params.get("job_id") || "", 10) || null;
  currentResumeId = requestedResumeId || (persistedResumeId ? String(persistedResumeId) : null);
  const sameResumeScope = !requestedResumeId || String(persistedResumeId) === String(requestedResumeId);
  currentJobId = requestedJobId || (sameResumeScope ? AppState.getJobId() : null);
  AppState.setResumeId(currentResumeId);
  if (currentJobId) AppState.setJobId(currentJobId); else AppState.clearJobId();
  if (!currentResumeId) {
    showError("No resume ID specified.");
    return;
  }
  document.getElementById("matching-btn").href = `matching.html?id=${encodeURIComponent(currentResumeId)}`;
  try {
    let resume = await apiRequest(`/resumes/${currentResumeId}`, { auth: true });
    if (currentJobId && resume.improvement_job_id !== currentJobId) {
      resume = { ...resume, improvement_recommendations: [], high_priority_fixes: [], impact_metrics: [], skills_ats_optimization: [], professional_summary_polish: [], improvement_job_id: null };
    } else if (!currentJobId && resume.improvement_job_id) {
      resume = { ...resume, improvement_recommendations: [], high_priority_fixes: [], impact_metrics: [], skills_ats_optimization: [], professional_summary_polish: [], improvement_job_id: null };
    }
    renderAnalysis(resume);
    await loadMatchingState();
  } catch (err) {
    showError(err.message);
  }

  document.getElementById("analyze-btn").addEventListener("click", analyzeResume);
  document.getElementById("improve-btn").addEventListener("click", recommendImprovements);
  document.getElementById("improve-job-select").addEventListener("change", (event) => {
    currentJobId = Number.parseInt(event.target.value, 10) || null;
    if (currentJobId) AppState.setJobId(currentJobId); else AppState.clearJobId();
    syncRecommendationScopeInUrl();
    clearRecommendationSections(currentJobId ? "Target job changed; generate recommendations for this CV and job." : "General CV recommendations will use only this CV.");
  });
  document.getElementById("delete-btn").addEventListener("click", async () => {
    if (!confirm("Are you sure you want to delete this resume? This action cannot be undone.")) return;
    try {
      await apiRequest(`/resumes/${currentResumeId}`, { method: "DELETE", auth: true });
      if (String(AppState.getResumeId()) === String(currentResumeId)) AppState.setResumeId(null);
      AppState.clearJobId();
      window.location.href = "dashboard.html";
    } catch (err) {
      showMessage(document.getElementById("analysis-message"), err.message);
    }
  });
  document.getElementById("toggle-raw").addEventListener("click", () => {
    const rawEl = document.getElementById("raw-text");
    const button = document.getElementById("toggle-raw");
    const showing = rawEl.style.display !== "none";
    rawEl.style.display = showing ? "none" : "block";
    button.textContent = showing ? "Show extracted text" : "Hide extracted text";
  });
});

async function analyzeResume() {
  const button = document.getElementById("analyze-btn");
  const messageEl = document.getElementById("analysis-message");
  button.disabled = true;
  button.textContent = "Analyzing...";
  hideMessage(messageEl);
  try {
    const resume = await apiRequest(`/resumes/${currentResumeId}/analyze`, { method: "POST", auth: true });
      currentJobId = null;
      AppState.clearJobId();
      renderAnalysis(resume);
    await loadMatchingState();
    showMessage(messageEl, "Analysis completed. Previous job-specific recommendations were cleared.", "success");
  } catch (err) {
    showMessage(messageEl, err.message);
  } finally {
    button.disabled = false;
    button.textContent = "Analyze CV";
  }
}

async function recommendImprovements() {
  const button = document.getElementById("improve-btn");
  const statusEl = document.getElementById("improve-status");
  const messageEl = document.getElementById("analysis-message");
  button.disabled = true;
  button.textContent = "Generating recommendations...";
  hideMessage(messageEl);
  try {
    const endpoint = currentJobId
      ? `/resumes/${currentResumeId}/improvements?job_id=${encodeURIComponent(currentJobId)}`
      : `/resumes/${currentResumeId}/improvements`;
    const recommendations = await apiRequest(endpoint, { method: "POST", auth: true });
    renderImprovementRecommendations(recommendations);
    if (statusEl) statusEl.textContent = recommendations.scope === "job_specific"
      ? `Recommendations are ready for ${recommendations.job_title}; they use only this CV and job.`
      : "General CV recommendations are ready; they use only this CV and no target job.";
    showMessage(messageEl, "Improvement recommendations are ready.", "success");
  } catch (err) {
    showMessage(messageEl, err.message);
  } finally {
    button.disabled = false;
    button.textContent = "Improvement Recommendations";
  }
}

async function loadMatchingState() {
  const improveButton = document.getElementById("improve-btn");
  const statusEl = document.getElementById("improve-status");
  const jobSelect = document.getElementById("improve-job-select");
  jobSelect.disabled = true;
  jobSelect.innerHTML = "<option value=\"\">Loading available targets…</option>";
  if (statusEl) statusEl.textContent = "Loading optional target jobs for this CV…";
  try {
    const recommendations = await apiRequest(`/recommendations?resume_id=${encodeURIComponent(currentResumeId)}`, { auth: true });
    const matched = recommendations.length > 0;
    if (matched) {
      jobSelect.innerHTML = `<option value="">General CV improvements</option>${recommendations.map((item) => `<option value="${item.job_id}">${escapeHtml(item.job_title || `Job ${item.job_id}`)}${item.job_company ? ` — ${escapeHtml(item.job_company)}` : ""}</option>`).join("")}`;
      const availableIds = recommendations.map((item) => item.job_id);
      if (!availableIds.includes(currentJobId)) currentJobId = null;
      jobSelect.value = currentJobId ? String(currentJobId) : "";
      jobSelect.disabled = false;
      improveButton.disabled = false;
      improveButton.title = currentJobId ? "Generate recommendations for the selected CV and target job." : "Generate general recommendations for the selected CV.";
      const selected = recommendations.find((item) => item.job_id === currentJobId);
      if (statusEl) statusEl.textContent = selected
        ? `Target job: ${selected.job_title}. Recommendations will use only this CV and job.`
        : "General CV recommendations will use only this CV. Select a matched job to tailor them.";
    } else {
      jobSelect.innerHTML = "<option value=\"\">General CV improvements</option>";
      jobSelect.disabled = false;
      improveButton.disabled = false;
      improveButton.title = "Generate general recommendations for the selected CV.";
      if (statusEl) statusEl.textContent = "General CV recommendations will use only this CV; no job selection is required.";
    }
  } catch (_) {
    jobSelect.innerHTML = "<option value=\"\">General CV improvements</option>";
    jobSelect.disabled = false;
    improveButton.disabled = false;
    improveButton.title = "Generate general recommendations for the selected CV.";
    if (statusEl) statusEl.textContent = "General CV recommendations will use only this CV; job matching is optional.";
  }
}

function renderAnalysis(resume) {
  document.getElementById("loading").style.display = "none";
  document.getElementById("analysis-content").style.display = "block";
  document.getElementById("resume-filename").textContent = resume.original_filename;
  document.getElementById("resume-full-name").textContent = resume.full_name || "Name not available";
  const contact = Object.entries(resume.contact || {}).filter(([, value]) => value).map(([key, value]) => `${key}: ${value}`);
  document.getElementById("resume-contact").textContent = contact.length ? contact.join(" | ") : "Contact information not available";
  const date = new Date(resume.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" });
  document.getElementById("resume-meta").textContent = `${resume.file_type.toUpperCase()} | Uploaded ${date}`;
  document.getElementById("resume-score").textContent = `${Math.round(resume.score || 0)}%`;
  document.getElementById("resume-summary").textContent = resume.summary || "No summary generated.";
  renderTags("tech-skills", resume.skills?.technical || [], "tech", "No technical skills detected.");
  renderTags("soft-skills", resume.skills?.soft || [], "soft", "No soft skills detected.");
  const skillGroups = [
    ["Programming languages", resume.skills?.programming_languages],
    ["Frameworks", resume.skills?.frameworks],
    ["Libraries", resume.skills?.libraries],
    ["Tools", resume.skills?.tools],
    ["Databases", resume.skills?.databases],
    ["Cloud", resume.skills?.cloud],
    ["Machine learning", resume.skills?.machine_learning],
    ["Data science", resume.skills?.data_science],
    ["AI", resume.skills?.ai],
    ["Computer vision", resume.skills?.computer_vision],
    ["NLP", resume.skills?.nlp],
  ].filter(([, values]) => values && values.length);
  document.getElementById("categorized-skills").innerHTML = skillGroups.length
    ? skillGroups.map(([label, values]) => `<div class="match-skills-row"><span class="match-skills-label">${escapeHtml(label)}:</span>${values.map((value) => `<span class="tag tech small">${escapeHtml(value)}</span>`).join("")}</div>`).join("")
    : `<p class="no-data">No categorized skill evidence detected.</p>`;
  renderEntries("education-list", resume.education || [], (entry) => `<div class="entry-title">${escapeHtml(entry.degree || "Degree not specified")}</div>${entry.institution ? `<div class="entry-subtitle">${escapeHtml(entry.institution)}</div>` : ""}${entry.year ? `<div class="entry-date">${escapeHtml(entry.year)}</div>` : ""}${entry.details ? `<div class="entry-details">${escapeHtml(entry.details)}</div>` : ""}`, "No education entries detected.");
  renderEntries("experience-list", resume.experience || [], (entry) => `<div class="entry-title">${escapeHtml(entry.title || "Role not specified")}</div>${entry.company ? `<div class="entry-subtitle">${escapeHtml(entry.company)}</div>` : ""}${entry.duration ? `<div class="entry-date">${escapeHtml(entry.duration)}</div>` : ""}${entry.description ? `<div class="entry-details">${escapeHtml(entry.description)}</div>` : ""}`, "No experience entries detected.");
  renderEntries("projects-list", resume.projects || [], (project) => `<div class="entry-title">${escapeHtml(project.name || "Project not specified")}</div>${project.technologies?.length ? `<div class="entry-subtitle">${escapeHtml(project.technologies.join(", "))}</div>` : ""}${project.description ? `<div class="entry-details">${escapeHtml(project.description)}</div>` : ""}`, "No projects detected.");
  renderEntries("strengths-list", resume.strengths || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "No strengths detected.");
  renderEntries("weaknesses-list", resume.weaknesses || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "No specific improvement points detected.");
  renderEntries("recommendations-list", resume.improvement_recommendations || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "Click Improvement Recommendations to generate CV-specific actions.");
  renderEntries("high-priority-fixes-list", resume.high_priority_fixes || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "Generate recommendations to see high-priority fixes.");
  renderEntries("impact-metrics-list", resume.impact_metrics || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "Generate recommendations to see impact and metrics guidance.");
  renderEntries("skills-ats-list", resume.skills_ats_optimization || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "Generate recommendations to see ATS keyword guidance.");
  renderEntries("summary-polish-list", resume.professional_summary_polish || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "Generate recommendations to see summary-polish guidance.");
  renderTags("certifications-list", resume.certifications || [], "tech", "No certifications detected.");
  renderEntries("training-list", resume.training || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "No training entries detected.");
  renderTags("languages-list", resume.languages || [], "soft", "No languages detected.");
  renderEntries("achievements-list", resume.achievements || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "No achievements detected.");
  renderEntries("learning-resources-list", resume.learning_resources || [], (item) => `<div class="entry-title">${escapeHtml(item)}</div>`, "No learning resources available.");
  document.getElementById("raw-text").textContent = resume.raw_text || "No text extracted.";
}

function syncRecommendationScopeInUrl() {
  const url = new URL(window.location.href);
  if (currentJobId) url.searchParams.set("job_id", String(currentJobId));
  else url.searchParams.delete("job_id");
  window.history.replaceState({}, "", url);
}

function clearRecommendationSections(emptyText) {
  const renderer = (id) => renderEntries(id, [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, emptyText);
  ["recommendations-list", "high-priority-fixes-list", "impact-metrics-list", "skills-ats-list", "summary-polish-list"].forEach(renderer);
  const statusEl = document.getElementById("improve-status");
  if (statusEl) statusEl.textContent = emptyText;
}

function renderImprovementRecommendations(data) {
  document.getElementById("resume-score").textContent = `${Math.round(data.score || 0)}%`;
  renderEntries("strengths-list", data.strengths || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "No strengths detected.");
  renderEntries("weaknesses-list", data.weaknesses || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "No weaknesses detected.");
  renderEntries("recommendations-list", data.recommendations || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "No recommendations returned.");
  renderEntries("high-priority-fixes-list", data.high_priority_fixes || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "No high-priority fixes returned.");
  renderEntries("impact-metrics-list", data.impact_metrics || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "No impact and metrics guidance returned.");
  renderEntries("skills-ats-list", data.skills_ats_optimization || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "No ATS keyword guidance returned.");
  renderEntries("summary-polish-list", data.professional_summary_polish || [], (item) => `<div class="entry-details">${escapeHtml(item)}</div>`, "No summary-polish guidance returned.");
  renderTags("certifications-list", data.certifications || [], "tech", "No certifications detected.");
  renderEntries("learning-resources-list", data.learning_resources || [], (item) => `<div class="entry-title">${escapeHtml(item)}</div>`, "No learning resources available.");
}

function renderTags(id, values, className, emptyText) {
  const container = document.getElementById(id);
  container.innerHTML = values.length ? values.map((value) => `<span class="tag ${className}">${escapeHtml(value)}</span>`).join("") : `<p class="no-data">${emptyText}</p>`;
}

function renderEntries(id, values, render, emptyText) {
  const container = document.getElementById(id);
  container.innerHTML = values.length ? values.map((value) => `<div class="entry-card"><div class="entry-body">${render(value)}</div></div>`).join("") : `<p class="no-data">${emptyText}</p>`;
}

function showError(message) {
  document.getElementById("loading").style.display = "none";
  document.getElementById("error-state").style.display = "block";
  document.getElementById("error-message").textContent = message;
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}
