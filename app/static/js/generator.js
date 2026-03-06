import { fetchProfile, generatePortfolio } from "./api.js";
import { isAuthenticated, setState } from "./state.js";
import { $, hideBanner, normalizeGithubInput, normalizeLinkedInInput, showBanner, splitCsv, validEmail, withButtonLoading } from "./utils.js";

function generatorBanner() {
  return $("generator-banner");
}

function readFormValues() {
  return {
    name: $("gen-name")?.value.trim() || "",
    email: $("gen-email")?.value.trim() || "",
    githubRaw: $("gen-github")?.value.trim() || "",
    linkedinRaw: $("gen-linkedin")?.value.trim() || "",
    skills: splitCsv($("gen-skills")?.value || ""),
    projects: splitCsv($("gen-projects")?.value || ""),
    theme: $("gen-theme")?.value || "modern",
    role: $("gen-role")?.value || "",
    deepMode: Boolean($("gen-deep-mode")?.checked),
    performanceMode: Boolean($("gen-performance")?.checked),
    neonMode: Boolean($("gen-neon")?.checked),
  };
}

function validateForm(values) {
  if (!validEmail(values.email)) return { ok: false, message: "Enter a valid email." };
  const github = normalizeGithubInput(values.githubRaw);
  if (!github.ok) return github;
  const linkedin = normalizeLinkedInInput(values.linkedinRaw);
  if (!linkedin.ok) return linkedin;
  return { ok: true, github: github.value, linkedin: linkedin.value };
}

function updateSubmitDisabled() {
  const generateBtn = $("generate-btn");
  if (!generateBtn) return;
  const validation = validateForm(readFormValues());
  generateBtn.disabled = !validation.ok;
}

function renderResult(portfolio, values) {
  const result = $("generator-result");
  if (!result) return;
  const summary = {
    theme: portfolio.theme,
    headline: portfolio.hero?.content?.headline,
    role: values.role || "none",
    performance_mode: values.performanceMode,
    neon_mode: values.neonMode,
    skills: values.skills,
    projects: values.projects,
  };
  result.textContent = JSON.stringify(summary, null, 2);
  result.hidden = false;
}

export function initGenerator() {
  const form = $("generator-form");
  const generateBtn = $("generate-btn");
  if (!form || !generateBtn) return;

  ["gen-email", "gen-github", "gen-linkedin"].forEach((id) => {
    $(id)?.addEventListener("input", updateSubmitDisabled);
  });
  updateSubmitDisabled();

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    withButtonLoading(generateBtn, "Generating...", async () => {
      if (!isAuthenticated()) throw new Error("Login required.");

      hideBanner(generatorBanner());
      const values = readFormValues();
      const validation = validateForm(values);
      if (!validation.ok) throw new Error(validation.message);

      showBanner(generatorBanner(), "Loading profile data...", "info");
      const profilePayload = await fetchProfile({
        username: validation.github,
        linkedin_username: validation.linkedin || undefined,
      });

      profilePayload.profile.name = profilePayload.profile.name || values.name || null;
      profilePayload.profile.email = profilePayload.profile.email || values.email || null;

      showBanner(generatorBanner(), "Generating portfolio...", "info");
      const portfolio = await generatePortfolio({
        ...profilePayload,
        theme: values.theme,
        target_role: values.role || undefined,
        deep_mode: values.deepMode,
      });

      setState({ generatorResult: portfolio });
      renderResult(portfolio, values);
      showBanner(generatorBanner(), "Portfolio generated successfully.", "success");
      showBanner($("global-banner"), "Portfolio generated successfully.", "success");
    }).catch((error) => {
      showBanner(generatorBanner(), error.message, "error");
      showBanner($("global-banner"), error.message, "error");
    }).finally(() => {
      updateSubmitDisabled();
    });
  });
}
