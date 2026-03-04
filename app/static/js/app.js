/* ═══════════════════════════════════════════════════════════════════
   Growth Strategist — Dashboard Application
   ═══════════════════════════════════════════════════════════════════ */

(() => {
    "use strict";

    // ── State ────────────────────────────────────────────────────────
    const state = {
        seeds: [],
        analysisResult: null,
        selectedNiche: null,
        isAnalyzing: false,
        timerInterval: null,
        timerStart: 0,
        scoreChart: null,
    };

    const PIPELINE_STEPS = [
        "Keyword Expansion",
        "Trend Discovery",
        "Niche Clustering",
        "Competition Analysis",
        "Virality Prediction",
        "CTR Prediction",
        "Faceless Viability",
        "Niche Ranking",
        "Video Strategy",
        "Blueprint Assembly",
        "Report Generation",
    ];

    // ── DOM References ───────────────────────────────────────────────
    const $ = (s, ctx = document) => ctx.querySelector(s);
    const $$ = (s, ctx = document) => [...ctx.querySelectorAll(s)];

    const dom = {
        keywordInput: $("#keywordInput"),
        analyzeBtn: $("#analyzeBtn"),
        analyzeBtnText: $("#analyzeBtnText"),
        analyzeBtnIcon: $("#analyzeBtnIcon"),
        seedTags: $("#seedTags"),
        pipelineProgress: $("#pipelineProgress"),
        progressLabel: $("#progressLabel"),
        progressTimer: $("#progressTimer"),
        progressBar: $("#progressBar"),
        progressSteps: $("#progressSteps"),
        errorBanner: $("#errorBanner"),
        errorText: $("#errorText"),
        healthDot: $("#healthDot"),
        healthText: $("#healthText"),
        nicheTableBody: $("#nicheTableBody"),
        statCards: $("#statCards"),
        resultsMeta: $("#resultsMeta"),
        resultsSubtitle: $("#resultsSubtitle"),
        scoreChart: $("#scoreChart"),
        drawerOverlay: $("#drawerOverlay"),
        nicheDrawer: $("#nicheDrawer"),
        drawerTitle: $("#drawerTitle"),
        drawerBody: $("#drawerBody"),
        drawerClose: $("#drawerClose"),
        toastContainer: $("#toastContainer"),
    };

    // ── Initialization ───────────────────────────────────────────────
    function init() {
        bindEvents();
        checkHealth();
        setInterval(checkHealth, 30_000);
    }

    // ── Event Binding ────────────────────────────────────────────────
    function bindEvents() {
        // Navigation
        $$(".nav-link").forEach((btn) =>
            btn.addEventListener("click", () => navigateTo(btn.dataset.page))
        );

        // Keyword input
        dom.keywordInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") { e.preventDefault(); addSeed(); }
        });

        dom.analyzeBtn.addEventListener("click", startAnalysis);

        // Example chips
        $$(".example-chip").forEach((chip) =>
            chip.addEventListener("click", () => {
                addSeedValue(chip.dataset.kw);
                dom.keywordInput.focus();
            })
        );

        // Drawer
        dom.drawerClose.addEventListener("click", closeDrawer);
        dom.drawerOverlay.addEventListener("click", closeDrawer);
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") closeDrawer();
        });
    }

    // ── Navigation ───────────────────────────────────────────────────
    function navigateTo(page) {
        $$(".page-section").forEach((s) => s.classList.remove("active"));
        $$(".nav-link").forEach((b) => b.classList.remove("active"));

        $(`#page-${page}`).classList.add("active");
        $(`.nav-link[data-page="${page}"]`).classList.add("active");
    }

    // ── Seed Management ──────────────────────────────────────────────
    function addSeed() {
        const val = dom.keywordInput.value.trim().toLowerCase();
        if (!val) return;
        addSeedValue(val);
        dom.keywordInput.value = "";
        dom.keywordInput.focus();
    }

    function addSeedValue(value) {
        if (state.seeds.includes(value) || state.seeds.length >= 10) return;
        state.seeds.push(value);
        renderSeeds();
        updateAnalyzeButton();
    }

    function removeSeed(value) {
        state.seeds = state.seeds.filter((s) => s !== value);
        renderSeeds();
        updateAnalyzeButton();
    }

    function renderSeeds() {
        dom.seedTags.innerHTML = state.seeds
            .map(
                (s) => `
        <span class="seed-tag">
          ${escapeHtml(s)}
          <span class="remove-tag" data-seed="${escapeHtml(s)}">✕</span>
        </span>`
            )
            .join("");

        $$(".remove-tag", dom.seedTags).forEach((el) =>
            el.addEventListener("click", () => removeSeed(el.dataset.seed))
        );
    }

    function updateAnalyzeButton() {
        dom.analyzeBtn.disabled = state.seeds.length === 0 || state.isAnalyzing;
    }

    // ── Analysis Pipeline ────────────────────────────────────────────
    async function startAnalysis() {
        if (state.isAnalyzing || state.seeds.length === 0) return;

        state.isAnalyzing = true;
        updateAnalyzeButton();
        dom.analyzeBtnText.textContent = "Analyzing…";
        dom.analyzeBtnIcon.textContent = "⏳";
        dom.errorBanner.classList.add("hidden");

        showProgress();
        startTimer();

        const topN = parseInt($("#topN").value, 10);
        const videosPerNiche = parseInt($("#videosPerNiche").value, 10);

        try {
            const res = await fetch("/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    seed_keywords: state.seeds,
                    top_n: topN,
                    videos_per_niche: videosPerNiche,
                }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Server error (${res.status})`);
            }

            const data = await res.json();
            state.analysisResult = data;

            // Complete progress
            completeProgress();

            setTimeout(() => {
                renderResults(data);
                navigateTo("results");
                toast("Analysis complete!", "success");
            }, 600);

        } catch (err) {
            showError(err.message);
            toast(err.message, "error");
        } finally {
            state.isAnalyzing = false;
            updateAnalyzeButton();
            dom.analyzeBtnText.textContent = "Analyze";
            dom.analyzeBtnIcon.textContent = "⚡";
            stopTimer();
        }
    }

    // ── Progress Animation ───────────────────────────────────────────
    function showProgress() {
        dom.pipelineProgress.classList.add("active");

        dom.progressSteps.innerHTML = PIPELINE_STEPS.map(
            (step, i) => `
      <div class="step-item" data-step="${i}">
        <div class="step-icon">${i + 1}</div>
        <span>${step}</span>
      </div>`
        ).join("");

        animateSteps();
    }

    function animateSteps() {
        let current = 0;
        const steps = $$(".step-item", dom.progressSteps);
        const total = steps.length;

        function next() {
            if (current >= total || !state.isAnalyzing) return;

            steps[current].classList.add("active");
            steps[current].querySelector(".step-icon").innerHTML = '<div class="step-spinner" style="width:12px;height:12px;border-width:1.5px"></div>';

            dom.progressBar.style.width = `${((current + 1) / total) * 90}%`;
            dom.progressLabel.textContent = PIPELINE_STEPS[current] + "…";

            if (current > 0) {
                steps[current - 1].classList.remove("active");
                steps[current - 1].classList.add("done");
                steps[current - 1].querySelector(".step-icon").innerHTML = "✓";
            }

            current++;
            const delay = 1200 + Math.random() * 2000;
            setTimeout(next, delay);
        }

        next();
    }

    function completeProgress() {
        const steps = $$(".step-item", dom.progressSteps);
        steps.forEach((s) => {
            s.classList.remove("active");
            s.classList.add("done");
            s.querySelector(".step-icon").innerHTML = "✓";
        });
        dom.progressBar.style.width = "100%";
        dom.progressLabel.textContent = "Pipeline complete!";
    }

    function startTimer() {
        state.timerStart = Date.now();
        state.timerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - state.timerStart) / 1000);
            const m = Math.floor(elapsed / 60);
            const s = elapsed % 60;
            dom.progressTimer.textContent = `${m}:${String(s).padStart(2, "0")}`;
        }, 500);
    }

    function stopTimer() {
        if (state.timerInterval) {
            clearInterval(state.timerInterval);
            state.timerInterval = null;
        }
    }

    // ── Results Rendering ────────────────────────────────────────────
    function renderResults(data) {
        const niches = data.top_niches || [];
        const concepts = data.channel_concepts || [];
        const blueprints = data.video_blueprints || {};
        const meta = data.metadata || {};

        // Subtitle
        dom.resultsSubtitle.textContent = `Seeds: ${data.seed_keywords.join(", ")}`;

        // Meta stats
        const totalBlueprints = Object.values(blueprints).reduce(
            (sum, bps) => sum + bps.length, 0
        );

        dom.resultsMeta.innerHTML = `
      <div class="meta-stat"><div class="value">${niches.length}</div><div class="label">Niches</div></div>
      <div class="meta-stat"><div class="value">${concepts.length}</div><div class="label">Channels</div></div>
      <div class="meta-stat"><div class="value">${totalBlueprints}</div><div class="label">Blueprints</div></div>
      <div class="meta-stat"><div class="value">${meta.pipeline_duration_seconds || "—"}s</div><div class="label">Duration</div></div>
    `;

        // Stat cards
        renderStatCards(niches);

        // Table
        renderNicheTable(niches, concepts, blueprints);

        // Chart
        renderScoreChart(niches);
    }

    function renderStatCards(niches) {
        if (!niches.length) { dom.statCards.innerHTML = ""; return; }

        const best = niches[0];
        const avgScore = (niches.reduce((s, n) => s + n.overall_score, 0) / niches.length).toFixed(1);
        const maxDemand = Math.max(...niches.map((n) => n.demand_score)).toFixed(1);
        const minComp = Math.min(...niches.map((n) => n.competition_score)).toFixed(1);
        const maxTrend = Math.max(...niches.map((n) => n.trend_momentum)).toFixed(1);
        const maxFaceless = Math.max(...niches.map((n) => n.faceless_viability)).toFixed(1);

        dom.statCards.innerHTML = `
      <div class="stat-card stat-accent-blue">
        <div class="stat-label">Top Niche</div>
        <div class="stat-value">${best.overall_score}</div>
        <div class="stat-sub">${escapeHtml(truncate(best.niche, 28))}</div>
      </div>
      <div class="stat-card stat-accent-emerald">
        <div class="stat-label">Avg Score</div>
        <div class="stat-value">${avgScore}</div>
        <div class="stat-sub">${niches.length} niches analyzed</div>
      </div>
      <div class="stat-card stat-accent-amber">
        <div class="stat-label">Peak Demand</div>
        <div class="stat-value">${maxDemand}</div>
        <div class="stat-sub">Highest demand score</div>
      </div>
      <div class="stat-card stat-accent-violet">
        <div class="stat-label">Low Competition</div>
        <div class="stat-value">${minComp}</div>
        <div class="stat-sub">Easiest entry point</div>
      </div>
      <div class="stat-card stat-accent-cyan">
        <div class="stat-label">Peak Trend</div>
        <div class="stat-value">${maxTrend}</div>
        <div class="stat-sub">Strongest momentum</div>
      </div>
      <div class="stat-card stat-accent-rose">
        <div class="stat-label">Faceless Ready</div>
        <div class="stat-value">${maxFaceless}</div>
        <div class="stat-sub">Best faceless fit</div>
      </div>
    `;
    }

    function renderNicheTable(niches, concepts, blueprints) {
        if (!niches.length) {
            dom.nicheTableBody.innerHTML = `
        <tr><td colspan="9" class="text-center" style="padding:3rem;color:var(--text-muted)">
          No niches found. Try different seed keywords.
        </td></tr>`;
            return;
        }

        dom.nicheTableBody.innerHTML = niches.map((n) => {
            const rankClass = n.rank <= 3 ? `rank-${n.rank}` : "rank-n";
            return `
        <tr data-niche="${escapeAttr(n.niche)}">
          <td><span class="rank-badge ${rankClass}">${n.rank}</span></td>
          <td><span class="niche-name">${escapeHtml(n.niche)}</span></td>
          <td><span class="score-pill ${scoreClass(n.overall_score)}">${n.overall_score}</span></td>
          <td>${miniBar(n.demand_score, "blue")}</td>
          <td>${miniBar(n.competition_score, "rose")}</td>
          <td>${miniBar(n.trend_momentum, "emerald")}</td>
          <td>${miniBar(n.virality_score, "violet")}</td>
          <td>${miniBar(n.ctr_potential, "amber")}</td>
          <td>${miniBar(n.faceless_viability, "cyan")}</td>
        </tr>`;
        }).join("");

        // Row clicks
        $$("tr[data-niche]", dom.nicheTableBody).forEach((row) =>
            row.addEventListener("click", () => {
                const name = row.dataset.niche;
                const niche = niches.find((n) => n.niche === name);
                const concept = concepts.find((c) => c.niche === name);
                const bps = blueprints[name] || [];
                openDrawer(niche, concept, bps);
            })
        );
    }

    function miniBar(value, color) {
        return `
      <div class="score-bar-cell">
        <div style="display:flex;align-items:center;gap:0.5rem;">
          <div class="score-bar bar-${color}" style="flex:1">
            <div class="score-bar-inner" style="width:${value}%"></div>
          </div>
          <span style="font-size:0.78rem;color:var(--text-muted);min-width:28px;text-align:right;font-variant-numeric:tabular-nums">${value}</span>
        </div>
      </div>`;
    }

    function scoreClass(score) {
        if (score >= 70) return "score-high";
        if (score >= 45) return "score-medium";
        return "score-low";
    }

    // ── Score Chart ──────────────────────────────────────────────────
    function renderScoreChart(niches) {
        if (state.scoreChart) { state.scoreChart.destroy(); state.scoreChart = null; }
        if (!niches.length) return;

        const labels = niches.map((n) => truncate(n.niche, 18));
        const colors = {
            demand: "rgba(59,130,246,0.8)",
            competition: "rgba(251,113,133,0.8)",
            trend: "rgba(52,211,153,0.8)",
            virality: "rgba(167,139,250,0.8)",
            ctr: "rgba(251,191,36,0.8)",
            faceless: "rgba(34,211,238,0.8)",
        };

        state.scoreChart = new Chart(dom.scoreChart, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    { label: "Demand", data: niches.map((n) => n.demand_score), backgroundColor: colors.demand },
                    { label: "Competition", data: niches.map((n) => n.competition_score), backgroundColor: colors.competition },
                    { label: "Trend", data: niches.map((n) => n.trend_momentum), backgroundColor: colors.trend },
                    { label: "Virality", data: niches.map((n) => n.virality_score), backgroundColor: colors.virality },
                    { label: "CTR", data: niches.map((n) => n.ctr_potential), backgroundColor: colors.ctr },
                    { label: "Faceless", data: niches.map((n) => n.faceless_viability), backgroundColor: colors.faceless },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: {
                        position: "top",
                        labels: { color: "#94a3b8", font: { size: 11, family: "Inter" }, boxWidth: 12, padding: 16 },
                    },
                    tooltip: {
                        backgroundColor: "#1a2235",
                        titleColor: "#f1f5f9",
                        bodyColor: "#94a3b8",
                        borderColor: "#1e2d45",
                        borderWidth: 1,
                        cornerRadius: 8,
                        padding: 12,
                    },
                },
                scales: {
                    x: {
                        ticks: { color: "#64748b", font: { size: 11, family: "Inter" }, maxRotation: 45 },
                        grid: { color: "rgba(255,255,255,0.03)" },
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: { color: "#64748b", font: { size: 11, family: "Inter" } },
                        grid: { color: "rgba(255,255,255,0.04)" },
                    },
                },
            },
        });
    }

    // ── Niche Detail Drawer ──────────────────────────────────────────
    function openDrawer(niche, concept, blueprints) {
        if (!niche) return;
        state.selectedNiche = niche;

        dom.drawerTitle.textContent = niche.niche;
        dom.drawerBody.innerHTML = buildDrawerContent(niche, concept, blueprints);
        dom.nicheDrawer.classList.add("open");
        dom.drawerOverlay.classList.add("open");
        document.body.style.overflow = "hidden";

        // Bind blueprint toggles
        $$(".blueprint-card-header", dom.drawerBody).forEach((h) =>
            h.addEventListener("click", () => h.parentElement.classList.toggle("expanded"))
        );
    }

    function closeDrawer() {
        dom.nicheDrawer.classList.remove("open");
        dom.drawerOverlay.classList.remove("open");
        document.body.style.overflow = "";
    }

    function buildDrawerContent(niche, concept, blueprints) {
        let html = "";

        // ── Score Grid ──
        html += `<div class="drawer-scores-grid">
      ${drawerScoreCard(niche.overall_score, "Overall", "var(--accent-blue)")}
      ${drawerScoreCard(niche.demand_score, "Demand", "var(--accent-blue)")}
      ${drawerScoreCard(niche.competition_score, "Competition", "var(--accent-rose)")}
      ${drawerScoreCard(niche.trend_momentum, "Trend", "var(--accent-emerald)")}
      ${drawerScoreCard(niche.virality_score, "Virality", "var(--accent-violet)")}
      ${drawerScoreCard(niche.faceless_viability, "Faceless", "var(--accent-cyan)")}
    </div>`;

        // ── Keywords ──
        if (niche.keywords && niche.keywords.length) {
            html += `<div class="drawer-section">
        <h4>🔑 Keywords</h4>
        <div class="keywords-list">
          ${niche.keywords.slice(0, 20).map((k) => `<span class="keyword-chip">${escapeHtml(k)}</span>`).join("")}
        </div>
      </div>`;
        }

        // ── Channel Concept ──
        if (concept) {
            const names = (concept.channel_name_ideas || []).slice(0, 5);
            html += `<div class="drawer-section">
        <h4>📺 Channel Concept</h4>
        <div class="channel-concept-card">
          ${conceptRow("Channel Names", names.map(escapeHtml).join(", "))}
          ${conceptRow("Positioning", escapeHtml(concept.positioning || "—"))}
          ${conceptRow("Cadence", escapeHtml(concept.posting_cadence || "—"))}
          ${conceptRow("Est. RPM", "$" + (concept.estimated_rpm || 0).toFixed(2))}
          ${conceptRow("Monetization", "~" + (concept.time_to_monetization_months || "?") + " months")}
          ${concept.audience ? conceptRow("Audience", escapeHtml(concept.audience.age_range || "—") + " — " + (concept.audience.interests || []).slice(0, 4).map(escapeHtml).join(", ")) : ""}
        </div>
      </div>`;
        }

        // ── Video Blueprints ──
        if (blueprints.length) {
            html += `<div class="drawer-section">
        <h4>🎬 Video Blueprints (${blueprints.length})</h4>
        ${blueprints.map((bp, i) => buildBlueprintCard(bp, i)).join("")}
      </div>`;
        }

        return html;
    }

    function drawerScoreCard(value, label, color) {
        return `<div class="drawer-score-card">
      <div class="dscore-value" style="color:${color}">${value || 0}</div>
      <div class="dscore-label">${label}</div>
    </div>`;
    }

    function conceptRow(label, value) {
        return `<div class="concept-row"><span class="concept-label">${label}</span><span class="concept-value">${value}</span></div>`;
    }

    function buildBlueprintCard(bp, index) {
        const idea = bp.video_idea || {};
        const diffClass = idea.difficulty === "easy" ? "badge-easy" : idea.difficulty === "hard" ? "badge-hard" : "badge-medium";

        let bodyHtml = "";

        // Titles
        const altTitles = bp.alternative_titles || [];
        if (bp.curiosity_gap_headline || bp.keyword_optimized_title || altTitles.length) {
            bodyHtml += `<div class="bp-section" style="grid-column:1/-1">
        <h5>Title Variations</h5>
        <ul class="bp-titles-list">
          ${bp.curiosity_gap_headline ? `<li><strong>Curiosity:</strong> ${escapeHtml(bp.curiosity_gap_headline)}</li>` : ""}
          ${bp.keyword_optimized_title ? `<li><strong>SEO:</strong> ${escapeHtml(bp.keyword_optimized_title)}</li>` : ""}
          ${altTitles.map((t) => `<li>${escapeHtml(t)}</li>`).join("")}
        </ul>
      </div>`;
        }

        // Thumbnail
        if (bp.thumbnail) {
            const t = bp.thumbnail;
            const palette = (t.color_palette || []).map((c) => `<div class="thumb-color" style="background:${c}"></div>`).join("");
            bodyHtml += `<div class="bp-section">
        <h5>Thumbnail</h5>
        <p><strong>Emotion:</strong> ${escapeHtml(t.emotion_trigger || "—")}</p>
        <p><strong>Focus:</strong> ${escapeHtml(truncate(t.visual_focal_point || "", 80))}</p>
        <p><strong>Text:</strong> ${escapeHtml(t.text_overlay || "—")}</p>
        ${palette ? `<div class="thumbnail-preview mt-1">${palette}</div>` : ""}
      </div>`;
        }

        // Script
        if (bp.script_structure) {
            const script = bp.script_structure;
            bodyHtml += `<div class="bp-section">
        <h5>Script Structure</h5>
        <p><strong>Hook:</strong> ${escapeHtml(truncate(script.hook || "", 120))}</p>
        <p class="mt-1"><strong>Mid-video:</strong> ${escapeHtml(truncate(script.mid_video_curiosity_loop || "", 120))}</p>
      </div>`;
        }

        // SEO Description
        if (bp.seo_description) {
            const seo = bp.seo_description;
            bodyHtml += `<div class="bp-section">
        <h5>SEO Description</h5>
        <p>${escapeHtml(truncate(seo.intro_paragraph || "", 150))}</p>
        ${seo.keyword_block && seo.keyword_block.length ? `<p class="mt-1" style="color:var(--accent-blue);font-size:0.75rem">${seo.keyword_block.slice(0, 8).map(escapeHtml).join(" · ")}</p>` : ""}
      </div>`;
        }

        // Monetization
        if (bp.monetization) {
            const mon = bp.monetization;
            bodyHtml += `<div class="bp-section">
        <h5>Monetization</h5>
        <ul>
          ${(mon.affiliate_products || []).slice(0, 4).map((p) => `<li>${escapeHtml(p)}</li>`).join("")}
        </ul>
      </div>`;
        }

        // Production
        if (bp.low_cost_production) {
            const lc = bp.low_cost_production;
            bodyHtml += `<div class="bp-section">
        <h5>Production</h5>
        <p><strong>Cost:</strong> ${escapeHtml(lc.estimated_cost_per_video || "—")}</p>
        <ul>
          ${(lc.ai_voiceover_tools || []).slice(0, 3).map((t) => `<li>${escapeHtml(t)}</li>`).join("")}
        </ul>
      </div>`;
        }

        return `
    <div class="blueprint-card">
      <div class="blueprint-card-header">
        <span class="blueprint-title">${index + 1}. ${escapeHtml(idea.title || "Untitled")}</span>
        <div class="blueprint-meta">
          <span class="blueprint-badge ${diffClass}">${idea.difficulty || "medium"}</span>
          <span class="blueprint-expand">▼</span>
        </div>
      </div>
      <div class="blueprint-body">
        <div class="blueprint-content">
          <div style="display:flex;gap:1rem;margin-bottom:0.75rem;font-size:0.82rem;color:var(--text-muted)">
            <span>📌 ${escapeHtml(idea.topic || "—")}</span>
            <span>🎯 ${escapeHtml(idea.angle || "—")}</span>
            ${idea.estimated_views ? `<span>👀 ${escapeHtml(idea.estimated_views)}</span>` : ""}
          </div>
          <div class="bp-grid">${bodyHtml}</div>
        </div>
      </div>
    </div>`;
    }

    // ── Health Check ─────────────────────────────────────────────────
    async function checkHealth() {
        try {
            const res = await fetch("/health");
            if (res.ok) {
                dom.healthDot.classList.remove("error");
                dom.healthText.textContent = "Online";
            } else {
                throw new Error();
            }
        } catch {
            dom.healthDot.classList.add("error");
            dom.healthText.textContent = "Offline";
        }
    }

    // ── Error Display ────────────────────────────────────────────────
    function showError(message) {
        dom.errorText.textContent = message;
        dom.errorBanner.classList.remove("hidden");
        dom.pipelineProgress.classList.remove("active");
    }

    // ── Toast ────────────────────────────────────────────────────────
    function toast(message, type = "success") {
        const el = document.createElement("div");
        el.className = `toast toast-${type}`;
        el.innerHTML = `<span>${type === "success" ? "✓" : "⚠"}</span> ${escapeHtml(message)}`;
        dom.toastContainer.appendChild(el);
        setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, 4000);
    }

    // ── Utilities ────────────────────────────────────────────────────
    function escapeHtml(str) {
        if (!str) return "";
        const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
        return String(str).replace(/[&<>"']/g, (c) => map[c]);
    }

    function escapeAttr(str) {
        return escapeHtml(str).replace(/"/g, "&quot;");
    }

    function truncate(str, len) {
        if (!str) return "";
        return str.length > len ? str.slice(0, len) + "…" : str;
    }

    // ── Boot ─────────────────────────────────────────────────────────
    document.addEventListener("DOMContentLoaded", init);
})();
