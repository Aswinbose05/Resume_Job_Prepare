/**
 * AI Resume Analyzer & Job Preparation System (CrewAI)
 * Clean, production-ready, resilient frontend application logic.
 */

let analysisData = null;
let currentMockQuestion = null;

// Defensive DOM Helpers (Guarantees zero null reference crashes)
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.innerText = (text !== undefined && text !== null) ? String(text) : "";
}

function setHtml(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = (html !== undefined && html !== null) ? String(html) : "";
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/^# (.*$)/gim, '<h1 class="text-base font-extrabold text-slate-900 dark:text-white mt-4 mb-2 border-b border-slate-300 dark:border-slate-700 pb-1">$1</h1>')
    .replace(/^## (.*$)/gim, '<h2 class="text-sm font-bold text-slate-900 dark:text-white mt-3.5 mb-1.5 border-b border-slate-200 dark:border-slate-800 pb-0.5">$1</h2>')
    .replace(/^### (.*$)/gim, '<h3 class="text-xs font-bold text-brand-600 dark:text-brand-400 mt-2.5 mb-1">$1</h3>')
    .replace(/^#### (.*$)/gim, '<h4 class="text-xs font-bold text-indigo-600 dark:text-indigo-400 mt-2 mb-1">$1</h4>')
    .replace(/^> (.*$)/gim, '<blockquote class="border-l-2 border-brand-500 pl-3 py-1 my-1.5 text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-900/50 rounded-r-lg italic text-[11px]">$1</blockquote>')
    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-slate-900 dark:text-white font-semibold">$1</strong>')
    .replace(/\*(.*?)\*/g, '<em class="text-slate-600 dark:text-slate-300">$1</em>')
    .replace(/`(.*?)`/g, '<code class="px-1 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-brand-700 dark:text-brand-300 font-mono text-[10px]">$1</code>')
    .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-brand-600 dark:text-brand-400 underline hover:text-brand-500 font-medium">$1</a>')
    .replace(/^\s*-\s+(.*$)/gim, '<li class="ml-4 list-disc text-slate-700 dark:text-slate-300">$1</li>')
    .replace(/^\s*\d+\.\s+(.*$)/gim, '<li class="ml-4 list-decimal text-slate-700 dark:text-slate-300">$1</li>')
    .replace(/\n\n/g, '<p class="mt-2"></p>')
    .replace(/\n/g, '<br/>');
}

function copyToClipboard(text, msg = "Copied to clipboard!") {
  if (!navigator.clipboard) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand('copy');
      alert(msg);
    } catch (err) {
      alert("Failed to copy text");
    }
    document.body.removeChild(textArea);
    return;
  }
  navigator.clipboard.writeText(text).then(() => {
    alert(msg);
  }).catch(() => {
    alert("Failed to copy text.");
  });
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  const savedTheme = localStorage.getItem("career_theme") || "light";
  if (savedTheme === "light") {
    document.documentElement.classList.remove("dark");
    document.getElementById("themeIcon")?.setAttribute("data-lucide", "sun");
  } else {
    document.documentElement.classList.add("dark");
    document.getElementById("themeIcon")?.setAttribute("data-lucide", "moon");
  }

  if (window.lucide) lucide.createIcons();
  setupDragAndDrop();
});

// Drag and drop setup for resume
function setupDragAndDrop() {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("resumeFileInput");
  if (!dropZone || !fileInput) return;

  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("border-brand-500", "bg-brand-50/30");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("border-brand-500", "bg-brand-50/30");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("border-brand-500", "bg-brand-50/30");
    if (e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      handleFileSelected({ target: fileInput });
    }
  });
}

function handleFileSelected(event) {
  const file = event.target.files[0];
  if (file) {
    const statusText = document.getElementById("fileStatusText");
    if (statusText) {
      statusText.innerText = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      statusText.classList.add("text-emerald-600", "dark:text-emerald-400", "font-bold");
    }
  }
}

// Tab navigation within Results
function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    const isActive = btn.dataset.tab === tabId;
    btn.classList.toggle("active", isActive);
    btn.classList.toggle("font-bold", isActive);
  });
  document.querySelectorAll(".tab-content").forEach(content => {
    content.classList.add("hidden");
  });
  const activeContent = document.getElementById(`tab-${tabId}`);
  if (activeContent) {
    activeContent.classList.remove("hidden");
    activeContent.classList.add("animate-fade-in");
  }
  if (window.lucide) lucide.createIcons();
}

// Submit Profile Analysis
async function handleAnalyzeSubmit(event) {
  if (event && event.preventDefault) event.preventDefault();
  const fileInput = document.getElementById("resumeFileInput");
  const jdText = document.getElementById("jdTextArea")?.value.trim() || "";
  const jdUrl = document.getElementById("jdUrlInput")?.value.trim() || "";

  if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
    alert("Please select or drop a resume file (PDF, DOCX, MD, or TXT) before analyzing.");
    return;
  }

  const formData = new FormData();
  formData.append("resume_file", fileInput.files[0]);
  if (jdText) formData.append("job_description", jdText);
  if (jdUrl) formData.append("job_url", jdUrl);

  // Show loading
  document.getElementById("landingSection")?.classList.add("hidden");
  document.getElementById("loadingOverlay")?.classList.remove("hidden");

  // Animate multi-agent progress steps
  const steps = [
    "Executing: Resume Agent • Extracting verified candidate competencies...",
    "Executing: Job Market Agent • Deconstructing target role requirements...",
    "Executing: ATS Scorer Engine • Running explainable 5-dimensional evaluation...",
    "Executing: Resume Optimizer Agent • Formulating STAR-grounded enhancements...",
    "Executing: Interview Coach Agent • Crafting role-specific questions..."
  ];
  let stepIdx = 0;
  const stepInterval = setInterval(() => {
    stepIdx = (stepIdx + 1) % steps.length;
    setText("loadingStep", steps[stepIdx]);
  }, 2500);

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      body: formData
    });

    clearInterval(stepInterval);

    if (!response.ok) {
      let errDetail = `Server returned status ${response.status}`;
      try {
        const errText = await response.text();
        try {
          const errJson = JSON.parse(errText);
          errDetail = errJson.detail || errText;
        } catch (_) {
          if (errText && errText.trim()) errDetail = errText;
        }
      } catch (e) {
        errDetail = response.statusText || errDetail;
      }
      throw new Error(errDetail);
    }

    analysisData = await response.json();
    
    // Safely render all views
    renderAllViews(analysisData);

    // Reveal UI tabs & results
    document.getElementById("loadingOverlay")?.classList.add("hidden");
    document.getElementById("landingSection")?.classList.remove("hidden");
    document.getElementById("topNavTabs")?.classList.remove("hidden");
    document.getElementById("resultsSection")?.classList.remove("hidden");
    switchTab("dashboard");

    // Smooth scroll to results
    document.getElementById("resultsSection")?.scrollIntoView({ behavior: "smooth" });

  } catch (error) {
    clearInterval(stepInterval);
    alert("Analysis Error: " + error.message);
    document.getElementById("loadingOverlay")?.classList.add("hidden");
    document.getElementById("landingSection")?.classList.remove("hidden");
  }
}

// Render All Components (Defensive execution)
function renderAllViews(data) {
  try {
    // 0. Update Summary Meta Banner
    const candName = data.resume_data?.contact?.name || "Candidate Profile";
    const roleTitle = data.jd_data?.title || data.jd_data?.role_domain || "Target Role";
    const atsScore = data.ats_analysis?.overall_ats_score || 0;
    const candDomain = data.resume_data?.candidate_domain || "Engineering";
    const expYears = data.resume_data?.estimated_experience_years || 1;

    setText("summaryCandName", candName);
    setText("summaryTargetRole", roleTitle);
    setText("summarySubText", `${candDomain} • ~${expYears} yrs experience • ATS Score: ${atsScore}/100`);

    renderDashboard(data);
    renderSkillIntelligence(data);
    renderResumeOptimizer(data);
    renderInterviewCoach(data);

  } catch (err) {
    console.error("View rendering warning:", err);
  }

  if (window.lucide) lucide.createIcons();
}

// 1. Dashboard View
function renderDashboard(data) {
  const ats = data.ats_analysis || {};
  const match = data.match_categories || {};
  const skills = data.skill_intelligence || {};
  const score = ats.overall_ats_score || 0;

  // Banner handling
  const alertBanner = document.getElementById("dashAlertBanner");
  const isMismatch = (score < 40) || (match.domain_match && match.domain_match.includes("Mismatch"));

  if (alertBanner) {
    alertBanner.classList.remove("hidden");
    if (isMismatch) {
      alertBanner.innerHTML = `
        <div class="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-500/50 flex items-start space-x-3">
          <i data-lucide="alert-octagon" class="w-5 h-5 text-rose-600 dark:text-rose-400 mt-0.5 shrink-0"></i>
          <div class="text-xs space-y-1">
            <strong class="text-rose-700 dark:text-rose-300 font-bold block">Domain or Seniority Realignment Needed</strong>
            <p class="text-slate-700 dark:text-slate-200 leading-relaxed">
              Target Role Domain: <span class="font-mono font-bold text-rose-600 dark:text-rose-400">${data.jd_data?.role_domain || "Specialized Domain"}</span> (${data.jd_data?.experience_requirements || "Experience specific"}).<br>
              Candidate Background: <span class="font-mono font-bold text-brand-600 dark:text-brand-400">${data.resume_data?.candidate_domain || "Software Engineering"}</span> (~${data.resume_data?.estimated_experience_years || 1} yrs exp).
            </p>
          </div>
        </div>
      `;
    } else {
      alertBanner.innerHTML = `
        <div class="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-300 dark:border-emerald-500/40 flex items-start space-x-3">
          <i data-lucide="check-circle" class="w-5 h-5 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0"></i>
          <div class="text-xs">
            <strong class="text-emerald-800 dark:text-emerald-300 font-bold block">High Candidate Alignment</strong>
            <span class="text-slate-700 dark:text-slate-200">Your profile in <strong class="font-mono text-emerald-700 dark:text-emerald-400">${data.resume_data?.candidate_domain || "Target Discipline"}</strong> matches the core requirements for this position.</span>
          </div>
        </div>
      `;
    }
  }

  // Cards
  setText("dashAtsScore", score);
  const atsBar = document.getElementById("dashAtsBar");
  if (atsBar) atsBar.style.width = `${score}%`;

  setText("dashJdMatch", `${match.overall_match || 0}%`);
  const jdBar = document.getElementById("dashJdBar");
  if (jdBar) jdBar.style.width = `${match.overall_match || 0}%`;
  setText("dashJdRole", `${data.jd_data?.title || "Target Role"} (${data.jd_data?.role_domain || "Domain"})`);

  const matchedLen = ats.matched_keywords?.length || 0;
  const missingLen = ats.missing_keywords?.length || 0;
  const totalReq = (matchedLen + missingLen) || 1;
  setText("dashSkillsCount", matchedLen);
  setText("dashSkillsTotal", `/ ${totalReq}`);
  const skillsBar = document.getElementById("dashSkillsBar");
  if (skillsBar) skillsBar.style.width = `${Math.min(100, Math.round((matchedLen / totalReq) * 100))}%`;
  setText("dashSkillsStatus", `${skills.strong_skills?.length || 0} Strong • ${missingLen} Missing`);

  setText("dashExpMatch", match.experience_match || "Aligned");
  setText("dashEduStatus", `Seniority: ${match.seniority_match || match.experience_match || "Verified"}`);

  // Breakdown Bars
  const breakdownContainer = document.getElementById("atsBreakdownContainer");
  const b = ats.breakdown || {
    keyword_coverage_score: 75,
    technical_skills_score: 70,
    experience_alignment_score: 80,
    education_alignment_score: 90,
    formatting_score: 95
  };

  if (breakdownContainer) {
    breakdownContainer.innerHTML = `
      <div>
        <div class="flex justify-between text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
          <span>Keyword Coverage (Weight: 35%)</span>
          <span class="text-brand-600 dark:text-brand-400 font-bold">${b.keyword_coverage_score}%</span>
        </div>
        <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
          <div class="bg-brand-600 h-2 rounded-full" style="width: ${b.keyword_coverage_score}%"></div>
        </div>
      </div>
      <div>
        <div class="flex justify-between text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
          <span>Technical Skills Alignment (Weight: 25%)</span>
          <span class="text-indigo-600 dark:text-indigo-400 font-bold">${b.technical_skills_score}%</span>
        </div>
        <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
          <div class="bg-indigo-500 h-2 rounded-full" style="width: ${b.technical_skills_score}%"></div>
        </div>
      </div>
      <div>
        <div class="flex justify-between text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
          <span>Experience & Seniority (Weight: 20%)</span>
          <span class="text-purple-600 dark:text-purple-400 font-bold">${b.experience_alignment_score}%</span>
        </div>
        <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
          <div class="bg-purple-500 h-2 rounded-full" style="width: ${b.experience_alignment_score}%"></div>
        </div>
      </div>
      <div>
        <div class="flex justify-between text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
          <span>Education & Credentials (Weight: 10%)</span>
          <span class="text-emerald-600 dark:text-emerald-400 font-bold">${b.education_alignment_score}%</span>
        </div>
        <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
          <div class="bg-emerald-500 h-2 rounded-full" style="width: ${b.education_alignment_score}%"></div>
        </div>
      </div>
      <div>
        <div class="flex justify-between text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
          <span>Formatting & Parser Structure (Weight: 10%)</span>
          <span class="text-amber-600 dark:text-amber-400 font-bold">${b.formatting_score}%</span>
        </div>
        <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
          <div class="bg-amber-500 h-2 rounded-full" style="width: ${b.formatting_score}%"></div>
        </div>
      </div>
    `;
  }

  setText("atsRationaleText", ats.scoring_rationale || "Transparent rule-based dimensional scoring applied.");

  // Domain Match
  const domainContainer = document.getElementById("domainMatchContainer");
  if (domainContainer) {
    domainContainer.innerHTML = `
      <div>
        <div class="flex justify-between text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
          <span>AI / Machine Learning</span>
          <span class="text-brand-600 dark:text-brand-400 font-bold">${match.ai_ml_match || 0}%</span>
        </div>
        <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
          <div class="bg-brand-500 h-2 rounded-full" style="width: ${match.ai_ml_match || 0}%"></div>
        </div>
      </div>
      <div>
        <div class="flex justify-between text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
          <span>Backend & Distributed Systems</span>
          <span class="text-indigo-600 dark:text-indigo-400 font-bold">${match.backend_match || 0}%</span>
        </div>
        <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
          <div class="bg-indigo-500 h-2 rounded-full" style="width: ${match.backend_match || 0}%"></div>
        </div>
      </div>
      <div>
        <div class="flex justify-between text-xs font-mono text-slate-700 dark:text-slate-300 mb-1">
          <span>Cloud & DevOps Architecture</span>
          <span class="text-amber-600 dark:text-amber-400 font-bold">${match.cloud_devops_match || 0}%</span>
        </div>
        <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
          <div class="bg-amber-500 h-2 rounded-full" style="width: ${match.cloud_devops_match || 0}%"></div>
        </div>
      </div>
    `;
  }

  // Formatting risks & Suggestions
  const risksList = document.getElementById("formattingRisksList");
  if (risksList) {
    risksList.innerHTML = (ats.formatting_risks && ats.formatting_risks.length > 0)
      ? ats.formatting_risks.map(r => `<li class="flex items-start space-x-2"><span class="text-amber-500">•</span><span>${escapeHtml(r)}</span></li>`).join("")
      : '<li class="text-emerald-600 flex items-center space-x-2"><i data-lucide="check" class="w-3.5 h-3.5"></i><span>Clean structure. No major ATS parsing hurdles detected.</span></li>';
  }

  const suggList = document.getElementById("improvementSuggestionsList");
  if (suggList) {
    suggList.innerHTML = (ats.improvement_suggestions && ats.improvement_suggestions.length > 0)
      ? ats.improvement_suggestions.map(s => `<li class="flex items-start space-x-2"><span class="text-brand-600">•</span><span>${escapeHtml(s)}</span></li>`).join("")
      : '<li class="text-slate-500">Your profile demonstrates solid keyword coverage.</li>';
  }
}

// 2. Skill Alignment & Roadmaps View
function renderSkillIntelligence(data) {
  const ats = data.ats_analysis || {};
  const intel = data.skill_intelligence || {};

  // Strong Technical Matches
  const strongList = document.getElementById("strongMatchesList");
  if (strongList) {
    const matched = ats.matched_keywords || [];
    if (matched.length > 0) {
      strongList.innerHTML = matched.map(k => `
        <div class="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-500/30 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <i data-lucide="check" class="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0"></i>
            <span class="text-xs font-bold text-slate-800 dark:text-slate-200 font-mono">${escapeHtml(k)}</span>
          </div>
          <span class="text-[10px] font-mono font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/50 px-2 py-0.5 rounded-full">MATCHED</span>
        </div>
      `).join('');
    } else {
      strongList.innerHTML = `<p class="text-xs text-slate-500 font-mono py-2">No direct keyword overlap detected between resume and JD.</p>`;
    }
  }

  // Missing Keywords / Gaps
  const partialList = document.getElementById("partialMatchesList");
  if (partialList) {
    const missing = ats.missing_keywords || [];
    if (missing.length > 0) {
      partialList.innerHTML = missing.map(k => `
        <div class="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-500/30 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <i data-lucide="alert-circle" class="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0"></i>
            <span class="text-xs font-bold text-slate-800 dark:text-slate-200 font-mono">${escapeHtml(k)}</span>
          </div>
          <span class="text-[10px] font-mono font-bold text-amber-700 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/50 px-2 py-0.5 rounded-full">GAP / REQUIRED</span>
        </div>
      `).join('');
    } else {
      partialList.innerHTML = `<p class="text-xs text-emerald-600 font-mono py-2">Zero skill gaps detected! 100% technical keyword coverage.</p>`;
    }
  }

  // Actionable Roadmaps
  const roadmaps = document.getElementById("skillRoadmapsContainer");
  if (roadmaps) {
    if (intel.skill_breakdown && intel.skill_breakdown.length > 0) {
      roadmaps.innerHTML = intel.skill_breakdown.map((item) => {
        const isStrong = item.status === "STRONG";
        const badgeClass = isStrong 
          ? "bg-emerald-100 dark:bg-emerald-950/70 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-500/40"
          : (item.status === "PARTIAL" 
            ? "bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-500/40"
            : "bg-rose-100 dark:bg-rose-950/70 text-rose-800 dark:text-rose-300 border-rose-300 dark:border-rose-500/40");

        return `
          <div class="p-5 rounded-2xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-3">
                <h4 class="text-sm font-bold text-slate-900 dark:text-white font-mono">${escapeHtml(item.skill)}</h4>
                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border ${badgeClass}">${item.status}</span>
              </div>
              <span class="text-xs font-mono text-slate-500">Priority: <strong class="text-brand-600 dark:text-brand-400">${item.importance}</strong></span>
            </div>
            <p class="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">${escapeHtml(item.reason)}</p>
            ${item.recommended_learning_path && item.recommended_learning_path.length > 0 ? `
              <div class="p-3 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">Bridge Learning Path:</span>
                <ul class="space-y-1 text-xs font-mono text-slate-700 dark:text-slate-300 list-disc list-inside">
                  ${item.recommended_learning_path.map(step => `<li>${escapeHtml(step)}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
          </div>
        `;
      }).join('');
    } else {
      roadmaps.innerHTML = `<p class="text-xs text-slate-500 font-mono py-2">Skill alignment analysis completed.</p>`;
    }
  }
}

// 3. Resume Optimizer View (CrewAI Resume Optimizer Agent)
function renderResumeOptimizer(data) {
  const container = document.getElementById("optimizerCardsContainer");
  if (!container) return;

  const opt = data.resume_optimization || {};
  const items = opt.items || [];
  const fullMd = opt.full_tailored_markdown || "";

  if (items.length === 0 && !fullMd) {
    container.innerHTML = `<p class="text-xs text-slate-500 font-mono py-4">No specific bullet point optimizations were required for this resume.</p>`;
    return;
  }

  let html = "";

  // Full Tailored Resume Banner
  if (fullMd) {
    html += `
      <div class="p-5 rounded-2xl bg-brand-50/50 dark:bg-slate-900 border border-brand-200 dark:border-slate-800 shadow-sm space-y-3">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h4 class="text-sm font-bold text-slate-900 dark:text-white flex items-center space-x-2">
              <i data-lucide="file-text" class="w-4 h-4 text-brand-600"></i>
              <span>Full Tailored Resume Generated</span>
            </h4>
            <p class="text-xs text-slate-500 mt-0.5">Assembled by CrewAI Resume Optimizer Agent with STAR action verbs and targeted keywords.</p>
          </div>
          <div class="flex items-center space-x-2">
            <button onclick="copyFullTailoredResume()" class="px-3 py-1.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:border-brand-500 text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center space-x-1.5 transition-all shadow-sm">
              <i data-lucide="copy" class="w-3.5 h-3.5"></i>
              <span>Copy Full Markdown</span>
            </button>
            <button onclick="downloadFullTailoredResume()" class="px-3 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold flex items-center space-x-1.5 transition-all shadow-sm">
              <i data-lucide="download" class="w-3.5 h-3.5"></i>
              <span>Download .md</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  // Render individual STAR bullet optimizations
  if (items.length > 0) {
    html += items.map((item, idx) => `
      <div class="p-6 rounded-2xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4 shadow-sm">
        <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
          <div class="flex items-center space-x-2.5">
            <span class="w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/60 text-brand-700 dark:text-brand-300 text-xs font-bold font-mono flex items-center justify-center">0${idx + 1}</span>
            <span class="text-xs font-bold text-brand-600 dark:text-brand-400 uppercase tracking-wider font-mono">${escapeHtml(item.section)}</span>
          </div>
          <button onclick="copyToClipboard('${escapeHtml(item.suggested).replace(/'/g, "\\'")}', 'Suggested bullet copied!')" class="px-3 py-1 rounded-lg bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:border-brand-500 text-slate-700 dark:text-slate-300 text-xs font-bold flex items-center space-x-1.5 transition-colors">
            <i data-lucide="copy" class="w-3.5 h-3.5"></i>
            <span>Copy</span>
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Original -->
          <div class="p-4 rounded-xl bg-rose-50/50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/40 space-y-1.5">
            <span class="text-[10px] font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 font-mono">Original Resume Bullet</span>
            <p class="text-xs text-slate-700 dark:text-slate-300 font-mono leading-relaxed">${escapeHtml(item.original)}</p>
          </div>

          <!-- Suggested -->
          <div class="p-4 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/40 space-y-1.5">
            <span class="text-[10px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 font-mono">STAR-Optimized Suggestion</span>
            <p class="text-xs text-slate-900 dark:text-slate-100 font-mono font-medium leading-relaxed">${escapeHtml(item.suggested)}</p>
          </div>
        </div>

        <div class="p-3.5 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
          <div class="text-xs text-slate-600 dark:text-slate-400">
            <strong class="text-brand-600 dark:text-brand-400">Why this improves ATS & Recruiter Impact:</strong>
            <span class="ml-1">${escapeHtml(item.why_this_is_better)}</span>
          </div>
          ${item.keywords_added && item.keywords_added.length > 0 ? `
            <div class="flex flex-wrap items-center gap-1.5 pt-1">
              <span class="text-[10px] text-slate-400 uppercase font-mono font-bold">Keywords Added:</span>
              ${item.keywords_added.map(k => `
                <span class="px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-900/40 border border-emerald-200 dark:border-emerald-700/50 text-[10px] font-mono text-emerald-700 dark:text-emerald-300 font-semibold">${escapeHtml(k)}</span>
              `).join('')}
            </div>
          ` : ''}
        </div>
      </div>
    `).join("");
  }

  container.innerHTML = html;
  if (window.lucide) lucide.createIcons();
}

function copyFullTailoredResume() {
  const fullMd = analysisData?.resume_optimization?.full_tailored_markdown;
  if (!fullMd) {
    alert("No full tailored markdown available.");
    return;
  }
  copyToClipboard(fullMd, "Full Tailored Resume copied to clipboard!");
}

function downloadFullTailoredResume() {
  const fullMd = analysisData?.resume_optimization?.full_tailored_markdown;
  if (!fullMd) {
    alert("No full tailored markdown available.");
    return;
  }
  const role = analysisData?.jd_data?.title || "Tailored_Resume";
  const filename = `${role.replace(/[\s/\\?%*:|"<>]/g, "_")}.md`;
  const blob = new Blob([fullMd], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 4. Interview Coach View (CrewAI Interview Coach Agent)
function renderInterviewCoach(data) {
  const patternContainer = document.getElementById("interviewPatternContainer");
  const questionsContainer = document.getElementById("interviewQuestionsContainer");
  const pattern = data.company_interview_pattern || {};
  const questions = data.interview_questions || [];

  // 1. Render Company & Role Interview Patterns
  if (patternContainer) {
    const company = pattern.company_name || data.jd_data?.company || "Target Enterprise";
    const domain = pattern.role_domain || data.jd_data?.role_domain || "Industry Domain";
    const role = pattern.target_role || data.jd_data?.title || "Target Role";
    const stages = pattern.interview_stages || [];
    const criteria = pattern.evaluation_criteria || [];
    const trends = pattern.reported_trends || [];

    patternContainer.innerHTML = `
      <div class="bg-gradient-to-br from-brand-50 to-indigo-50/50 dark:from-slate-900 dark:to-slate-800/80 border border-brand-200 dark:border-slate-800 rounded-2xl p-6 sm:p-7 shadow-sm space-y-5">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-brand-200/60 dark:border-slate-800">
          <div>
            <div class="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-brand-100 dark:bg-brand-900/60 text-brand-700 dark:text-brand-300 text-[10px] font-mono font-bold uppercase mb-1">
              <i data-lucide="compass" class="w-3 h-3"></i>
              <span>Web-Reported Interview Intelligence</span>
            </div>
            <h4 class="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white">
              ${escapeHtml(company)} — Interview Rounds & Hiring Bar Patterns
            </h4>
            <p class="text-xs text-slate-500 mt-0.5">Real-world interview trends and stage-by-stage evaluation focus for <strong class="text-slate-800 dark:text-slate-200">${escapeHtml(role)}</strong> (${escapeHtml(domain)}).</p>
          </div>
          <span class="px-3 py-1 rounded-xl bg-white dark:bg-slate-800 text-xs font-mono font-bold text-brand-600 dark:text-brand-400 border border-slate-200 dark:border-slate-700 self-start sm:self-auto shadow-xs">
            ${stages.length} Interview Rounds
          </span>
        </div>

        <!-- Stages Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          ${stages.map((st, i) => `
            <div class="p-4 rounded-xl bg-white dark:bg-slate-950 border border-brand-100 dark:border-slate-800 space-y-1.5 shadow-xs">
              <span class="text-[10px] font-mono font-bold text-brand-600 dark:text-brand-400 uppercase tracking-wider block">Stage 0${i+1}</span>
              <h5 class="text-xs font-bold text-slate-900 dark:text-white">${escapeHtml(st.round)}</h5>
              <p class="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed font-sans">${escapeHtml(st.desc)}</p>
            </div>
          `).join('')}
        </div>

        <!-- Evaluation Criteria & Web Trends -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          <div class="p-4 rounded-xl bg-white/80 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 space-y-2">
            <span class="text-[11px] font-bold text-slate-900 dark:text-white uppercase font-mono flex items-center space-x-1.5">
              <i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-500"></i>
              <span>Core Evaluation Criteria</span>
            </span>
            <ul class="space-y-1.5 text-xs text-slate-700 dark:text-slate-300">
              ${criteria.map(c => `<li class="flex items-start space-x-2"><span class="text-emerald-500">•</span><span>${escapeHtml(c)}</span></li>`).join('')}
            </ul>
          </div>

          <div class="p-4 rounded-xl bg-white/80 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 space-y-2">
            <span class="text-[11px] font-bold text-slate-900 dark:text-white uppercase font-mono flex items-center space-x-1.5">
              <i data-lucide="trending-up" class="w-3.5 h-3.5 text-indigo-500"></i>
              <span>Reported Question Trends & Discussion Topics</span>
            </span>
            <ul class="space-y-1.5 text-xs text-slate-700 dark:text-slate-300 font-mono">
              ${trends.map(t => `<li class="flex items-start space-x-2"><span class="text-indigo-500">•</span><span>${escapeHtml(t)}</span></li>`).join('')}
            </ul>
          </div>
        </div>
      </div>
    `;
  }

  // 2. Render Role-Specific Interview Questions
  if (!questionsContainer) return;

  if (questions.length === 0) {
    questionsContainer.innerHTML = `<p class="text-xs text-slate-500 font-mono py-4">No specific interview questions generated for this profile.</p>`;
    return;
  }

  questionsContainer.innerHTML = questions.map((q) => {
    const isReported = q.category.toLowerCase().includes("reported") || q.category.toLowerCase().includes("company");
    const badgeColor = isReported
      ? "bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-500/30"
      : "bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-500/30";

    return `
      <div class="p-6 rounded-2xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4 shadow-sm">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold border ${badgeColor}">
              ${escapeHtml(q.category)}
            </span>
            ${q.context_source ? `<span class="hidden sm:inline text-[10px] text-slate-400 font-mono">Context: ${escapeHtml(q.context_source)}</span>` : ''}
          </div>
          <button onclick="openMockModal('${encodeURIComponent(JSON.stringify(q))}')" class="px-3.5 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold flex items-center space-x-1.5 transition-all shadow-sm">
            <i data-lucide="message-square" class="w-3.5 h-3.5"></i>
            <span>Practice in Mock Simulator</span>
          </button>
        </div>

        <h4 class="text-sm sm:text-base font-bold text-slate-900 dark:text-white leading-snug">${escapeHtml(q.question)}</h4>

        <div class="p-4 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
          <span class="text-[11px] font-mono text-slate-400 block mb-2 uppercase font-bold">Strategic Talking Points:</span>
          <ul class="space-y-1 text-xs text-slate-700 dark:text-slate-300 font-mono">
            ${q.talking_points ? q.talking_points.map(tp => `<li class="flex items-start space-x-2"><span class="text-brand-600">•</span><span>${escapeHtml(tp)}</span></li>`).join("") : ''}
          </ul>
        </div>
      </div>
    `;
  }).join("");

  if (window.lucide) lucide.createIcons();
}

// 5. Theme Toggle
function toggleDarkMode() {
  const html = document.documentElement;
  const isDark = html.classList.toggle("dark");
  const icon = document.getElementById("themeIcon");
  if (isDark) {
    localStorage.setItem("career_theme", "dark");
    icon?.setAttribute("data-lucide", "moon");
  } else {
    localStorage.setItem("career_theme", "light");
    icon?.setAttribute("data-lucide", "sun");
  }
  if (window.lucide) lucide.createIcons();
}
