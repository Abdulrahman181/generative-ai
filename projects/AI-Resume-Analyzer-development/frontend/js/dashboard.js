
document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.isLoggedIn()) {
    window.location.href = "login.html";
    return;
  }

  
  try {
    const user = await apiRequest("/auth/me", { auth: true });
    document.getElementById("user-name").textContent = user.full_name || user.email;
    document.getElementById("user-email").textContent = user.email;
  } catch (err) {
    Auth.clearToken();
    window.location.href = "login.html";
    return;
  }

  
  document.getElementById("logout-btn").addEventListener("click", async () => {
    try {
      await apiRequest("/auth/logout", { method: "POST", auth: true });
    } catch (_) {
      
    } finally {
      Auth.clearToken();
      window.location.href = "login.html";
    }
  });

  
  await loadResumes();

  
  const uploadZone = document.getElementById("upload-zone");
  const fileInput = document.getElementById("resume-file");
  const filePreview = document.getElementById("file-preview");
  const fileName = document.getElementById("file-name");
  const clearBtn = document.getElementById("clear-file");
  const uploadBtn = document.getElementById("upload-btn");
  const uploadForm = document.getElementById("upload-form");
  const uploadMessage = document.getElementById("upload-message");

  
  uploadZone.addEventListener("click", () => fileInput.click());

  
  uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadZone.classList.add("drag-over");
  });
  uploadZone.addEventListener("dragleave", () => {
    uploadZone.classList.remove("drag-over");
  });
  uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.classList.remove("drag-over");
    if (e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      selectFile(e.dataTransfer.files[0]);
    }
  });

  
  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      selectFile(fileInput.files[0]);
    }
  });

  function selectFile(file) {
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx"].includes(ext)) {
      showMessage(uploadMessage, `Unsupported file format '.${ext}'. Please upload a PDF or DOCX file.`);
      return;
    }
    hideMessage(uploadMessage);
    fileName.textContent = file.name;
    filePreview.style.display = "flex";
    uploadZone.style.display = "none";
    uploadBtn.disabled = false;
  }

  clearBtn.addEventListener("click", () => {
    fileInput.value = "";
    filePreview.style.display = "none";
    uploadZone.style.display = "flex";
    uploadBtn.disabled = true;
    hideMessage(uploadMessage);
  });

  
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideMessage(uploadMessage);

    if (!fileInput.files.length) {
      showMessage(uploadMessage, "Please select a file first.");
      return;
    }

    uploadBtn.disabled = true;
    uploadBtn.querySelector(".btn-text").textContent = "Analyzing…";
    uploadBtn.querySelector(".spinner").style.display = "inline-block";

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
      const resume = await apiUpload("/resumes/upload", formData);
      showMessage(uploadMessage, "Resume analyzed successfully.", "success");

      
      fileInput.value = "";
      filePreview.style.display = "none";
      uploadZone.style.display = "flex";

      
      await loadResumes();

      
      setTimeout(() => {
        window.location.href = `resume.html?id=${resume.id}`;
      }, 800);

    } catch (err) {
      showMessage(uploadMessage, err.message);
    } finally {
      uploadBtn.disabled = false;
      uploadBtn.querySelector(".btn-text").textContent = "Analyze Resume";
      uploadBtn.querySelector(".spinner").style.display = "none";
    }
  });
});




async function loadResumes() {
  const listEl = document.getElementById("resumes-list");
  const countEl = document.getElementById("resume-count");
  try {
    const resumes = await apiRequest("/resumes", { auth: true });
    countEl.textContent = resumes.length;

    if (resumes.length === 0) {
      listEl.innerHTML = '<p class="empty-state" id="empty-state">No resumes uploaded yet. Upload one above to get started!</p>';
      return;
    }

    listEl.innerHTML = resumes.map((r) => `
      <div class="resume-card">
        <a href="resume.html?id=${r.id}" class="resume-card-link">
          <div class="resume-card-icon">${escapeHtml(r.file_type.toUpperCase())}</div>
          <div class="resume-card-body">
            <div class="resume-card-name">${escapeHtml(r.original_filename)}</div>
            <div class="resume-card-summary">${r.summary ? escapeHtml(r.summary.substring(0, 120)) + '…' : 'No summary available'}</div>
            <div class="resume-card-date">${new Date(r.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</div>
          </div>
          <div class="resume-card-arrow" aria-hidden="true"></div>
        </a>
        <button type="button" class="resume-delete" data-resume-id="${r.id}" aria-label="Delete ${escapeHtml(r.original_filename)}">X</button>
      </div>
    `).join("");

    listEl.querySelectorAll(".resume-delete").forEach((button) => {
      button.addEventListener("click", async (event) => {
        event.preventDefault();
        event.stopPropagation();
        const targetId = Number(event.currentTarget.dataset.resumeId);
        if (!Number.isInteger(targetId) || targetId <= 0) {
          showMessage(document.getElementById("upload-message"), "This resume could not be identified for deletion.");
          return;
        }
        if (!window.confirm("Delete this resume and its stored analysis?")) return;
        button.disabled = true;
        try {
          await apiRequest(`/resumes/${targetId}`, { method: "DELETE", auth: true });
          await loadResumes();
        } catch (err) {
          showMessage(document.getElementById("upload-message"), err.message);
          button.disabled = false;
        }
      });
    });

  } catch (err) {
    listEl.innerHTML = `<p class="error-inline">Failed to load resumes: ${escapeHtml(err.message)}</p>`;
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
