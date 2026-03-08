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
  meaningfulText,
  withButtonLoading,
} from "./utils.js";

const FIELD_IDS = {
  name: "gen-name",
  email: "gen-email",
  github: "gen-github",
  linkedin: "gen-linkedin",
  skills: "gen-skills",
  projects: "gen-projects",
};

function generatorBanner() {
  return $("generator-banner");
}

function readFormValues() {
  return {
    name: $(FIELD_IDS.name)?.value.trim() || "",
    email: $(FIELD_IDS.email)?.value.trim() || "",
    githubRaw: $(FIELD_IDS.github)?.value.trim() || "",
    linkedinRaw: $(FIELD_IDS.linkedin)?.value.trim() || "",
    skills: splitCsv($(FIELD_IDS.skills)?.value || ""),
    projects: splitCsv($(FIELD_IDS.projects)?.value || ""),
    theme: $("gen-theme")?.value || "modern",
    role: $("gen-role")?.value || "",
    deepMode: Boolean($("gen-deep-mode")?.checked),
  };
}

function ensureFieldErrorNode(fieldId) {
  const input = $(fieldId);
  if (!input) return null;
  let errorNode = $(`${fieldId}-error`);
  if (!errorNode) {
    errorNode = document.createElement("div");
    errorNode.id = `${fieldId}-error`;
    errorNode.className = "field-error";
    errorNode.hidden = true;
    input.insertAdjacentElement("afterend", errorNode);
  }
  return errorNode;
}

function setFieldError(fieldId, message = "") {
  const input = $(fieldId);
  const errorNode = ensureFieldErrorNode(fieldId);
  if (!input || !errorNode) return;

  if (!message) {
    errorNode.hidden = true;
    errorNode.textContent = "";
    input.classList.remove("input-invalid");
    input.setAttribute("aria-invalid", "false");
    return;
  }

  errorNode.hidden = false;
  errorNode.textContent = message;
  input.classList.add("input-invalid");
  input.setAttribute("aria-invalid", "true");
}

function applyFieldErrors(errors = {}) {
  Object.values(FIELD_IDS).forEach((fieldId) => setFieldError(fieldId, ""));
  Object.entries(errors).forEach(([field, message]) => {
    const fieldId = FIELD_IDS[field];
    if (fieldId) setFieldError(fieldId, message);
  });
}

function validateForm(values) {
  const errors = {};

  if (!meaningfulText(values.name, { minLetters: 2, minUniqueLetters: 2 }) || values.name.length > 80) {
    errors.name = "Enter a valid name.";
  }

  if (!validEmail(values.email)) {
    errors.email = "Enter a valid email.";
  }

  const github = normalizeGithubInput(values.githubRaw);
  if (!github.ok) {
    errors.github = "Enter a valid GitHub username or URL.";
  }

  if (!values.linkedinRaw) {
    errors.linkedin = "Enter a valid LinkedIn username or URL.";
  }
  const linkedin = normalizeLinkedInInput(values.linkedinRaw);
  if (!linkedin.ok) {
    errors.linkedin = "Enter a valid LinkedIn username or URL.";
  }

  const meaningfulSkills = values.skills.filter((item) => meaningfulText(item));
  const meaningfulProjects = values.projects.filter((item) => meaningfulText(item, { minLetters: 4, minUniqueLetters: 3 }));

  return {
    ok: Object.keys(errors).length === 0,
    errors,
    github: github.ok ? github.value : "",
    linkedin: linkedin.ok ? linkedin.value : "",
    linkedinUrl: linkedin.ok ? (linkedin.profileUrl || "") : "",
    skills: meaningfulSkills,
    projects: meaningfulProjects,
  };
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
  applyFieldErrors(validation.errors);
  generateBtn.disabled = !validation.ok;
}

function renderResult(portfolio, saveMessage, linkedinUrl = "") {
  const result = $("generator-result");
  if (!result) return;
  const headline = portfolio.hero?.content?.headline || "Portfolio generated";
  const topSkills = (portfolio.skills?.content?.highlighted || []).slice(0, 6);
  const projectCount = (portfolio.projects?.content?.items || []).length;
  result.innerHTML = `
    <h3>Preview Ready</h3>
    <p><strong>Headline:</strong> ${headline}</p>
    <p><strong>Theme:</strong> ${portfolio.theme}</p>
    <p><strong>Projects:</strong> ${projectCount}</p>
    <p><strong>Top Skills:</strong> ${topSkills.join(", ") || "N/A"}</p>
    <p><strong>LinkedIn:</strong> ${linkedinUrl || "Not provided"}</p>
    <p><strong>Status:</strong> ${saveMessage}</p>
  `;
  result.hidden = false;
}

function mapServerErrorToField(message) {
  const text = (message || "").toLowerCase();
  if (text.includes("email")) return { email: "Enter a valid email." };
  if (text.includes("github")) return { github: "Enter a valid GitHub username or URL." };
  if (text.includes("linkedin")) return { linkedin: "Enter a valid LinkedIn username or URL." };
  if (text.includes("skills")) return { skills: "Please enter meaningful skills." };
  if (text.includes("project")) return { projects: "Please enter meaningful project information." };
  if (text.includes("name")) return { name: "Enter a valid name." };
  return {};
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

  Object.values(FIELD_IDS).forEach((id) => {
    ensureFieldErrorNode(id);
    $(id)?.addEventListener("input", () => {
      hideBanner(generatorBanner());
      updateSubmitDisabled();
    });
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
      applyFieldErrors(validation.errors);
      if (!validation.ok) {
        setExportButtonsEnabled(false);
        return;
      }

      if (validation.linkedinUrl && $(FIELD_IDS.linkedin)) {
        $(FIELD_IDS.linkedin).value = validation.linkedinUrl;
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
        manual_input: {
          name: values.name,
          email: values.email,
          github: values.githubRaw,
          linkedin: values.linkedinRaw,
          skills: validation.skills,
          projects: validation.projects,
        },
      });

      const saved = await saveResume({
        title: `${values.name || profilePayload.profile.name || validation.github} Portfolio`,
        status: "draft",
        portfolio,
      });

      setState({ generatorResult: portfolio });
      setExportButtonsEnabled(true);
      renderResult(portfolio, saved.message, validation.linkedinUrl);
      showBanner(generatorBanner(), "Portfolio generated and saved successfully.", "success");
      showBanner($("global-banner"), "Portfolio generated and saved successfully.", "success");
    })
      .catch((error) => {
        const fieldError = mapServerErrorToField(error.message);
        if (Object.keys(fieldError).length > 0) {
          applyFieldErrors(fieldError);
          hideBanner(generatorBanner());
        } else {
          showBanner(generatorBanner(), error.message, "error");
          showBanner($("global-banner"), error.message, "error");
        }
        setExportButtonsEnabled(Boolean(state.generatorResult));
      })
      .finally(() => {
        updateSubmitDisabled();
      });
  });
}
