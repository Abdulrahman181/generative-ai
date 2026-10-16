
document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.isLoggedIn()) { window.location.href = "login.html"; return; }

  const messageEl = document.getElementById("match-message");

  
  document.getElementById("logout-btn").addEventListener("click", async () => {
    try { await apiRequest("/auth/logout", { method: "POST", auth: true }); } catch (_) {}
    Auth.clearToken();
    window.location.href = "login.html";
  });

  
  const initialResumeId = Number.parseInt(new URLSearchParams(window.location.search).get("id") || "", 10) || AppState.getResumeId();
  let selectedResumeId = initialResumeId;
  const selectorEl = document.getElementById("resume-selector");
  const selectedStatusEl = document.getElementById("selected-resume-status");
  const matchAction = document.getElementById("match-action");
  const resultsSection = document.getElementById("results-section");
  const resultsSummary = document.getElementById("results-summary");
  const resultsList = document.getElementById("match-results");
  let selectedResumeLabel = "";

  try {
    const resumes = await apiRequest("/resumes", { auth: true });
    selectorEl.dataset.state = "ready";
    if (resumes.length === 0) {
      selectorEl.dataset.state = "empty";
      selectorEl.innerHTML = `
        <div class="empty-state">
          <p>You haven't uploaded any resumes yet.</p>
          <a href="dashboard.html" class="primary" style="display:inline-block;width:auto;padding:10px 24px;text-decoration:none;">Upload Resume</a>
        </div>`;
      return;
    }

    selectorEl.innerHTML = resumes.map(r => `
      <label class="resume-option" data-id="${r.id}">
        <input type="radio" name="resume" value="${r.id}" />
        <div class="resume-option-body">
          <span class="resume-option-icon">${escapeHtml(r.file_type.toUpperCase())}</span>
          <div>
            <div class="resume-option-name">${escapeHtml(r.original_filename)}</div>
            <div class="resume-option-date">${new Date(r.created_at).toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' })}</div>
          </div>
        </div>
      </label>
    `).join("");

    
    selectorEl.querySelectorAll('input[name="resume"]').forEach(radio => {
      radio.addEventListener("change", () => {
        selectedResumeId = parseInt(radio.value, 10);
        window.selectedMatchingResumeId = selectedResumeId;
        AppState.setResumeId(selectedResumeId);
        AppState.clearJobId();
        selectedResumeLabel = radio.closest(".resume-option").querySelector(".resume-option-name").textContent.trim();
        if (selectedStatusEl) selectedStatusEl.textContent = `Selected resume: ${selectedResumeLabel} (ID ${selectedResumeId}). Matching will use only this resume.`;
        matchAction.style.display = "block";
        matchAction.dataset.state = "ready";
        resultsSection.style.display = "none";
        resultsSection.dataset.state = "hidden";
        resultsSummary.textContent = "";
        resultsList.innerHTML = "";
        selectorEl.querySelectorAll(".resume-option").forEach(opt => opt.classList.remove("selected"));
        radio.closest(".resume-option").classList.add("selected");
      });
    });
    const requestedResumeId = new URLSearchParams(window.location.search).get("id") || (initialResumeId ? String(initialResumeId) : null);
    if (requestedResumeId) {
      const requested = selectorEl.querySelector(`input[value="${CSS.escape(requestedResumeId)}"]`);
      if (requested) {
        requested.checked = true;
        requested.dispatchEvent(new Event("change"));
      } else if (selectedStatusEl) {
        selectedStatusEl.textContent = "The requested resume is not available. Select an available resume before running matching.";
      }
    }

  } catch (err) {
    selectorEl.dataset.state = "error";
    selectorEl.innerHTML = `<p class="error-inline">Failed to load resumes: ${escapeHtml(err.message)}</p>`;
  }

  
  const matchBtn = document.getElementById("match-btn");

  matchBtn.addEventListener("click", async () => {
    if (!selectedResumeId) {
      showMessage(messageEl, "Please select a resume first.");
      return;
    }

    hideMessage(messageEl);
    const requestResumeId = selectedResumeId;
    resultsSection.dataset.state = "loading";
    resultsSection.style.display = "block";
    resultsSummary.textContent = "Matching the selected resume against available jobs…";
    resultsList.innerHTML = "";
    matchBtn.disabled = true;
    matchBtn.querySelector(".btn-text").textContent = "Matching…";
    matchBtn.querySelector(".spinner").style.display = "inline-block";

    try {
      const results = await apiRequest(`/match/${selectedResumeId}?limit=5`, {
        method: "POST",
        auth: true,
      });
      if (selectedResumeId !== requestResumeId || results.some((result) => result.resume_id != null && result.resume_id !== requestResumeId)) return;
      renderResults(results);
      showMessage(messageEl, `Matching completed for selected resume: ${selectedResumeLabel}.`, "success");
    } catch (err) {
      resultsSection.dataset.state = "error";
      resultsSummary.textContent = "Matching could not be completed for the selected resume.";
      resultsList.innerHTML = "";
      showMessage(messageEl, err.message);
    } finally {
      matchBtn.disabled = false;
      matchBtn.querySelector(".btn-text").textContent = "Run Job Matching";
      matchBtn.querySelector(".spinner").style.display = "none";
    }
  });
});




function renderResults(results) {
  const section = document.getElementById("results-section");
  section.dataset.state = results.length ? "ready" : "empty";
  const summaryEl = document.getElementById("results-summary");
  const listEl = document.getElementById("match-results");

  section.style.display = "block";

  if (results.length === 0) {
    summaryEl.textContent = "No suitable job matches were found from the available open jobs.";
    listEl.innerHTML = "";
    return;
  }

  const topResults = results.slice(0, 5);
  summaryEl.textContent = `Showing ${topResults.length} suitable job(s), ranked by deterministic compatibility score.`;

  listEl.innerHTML = topResults.map((r, i) => {
    const scoreClass = r.match_score >= 70 ? "score-high" : r.match_score >= 40 ? "score-mid" : "score-low";
    const rank = i + 1;

    return `
      <div class="match-card ${scoreClass}">
        <div class="match-card-rank">#${rank}</div>
        <div class="match-card-score-ring">
          <svg viewBox="0 0 36 36" class="score-circle">
            <path class="score-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            <path class="score-fill" stroke-dasharray="${r.match_score}, 100"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
          </svg>
          <span class="score-value">${Math.round(r.match_score)}%</span>
        </div>
        <div class="match-card-body">
          <h3 class="match-card-title">${escapeHtml(r.job.title)}</h3>
          <div class="match-card-meta">
            ${r.job.company ? `<span>${escapeHtml(r.job.company)}</span>` : ''}
            ${r.job.location ? `<span>${escapeHtml(r.job.location)}</span>` : ''}
          </div>
          <p class="match-card-explanation">${escapeHtml(r.explanation)}</p>
          <div class="match-skills-row">
            <span class="match-skills-label">Matched:</span>
            ${((r.matched_skills || []).length ? r.matched_skills : ["None"]).map(s => `<span class="tag tech small">${escapeHtml(s)}</span>`).join('')}
          </div>
          <div class="match-skills-row">
            <span class="match-skills-label">Partial:</span>
            ${((r.partially_matched || []).length ? r.partially_matched : ["None"]).map(s => `<span class="tag small">${escapeHtml(s)}</span>`).join('')}
          </div>
          <div class="match-skills-row">
            <span class="match-skills-label">Missing skills:</span>
            ${((r.missing_skills || []).length ? r.missing_skills : ["None"]).map(s => `<span class="tag missing small">${escapeHtml(s)}</span>`).join('')}
          </div>
          <div class="match-skills-row">
            <span class="match-skills-label">Missing requirements:</span>
            ${((r.missing_requirements || []).length ? r.missing_requirements : ["None"]).map(s => `<span class="tag missing small">${escapeHtml(s)}</span>`).join('')}
          </div>
          <div class="match-suggestions"><strong>Improvement suggestions:</strong> ${((r.improvement_suggestions || []).length ? r.improvement_suggestions : ["No additional grounded suggestion."]).map(s => escapeHtml(s)).join(' ')}</div>
          <a class="toggle-btn" href="resume.html?id=${encodeURIComponent(window.selectedMatchingResumeId)}&job_id=${encodeURIComponent(r.job.id)}&source=matching">Improve for this job</a>
          <button type="button" class="toggle-btn apply-btn" onclick="applyMatchedJob(${r.job.id})" ${r.job.is_open ? "" : "disabled"}>${r.job.is_open ? "Apply" : "Closed"}</button>
        </div>
      </div>
    `;
  }).join("");
}

async function applyMatchedJob(jobId) {
  const resumeId = window.selectedMatchingResumeId;
  const messageEl = document.getElementById("match-message");
  if (!resumeId) {
    showMessage(messageEl, "Select a resume before recording an application.");
    return;
  }
  try {
    await apiRequest(`/jobs/${jobId}/apply?resume_id=${encodeURIComponent(resumeId)}`, { method: "POST", auth: true });
    showMessage(messageEl, "تم التقديم بنجاح", "success");
  } catch (err) {
    showMessage(messageEl, err.message);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
