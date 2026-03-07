import { exportPortfolio, fetchProfile, generatePortfolio, saveResume } from "./api.js";
import { isAuthenticated, setState, state } from "./state.js";
import {
  $,
  contentDispositionFilename,
  downloadBlob,
  hideBanner,
  normalizeGithubInput,
  normalizeLinkedInInput,
  showBanner,
  splitCsv,
  validEmail,
  withButtonLoading,
} from "./utils.js";

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
  return { ok: true, github: github.value, linkedin: linkedin.value, linkedinUrl: linkedin.profileUrl || "" };
}

function setExportButtonsEnabled(enabled) {
  ["export-html-btn", "export-pdf-btn", "export-zip-btn"].forEach((id) => {
    const btn = $(id);
    if (btn) btn.disabled = !enabled;
  });
}

function updateSubmitDisabled() {
  const generateBtn = $("generate-btn");
  if (!generateBtn) return;
  const validation = validateForm(readFormValues());
  generateBtn.disabled = !validation.ok;
}

function renderResult(portfolio, values, saveMessage, linkedinUrl = "") {
  const result = $("generator-result");
  if (!result) return;
  const summary = {
    theme: portfolio.theme,
    headline: portfolio.hero?.content?.headline,
    role: values.role || "none",
    performance_mode: values.performanceMode,
    neon_mode: values.neonMode,
    linkedin_input: values.linkedinRaw || "",
    linkedin_resolved_url: linkedinUrl || "",
    linkedin_in_portfolio: portfolio.contact?.content?.linkedin || portfolio.about?.content?.linkedin || "",
    skills: values.skills,
    projects: values.projects,
    save_status: saveMessage,
  };
  result.textContent = JSON.stringify(summary, null, 2);
  result.hidden = false;
}

async function exportCurrentPortfolio(format) {
  if (!state.generatorResult) throw new Error("Generate a portfolio first.");
  const payload = {
    portfolio: state.generatorResult,
    template_id: state.generatorResult.theme || "modern",
    filename: `portfolio-${state.generatorResult.profile?.username || "resume"}`,
  };
  const response = await exportPortfolio(format, payload);
  const defaultName = `${payload.filename}.${format}`;
  const fileName = contentDispositionFilename(response.headers.get("content-disposition"), defaultName);
  const blob = await response.blob();
  downloadBlob(blob, fileName);
}

export function initGenerator() {
  const form = $("generator-form");
  const generateBtn = $("generate-btn");
  const exportHtmlBtn = $("export-html-btn");
  const exportPdfBtn = $("export-pdf-btn");
  const exportZipBtn = $("export-zip-btn");
  if (!form || !generateBtn) return;

  ["gen-email", "gen-github", "gen-linkedin"].forEach((id) => {
    $(id)?.addEventListener("input", updateSubmitDisabled);
  });

  exportHtmlBtn?.addEventListener("click", () =>
    withButtonLoading(exportHtmlBtn, "Exporting...", async () => {
      await exportCurrentPortfolio("html");
      showBanner($("global-banner"), "HTML exported.", "success");
    }).catch((error) => showBanner($("global-banner"), error.message, "error"))
  );

  exportPdfBtn?.addEventListener("click", () =>
    withButtonLoading(exportPdfBtn, "Exporting...", async () => {
      await exportCurrentPortfolio("pdf");
      showBanner($("global-banner"), "PDF exported.", "success");
    }).catch((error) => showBanner($("global-banner"), error.message, "error"))
  );

  exportZipBtn?.addEventListener("click", () =>
    withButtonLoading(exportZipBtn, "Exporting...", async () => {
      await exportCurrentPortfolio("zip");
      showBanner($("global-banner"), "ZIP exported.", "success");
    }).catch((error) => showBanner($("global-banner"), error.message, "error"))
  );

  updateSubmitDisabled();
  setExportButtonsEnabled(Boolean(state.generatorResult));

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    withButtonLoading(generateBtn, "Generating...", async () => {
      if (!isAuthenticated()) throw new Error("Login required.");

      hideBanner(generatorBanner());
      const values = readFormValues();
      const validation = validateForm(values);
      if (!validation.ok) throw new Error(validation.message);

      if (validation.linkedinUrl && $("gen-linkedin")) {
        $("gen-linkedin").value = validation.linkedinUrl;
      }

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

      const saved = await saveResume({
        title: `${values.name || profilePayload.profile.name || validation.github} Portfolio`,
        status: "draft",
        portfolio,
      });

      setState({ generatorResult: portfolio });
      setExportButtonsEnabled(true);
      renderResult(portfolio, values, saved.message, validation.linkedinUrl);
      showBanner(generatorBanner(), "Portfolio generated and saved successfully.", "success");
      showBanner($("global-banner"), "Portfolio generated and saved successfully.", "success");
    })
      .catch((error) => {
        setExportButtonsEnabled(Boolean(state.generatorResult));
        showBanner(generatorBanner(), error.message, "error");
        showBanner($("global-banner"), error.message, "error");
      })
      .finally(() => {
        updateSubmitDisabled();
      });
  });
}
