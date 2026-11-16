const form = document.getElementById("form");
const urlInput = document.getElementById("url");
const submitBtn = document.getElementById("submit");
const errorEl = document.getElementById("error");
const resultEl = document.getElementById("result");
const shortInput = document.getElementById("short");
const copyBtn = document.getElementById("copy");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorEl.hidden = true;
  resultEl.hidden = true;
  submitBtn.disabled = true;
  try {
    const res = await fetch("/api/shorten", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: urlInput.value }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Invalid request.");
    shortInput.value = data.short_url;
    resultEl.hidden = false;
    copyBtn.textContent = "Copy";
  } catch (err) {
    errorEl.textContent = err.message || "Something went wrong.";
    errorEl.hidden = false;
  } finally {
    submitBtn.disabled = false;
  }
});

copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(shortInput.value);
  } catch {
    shortInput.select();
    document.execCommand("copy");
  }
  copyBtn.textContent = "Copied!";
});
