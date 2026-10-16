document.addEventListener("DOMContentLoaded", () => {
  if (Auth.isLoggedIn()) {
    window.location.href = "dashboard.html";
    return;
  }

  const form = document.getElementById("login-form");
  const messageEl = document.getElementById("message");
  const submitBtn = document.getElementById("submit-btn");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage(messageEl);

    const identifier = document.getElementById("identifier").value.trim();
    const password = document.getElementById("password").value;

    if (!identifier || !password) {
      showMessage(messageEl, "Please fill in both username or email and password.");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Logging in…";

    try {
      const data = await apiRequest("/auth/login", {
        method: "POST",
        body: identifier.includes("@") ? { email: identifier, password } : { username: identifier, password },
      });
      Auth.setToken(data.access_token);
      showMessage(messageEl, "Logged in! Redirecting…", "success");
      setTimeout(() => (window.location.href = "dashboard.html"), 400);
    } catch (err) {
      showMessage(messageEl, err.message);
      submitBtn.disabled = false;
      submitBtn.textContent = "Log in";
    }
  });
});
