document.addEventListener("DOMContentLoaded", () => {
  if (Auth.isLoggedIn()) {
    window.location.href = "dashboard.html";
    return;
  }

  const form = document.getElementById("register-form");
  const messageEl = document.getElementById("message");
  const submitBtn = document.getElementById("submit-btn");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage(messageEl);

    const full_name = document.getElementById("full_name").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    if (!email || !password) {
      showMessage(messageEl, "Please fill in email and password.");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Creating account…";

    try {
      await apiRequest("/auth/register", {
        method: "POST",
        body: { email, password, full_name: full_name || null },
      });

      
      const loginData = await apiRequest("/auth/login", {
        method: "POST",
        body: { email, password },
      });
      Auth.setToken(loginData.access_token);
      showMessage(messageEl, "Account created! Redirecting…", "success");
      setTimeout(() => (window.location.href = "dashboard.html"), 400);
    } catch (err) {
      showMessage(messageEl, err.message);
      submitBtn.disabled = false;
      submitBtn.textContent = "Create account";
    }
  });
});
