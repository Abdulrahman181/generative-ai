"use strict";

(function () {
  const token = Auth.getToken();
  if (!token) { window.location.href = "login.html"; return; }

  const messagesEl = document.getElementById("chatMessages");
  const formEl = document.getElementById("chatForm");
  const inputEl = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const resumeSel = document.getElementById("resumeSelect");
  const jobSel = document.getElementById("jobSelect");
  const selectedResumeStatus = document.getElementById("selected-resume-status");
  const selectedJobStatus = document.getElementById("selected-job-status");
  const clearBtn = document.getElementById("clearHistoryBtn");
  const logoutLink = document.getElementById("logout-btn");
  const params = new URLSearchParams(window.location.search);

  let selectedResumeId = Number.parseInt(params.get("resume_id") || params.get("id") || "", 10) || AppState.getResumeId();
  let selectedJobId = Number.parseInt(params.get("job_id") || "", 10) || AppState.getJobId();

  function escapeHtml(text) {
    const d = document.createElement("div");
    d.textContent = text;
    return d.innerHTML;
  }

  function renderMarkdown(text) {
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
    html = html.replace(/^• (.+)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");
    html = html.replace(/\n/g, "<br>");
    return html;
  }

  function addMessage(role, content) {
    const wrapper = document.createElement("div");
    wrapper.className = `chat-msg chat-msg--${role}`;

    const avatar = document.createElement("div");
    avatar.className = "chat-msg__avatar";
    avatar.textContent = role === "user" ? "You" : "AI";

    const bubble = document.createElement("div");
    bubble.className = "chat-msg__bubble";
    bubble.innerHTML = role === "user" ? `<p>${escapeHtml(content)}</p>` : renderMarkdown(content);

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    messagesEl.appendChild(wrapper);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function addTypingIndicator() {
    const wrapper = document.createElement("div");
    wrapper.className = "chat-msg chat-msg--assistant";
    wrapper.id = "typingIndicator";

    const avatar = document.createElement("div");
    avatar.className = "chat-msg__avatar";
    avatar.textContent = "AI";

    const bubble = document.createElement("div");
    bubble.className = "chat-msg__bubble chat-msg__typing";
    bubble.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    messagesEl.appendChild(wrapper);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function removeTypingIndicator() {
    const el = document.getElementById("typingIndicator");
    if (el) el.remove();
  }

  function syncStateToUrl() {
    const url = new URL(window.location.href);
    if (selectedResumeId) url.searchParams.set("resume_id", String(selectedResumeId));
    else url.searchParams.delete("resume_id");
    if (selectedJobId) url.searchParams.set("job_id", String(selectedJobId));
    else url.searchParams.delete("job_id");
    window.history.replaceState({}, "", url);
  }

  function updateScopeStatus() {
    const resumeOption = resumeSel.options[resumeSel.selectedIndex];
    selectedResumeStatus.textContent = selectedResumeId
      ? `Selected resume: ${resumeOption ? resumeOption.textContent : `Resume ${selectedResumeId}`}`
      : "No resume selected; resume-specific questions require an explicit selection. Profile and stored job data remain available.";
    const jobOption = jobSel.options[jobSel.selectedIndex];
    selectedJobStatus.textContent = selectedJobId
      ? `Selected job: ${jobOption ? jobOption.textContent : `Job ${selectedJobId}`}`
      : "No job selected; job-specific context is disabled.";
  }

  async function loadResumes() {
    try {
      const resumes = await api("GET", "/api/resumes");
      resumeSel.innerHTML = '<option value="">No resume selected</option>';
      resumes.forEach(function (r) {
        const opt = document.createElement("option");
        opt.value = r.id;
        opt.textContent = r.original_filename + (r.summary ? " — " + r.summary.slice(0, 60) : "");
        resumeSel.appendChild(opt);
      });
      if (!resumes.some((resume) => resume.id === selectedResumeId)) selectedResumeId = null;
      resumeSel.value = selectedResumeId ? String(selectedResumeId) : "";
      if (selectedResumeId) AppState.setResumeId(selectedResumeId);
      else AppState.setResumeId(null);
      updateScopeStatus();
      resumeSel.addEventListener("change", async function () {
        selectedResumeId = Number.parseInt(resumeSel.value || "", 10) || null;
        AppState.setResumeId(selectedResumeId);
        // A job conversation is scoped to the selected CV; do not carry it across CVs.
        selectedJobId = null;
        AppState.clearJobId();
        jobSel.value = "";
        syncStateToUrl();
        updateScopeStatus();
        messagesEl.innerHTML = "";
        await loadHistory();
      });
    } catch (e) {
      selectedResumeStatus.textContent = "Resume list is unavailable; resume-specific questions require an explicit selection.";
      selectedResumeId = null;
      AppState.setResumeId(null);
    }
  }

  async function loadJobs() {
    try {
      const jobs = await api("GET", "/api/jobs");
      jobSel.innerHTML = '<option value="">No job selected</option>';
      jobs.forEach(function (job) {
        const opt = document.createElement("option");
        opt.value = job.id;
        opt.textContent = `${job.title}${job.company ? " — " + job.company : ""}`;
        jobSel.appendChild(opt);
      });
      if (!jobs.some((job) => job.id === selectedJobId)) selectedJobId = null;
      jobSel.value = selectedJobId ? String(selectedJobId) : "";
      if (selectedJobId) AppState.setJobId(selectedJobId);
      else AppState.clearJobId();
      updateScopeStatus();
      jobSel.addEventListener("change", async function () {
        selectedJobId = Number.parseInt(jobSel.value || "", 10) || null;
        AppState.setJobId(selectedJobId);
        syncStateToUrl();
        updateScopeStatus();
        messagesEl.innerHTML = "";
        await loadHistory();
      });
    } catch (e) {
      jobSel.innerHTML = '<option value="">No job selected</option>';
      selectedJobId = null;
      AppState.clearJobId();
      updateScopeStatus();
    }
  }

  async function loadHistory() {
    try {
      const query = new URLSearchParams();
      if (selectedResumeId) query.set("resume_id", String(selectedResumeId));
      if (selectedJobId) query.set("job_id", String(selectedJobId));
      const suffix = query.toString() ? `?${query.toString()}` : "";
      const history = await api("GET", `/api/chat/history${suffix}`);
      if (history.length > 0) history.forEach(function (msg) { addMessage(msg.role, msg.content); });
    } catch (e) {
      console.warn("Could not load history:", e);
    }
  }

  formEl.addEventListener("submit", async function (e) {
    e.preventDefault();
    const message = inputEl.value.trim();
    if (!message) return;

    inputEl.value = "";
    sendBtn.disabled = true;
    addMessage("user", message);
    addTypingIndicator();

    const body = { message: message };
    if (selectedResumeId) body.resume_id = selectedResumeId;
    if (selectedJobId) body.job_id = selectedJobId;

    try {
      const data = await api("POST", "/api/chat", body);
      removeTypingIndicator();
      addMessage("assistant", data.reply);

      if (data.sources && data.sources.length > 0) {
        const srcNote = document.createElement("div");
        srcNote.className = "chat-sources";
        srcNote.textContent = "Sources: " + data.sources.join(", ");
        messagesEl.appendChild(srcNote);
      }
    } catch (err) {
      removeTypingIndicator();
      addMessage("assistant", "Sorry, I encountered an error. Please try again.");
    }

    sendBtn.disabled = false;
    inputEl.focus();
  });

  clearBtn.addEventListener("click", async function () {
    if (!confirm("Clear chat history for the selected resume and job scope?")) return;
    try {
      const query = new URLSearchParams();
      if (selectedResumeId) query.set("resume_id", String(selectedResumeId));
      if (selectedJobId) query.set("job_id", String(selectedJobId));
      const suffix = query.toString() ? `?${query.toString()}` : "";
      await api("DELETE", `/api/chat/history${suffix}`);
      messagesEl.innerHTML = "";
      addMessage("assistant", "Chat history cleared for the selected resume and job scope.");
    } catch (e) {
      alert("Failed to clear history.");
    }
  });

  logoutLink.addEventListener("click", async function (e) {
    e.preventDefault();
    try { await api("POST", "/api/auth/logout"); } catch (_) { }
    Auth.clearToken();
    window.location.href = "login.html";
  });

  (async function init() {
    await loadResumes();
    await loadJobs();
    syncStateToUrl();
    messagesEl.innerHTML = "";
    await loadHistory();
  })();
})();
