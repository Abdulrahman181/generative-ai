let canManageJobs = false;
let selectedResumeId = null;
let eligibleJobIds = new Set();
let recommendationsByJobId = new Map();

 document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.isLoggedIn()) {
    window.location.href = "login.html";
    return;
  }

  const messageEl = document.getElementById("jobs-message");
  const params = new URLSearchParams(window.location.search);
  selectedResumeId = Number.parseInt(params.get("resume_id") || params.get("id") || "", 10) || AppState.getResumeId();
  try {
    const user = await apiRequest("/auth/me", { auth: true });
    canManageJobs = Boolean(user.is_admin);
    document.getElementById("add-job-section").style.display = canManageJobs ? "block" : "none";
  } catch (err) {
    Auth.clearToken();
    window.location.href = "login.html";
    return;
  }

  await loadApplicationResumes();
  await loadEligibleMatches();
  await loadJobs();

  document.getElementById("logout-btn").addEventListener("click", async () => {
    try {
      await apiRequest("/auth/logout", { method: "POST", auth: true });
    } catch (err) {
      showMessage(messageEl, err.message);
    } finally {
      Auth.clearToken();
      window.location.href = "login.html";
    }
  });

  const toggleBtn = document.getElementById("toggle-add-job");
  const formWrap = document.getElementById("add-job-form-wrap");
  document.getElementById("cancel-add-job").addEventListener("click", () => {
    formWrap.style.display = "none";
    toggleBtn.style.display = "inline-block";
    document.getElementById("add-job-form").reset();
  });
  toggleBtn.addEventListener("click", () => {
    formWrap.style.display = "block";
    toggleBtn.style.display = "none";
  });

  document.getElementById("add-job-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage(messageEl);
    const title = document.getElementById("job-title").value.trim();
    const company = document.getElementById("job-company").value.trim() || null;
    const location = document.getElementById("job-location").value.trim() || null;
    const description = document.getElementById("job-description").value.trim();
    const skills = document.getElementById("job-skills").value.trim();
    const preferredSkills = document.getElementById("job-preferred-skills").value.trim();
    const experienceYears = document.getElementById("job-experience-years").value.trim() || null;
    const educationRequired = document.getElementById("job-education-required").value.trim() || null;
    const deadline = document.getElementById("job-deadline").value;
    const maxApplications = document.getElementById("job-max-applications").value;
    if (!title || !description) {
      showMessage(messageEl, "Title and description are required.");
      return;
    }
    const addBtn = document.getElementById("add-job-btn");
    addBtn.disabled = true;
    addBtn.textContent = "Creating...";
    try {
      await apiRequest("/jobs", {
        method: "POST",
        body: {
          title,
          company,
          location,
          description,
          skills_required: splitSkills(skills),
          skills_preferred: splitSkills(preferredSkills),
          experience_years: experienceYears,
          education_required: educationRequired,
          application_deadline: deadline ? new Date(deadline).toISOString() : null,
          max_applications: maxApplications ? Number(maxApplications) : null,
        },
        auth: true,
      });
      showMessage(messageEl, "Job posting created successfully.", "success");
      document.getElementById("add-job-form").reset();
      formWrap.style.display = "none";
      toggleBtn.style.display = "inline-block";
      await loadJobs();
    } catch (err) {
      showMessage(messageEl, err.message);
    } finally {
      addBtn.disabled = false;
      addBtn.textContent = "Create Job";
    }
  });

  const searchBtn = document.getElementById("search-btn");
  const clearSearch = document.getElementById("clear-search");
  searchBtn.addEventListener("click", async () => {
    const q = document.getElementById("search-q").value.trim();
    const location = document.getElementById("search-location").value.trim();
    const skill = document.getElementById("search-skill").value.trim();
    if (!q && !location && !skill) {
      await loadJobs();
      clearSearch.style.display = "none";
      return;
    }
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (location) params.set("location", location);
    if (skill) params.set("skill", skill);
    try {
      renderJobs(await apiRequest(`/jobs/search?${params}`, { auth: true }), true);
      clearSearch.style.display = "inline-block";
    } catch (err) {
      showMessage(messageEl, err.message);
    }
  });
  document.querySelectorAll(".search-field input").forEach((input) => {
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        searchBtn.click();
      }
    });
  });
  clearSearch.addEventListener("click", async () => {
    document.getElementById("search-q").value = "";
    document.getElementById("search-location").value = "";
    document.getElementById("search-skill").value = "";
    clearSearch.style.display = "none";
    await loadJobs();
  });

  const editModal = document.getElementById("edit-modal");
  document.getElementById("cancel-edit").addEventListener("click", () => {
    editModal.style.display = "none";
  });
  editModal.addEventListener("click", (event) => {
    if (event.target === editModal) editModal.style.display = "none";
  });
  document.getElementById("edit-job-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage(messageEl);
    const jobId = document.getElementById("edit-job-id").value;
    const deadline = document.getElementById("edit-deadline").value;
    const maxApplications = document.getElementById("edit-max-applications").value;
    const payload = {
      title: document.getElementById("edit-title").value.trim(),
      company: document.getElementById("edit-company").value.trim() || null,
      location: document.getElementById("edit-location").value.trim() || null,
      description: document.getElementById("edit-description").value.trim(),
      skills_required: splitSkills(document.getElementById("edit-skills").value.trim()),
      skills_preferred: splitSkills(document.getElementById("edit-preferred-skills").value.trim()),
      experience_years: document.getElementById("edit-experience-years").value.trim() || null,
      education_required: document.getElementById("edit-education-required").value.trim() || null,
      application_deadline: deadline ? new Date(deadline).toISOString() : null,
      max_applications: maxApplications ? Number(maxApplications) : null,
    };
    try {
      await apiRequest(`/jobs/${jobId}`, { method: "PUT", body: payload, auth: true });
      showMessage(messageEl, "Job updated successfully.", "success");
      editModal.style.display = "none";
      await loadJobs();
    } catch (err) {
      showMessage(messageEl, err.message);
    }
  });
});

async function loadApplicationResumes() {
  try {
    const resumes = await apiRequest("/resumes", { auth: true });
    const select = document.getElementById("application-resume");
    const wrapper = document.getElementById("application-resume-wrap");
    select.innerHTML = `<option value="">Select a CV before applying</option>${resumes.map((resume) => `<option value="${resume.id}">${escapeHtml(resume.original_filename)}</option>`).join("")}`;
    if (!resumes.some((resume) => resume.id === selectedResumeId)) selectedResumeId = null;
    select.value = selectedResumeId ? String(selectedResumeId) : "";
    AppState.setResumeId(selectedResumeId);
    select.addEventListener("change", async () => {
      selectedResumeId = Number.parseInt(select.value || "", 10) || null;
      AppState.setResumeId(selectedResumeId);
      AppState.clearJobId();
      await loadEligibleMatches();
      await loadJobs();
    });
    wrapper.style.display = resumes.length ? "block" : "none";
    const matchStatus = document.getElementById("jobs-match-status");
    if (matchStatus) matchStatus.textContent = resumes.length
      ? (selectedResumeId ? "Loading the top-five recommendations for the selected CV…" : "Select an analyzed CV to load the top-five job recommendations and unlock Apply.")
      : "Upload and analyze a CV to load job recommendations and unlock Apply.";
  } catch (err) {
    document.getElementById("application-resume-wrap").style.display = "none";
  }
}

async function loadEligibleMatches() {
  eligibleJobIds = new Set();
  recommendationsByJobId = new Map();
  const matchStatus = document.getElementById("jobs-match-status");
  if (!selectedResumeId) {
    if (matchStatus) matchStatus.textContent = "Select an analyzed CV to load the top-five job recommendations and unlock Apply.";
    return;
  }
  try {
    const matches = await apiRequest(`/match/${encodeURIComponent(selectedResumeId)}?limit=5`, { auth: true });
    const topMatches = matches.slice(0, 5);
    eligibleJobIds = new Set(topMatches.map((match) => match.job.id));
    recommendationsByJobId = new Map(topMatches.map((match) => [match.job.id, match]));
    if (matchStatus) matchStatus.textContent = topMatches.length
      ? `Showing the top ${topMatches.length} recommendations for the selected CV. Apply is available only for these jobs.`
      : "No positive matches were found for this CV.";
  } catch (_) {
    eligibleJobIds = new Set();
    recommendationsByJobId = new Map();
    if (matchStatus) matchStatus.textContent = "Matching is unavailable for this CV right now. Apply remains locked until matching succeeds.";
  }
}

async function loadJobs() {
  try {
    renderJobs(await apiRequest("/jobs", { auth: true }), false);
  } catch (err) {
    document.getElementById("jobs-list").innerHTML = `<p class="error-inline">Failed to load jobs: ${escapeHtml(err.message)}</p>`;
  }
}

function renderJobs(jobs, isSearch) {
  const listEl = document.getElementById("jobs-list");
  const countEl = document.getElementById("jobs-count");
  const headingEl = document.getElementById("jobs-heading");
  const emptyEl = document.getElementById("jobs-empty");
  countEl.textContent = jobs.length;
  headingEl.textContent = isSearch ? "Search Results" : "All Jobs";
  if (jobs.length === 0) {
    if (emptyEl) {
      emptyEl.style.display = "block";
      emptyEl.textContent = isSearch ? "No jobs match your search criteria." : (canManageJobs ? "No job postings yet. Add one above to get started." : "No job postings available.");
      listEl.innerHTML = "";
      listEl.appendChild(emptyEl);
    } else {
      listEl.innerHTML = `<p class="empty-state">${escapeHtml(isSearch ? "No jobs match your search criteria." : (canManageJobs ? "No job postings yet. Add one above to get started." : "No job postings available."))}</p>`;
    }
    return;
  }
  if (emptyEl) emptyEl.style.display = "none";
  listEl.innerHTML = jobs.map((job) => {
    const status = job.is_open ? "Open" : "Closed";
    const remaining = job.applications_remaining === null ? "No application limit" : `${job.applications_remaining} applications remaining`;
    const canApply = job.is_open && selectedResumeId && eligibleJobIds.has(job.id);
    const match = recommendationsByJobId.get(job.id);
    const recommendation = match ? `<div class="job-card-recommendation"><strong>Top match recommendation: ${Math.round(match.match_score)}%</strong><p>${escapeHtml(match.explanation)}</p>${match.missing_requirements && match.missing_requirements.length ? `<div class="meta">Focus next on: ${escapeHtml(match.missing_requirements.join(", "))}</div>` : ""}<a class="toggle-btn" href="resume.html?id=${encodeURIComponent(selectedResumeId)}&job_id=${encodeURIComponent(job.id)}&source=jobs">Improve for this job</a></div>` : "";
    const applyButton = canApply
      ? `<button class="toggle-btn apply-btn" onclick="applyToJob(${job.id})">Apply</button>`
      : `<span class="job-status ${job.is_open ? "not-eligible" : "closed"}">${job.is_open ? (selectedResumeId ? "Outside top 5" : "Match a CV to apply") : "Closed"}</span>`;
    const manageActions = canManageJobs ? `<div class="job-card-actions"><button class="icon-btn edit-btn" title="Edit" onclick="openEditModal(${job.id})">Edit</button><button class="icon-btn delete-btn" title="Delete" onclick="deleteJob(${job.id})">Delete</button></div>` : "";
    return `<div class="job-card ${job.is_open ? "" : "job-closed"}" data-id="${job.id}">
      <div class="job-card-header"><div><h3 class="job-card-title">${escapeHtml(job.title)}</h3><div class="job-card-meta">${job.company ? `<span>${escapeHtml(job.company)}</span>` : ""}${job.location ? `<span>${escapeHtml(job.location)}</span>` : ""}</div></div>${manageActions}</div>
      ${job.skills_required && job.skills_required.length ? `<div class="job-card-skills"><span class="job-skill-label">Required:</span>${job.skills_required.map((skill) => `<span class="tag tech">${escapeHtml(skill)}</span>`).join("")}</div>` : ""}
      ${job.skills_preferred && job.skills_preferred.length ? `<div class="job-card-skills"><span class="job-skill-label">Preferred:</span>${job.skills_preferred.map((skill) => `<span class="tag">${escapeHtml(skill)}</span>`).join("")}</div>` : ""}
      ${job.experience_years || job.education_required ? `<div class="job-card-requirements">${job.experience_years ? `<span>Experience: ${escapeHtml(job.experience_years)}</span>` : ""}${job.education_required ? `<span>Education: ${escapeHtml(job.education_required)}</span>` : ""}</div>` : ""}
      <div class="job-card-date">${status} | ${job.application_count} applications | ${remaining}${job.application_deadline ? ` | Deadline: ${formatDate(job.application_deadline)}` : ""}</div>
      ${recommendation}
      <div class="job-card-actions">${applyButton}</div>
    </div>`;
  }).join("");
}

async function applyToJob(jobId) {
  const resumeId = document.getElementById("application-resume").value;
  const messageEl = document.getElementById("jobs-message");
  if (!resumeId || !eligibleJobIds.has(Number(jobId))) {
    showMessage(messageEl, "Applications are limited to the top five matching jobs for the selected resume.");
    return;
  }
  try {
    await apiRequest(`/jobs/${jobId}/apply?resume_id=${encodeURIComponent(resumeId)}`, { method: "POST", auth: true });
    showMessage(messageEl, "Applied successfully", "success");
    await loadJobs();
  } catch (err) {
    showMessage(messageEl, err.message);
  }
}

async function openEditModal(jobId) {
  try {
    const job = await apiRequest(`/jobs/${jobId}`, { auth: true });
    document.getElementById("edit-job-id").value = job.id;
    document.getElementById("edit-title").value = job.title;
    document.getElementById("edit-company").value = job.company || "";
    document.getElementById("edit-location").value = job.location || "";
    document.getElementById("edit-description").value = job.description;
    document.getElementById("edit-skills").value = (job.skills_required || []).join(", ");
    document.getElementById("edit-preferred-skills").value = (job.skills_preferred || []).join(", ");
    document.getElementById("edit-experience-years").value = job.experience_years || "";
    document.getElementById("edit-education-required").value = job.education_required || "";
    document.getElementById("edit-deadline").value = toLocalDateTime(job.application_deadline);
    document.getElementById("edit-max-applications").value = job.max_applications || "";
    document.getElementById("edit-modal").style.display = "flex";
  } catch (err) {
    showMessage(document.getElementById("jobs-message"), err.message);
  }
}

async function deleteJob(jobId) {
  if (!confirm("Delete this job posting? This cannot be undone.")) return;
  try {
    await apiRequest(`/jobs/${jobId}`, { method: "DELETE", auth: true });
    await loadJobs();
    showMessage(document.getElementById("jobs-message"), "Job deleted.", "success");
  } catch (err) {
    showMessage(document.getElementById("jobs-message"), err.message);
  }
}

function splitSkills(value) {
  return value ? value.split(",").map((skill) => skill.trim()).filter(Boolean) : [];
}

function formatDate(value) {
  return new Date(value).toLocaleString("en-US", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function toLocalDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}
