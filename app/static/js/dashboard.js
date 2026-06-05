/**
 * AI Trend Dashboard — interactions, search modes, AJAX, counters.
 */

function updateClock() {
    const el = document.getElementById('currentTime');
    if (el) {
        const now = new Date();
        el.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
}
setInterval(updateClock, 1000);
updateClock();

const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar = document.getElementById('sidebar');
const mainWrapper = document.getElementById('mainWrapper');
if (sidebarToggle && sidebar && mainWrapper) {
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        if (window.innerWidth > 768) {
            const isCollapsed = sidebar.style.transform === 'translateX(-100%)';
            sidebar.style.transform = isCollapsed ? '' : 'translateX(-100%)';
            mainWrapper.style.marginLeft = isCollapsed ? 'var(--sidebar-width)' : '0';
        }
    });
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('appToast');
    const body = document.getElementById('toastBody');
    if (!toast || !body || typeof bootstrap === 'undefined') return;
    body.textContent = message;
    toast.style.borderColor = type === 'error' ? 'var(--red)' : type === 'success' ? 'var(--green)' : 'var(--border)';
    new bootstrap.Toast(toast, { delay: 3200 }).show();
}

const globalSearch = document.getElementById('globalSearch');
const searchResults = document.getElementById('searchResults');
let searchTimeout = null;
if (globalSearch && searchResults) {
    globalSearch.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        const q = globalSearch.value.trim();
        if (q.length < 2) {
            searchResults.classList.remove('show');
            return;
        }
        searchTimeout = setTimeout(() => fetchSearch(q), 280);
    });
    document.addEventListener('click', (e) => {
        if (!globalSearch.contains(e.target) && !searchResults.contains(e.target)) searchResults.classList.remove('show');
    });
}

async function fetchSearch(q) {
    try {
        const resp = await fetch(`/jobs/search?q=${encodeURIComponent(q)}&page=1`);
        const data = await resp.json();
        renderSearchResults(data.jobs || []);
    } catch (e) {
        console.error('Search error:', e);
    }
}

function renderSearchResults(jobs) {
    if (!searchResults) return;
    if (jobs.length === 0) {
        searchResults.innerHTML = '<div class="search-result-item"><span class="search-result-meta">No results found</span></div>';
    } else {
        searchResults.innerHTML = jobs.slice(0, 6).map(job => `
            <div class="search-result-item" onclick="window.open('${escapeAttr(job.job_url || '#')}', '_blank')">
                <div class="search-result-title">${escapeHtml(job.title)}</div>
                <div class="search-result-meta">${escapeHtml(job.company)} · ${escapeHtml(job.location)}</div>
            </div>
        `).join('');
    }
    searchResults.classList.add('show');
}

// ------------------------------------------------------------------
// Search mode system
// ------------------------------------------------------------------
function setupModeGroup(groupName, hiddenId, noteId) {
    const wrapper = document.querySelector(`[data-mode-group="${groupName}"]`);
    if (!wrapper) return;
    const buttons = wrapper.querySelectorAll('[data-search-mode]');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.searchMode;
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const hidden = document.getElementById(hiddenId);
            if (hidden) hidden.value = mode;
            updateModeUI(groupName, mode, noteId);
        });
    });
}

function updateModeUI(groupName, mode, noteId) {
    const scope = groupName === 'dashboard' ? document : document.getElementById('scrapeModal');
    if (!scope) return;
    const keywordFields = scope.querySelectorAll('[data-field="keyword"]');
    const locationFields = scope.querySelectorAll('[data-field="location"]');
    const sourceFields = scope.querySelectorAll('[data-field="sources"]');
    const note = document.getElementById(noteId);

    keywordFields.forEach(el => el.classList.toggle('d-none', mode === 'demo'));
    locationFields.forEach(el => el.classList.toggle('d-none', mode !== 'keyword_location'));
    sourceFields.forEach(el => el.classList.toggle('d-none', mode === 'demo'));
    if (note) note.classList.toggle('d-none', mode !== 'demo');

    const primary = groupName === 'dashboard' ? document.getElementById('runModeSearch') : document.getElementById('startScrape');
    if (primary) {
        primary.innerHTML = mode === 'demo'
            ? '<i class="bi bi-speedometer2 me-1"></i> Load Demo Dashboard'
            : '<i class="bi bi-rocket-takeoff me-1"></i> Run Search';
    }
}

setupModeGroup('dashboard', 'dashboardSearchMode', 'dashboardDemoNote');
setupModeGroup('modal', 'scrapeSearchMode', 'modalDemoNote');

function getDashboardPayload(forceDemo = false) {
    const mode = forceDemo ? 'demo' : (document.getElementById('dashboardSearchMode')?.value || 'keyword_location');
    const payload = { search_mode: mode };
    if (mode !== 'demo') {
        payload.keyword = document.getElementById('dashboardKeyword')?.value?.trim() || '';
        payload.location = mode === 'keyword_location' ? (document.getElementById('dashboardLocation')?.value?.trim() || '') : '';
        payload.sources = [];
        if (document.getElementById('dashboardSrcLinkedin')?.checked) payload.sources.push('linkedin');
        if (document.getElementById('dashboardSrcIndeed')?.checked) payload.sources.push('indeed');
    }
    return payload;
}

function getModalPayload() {
    const mode = document.getElementById('scrapeSearchMode')?.value || 'keyword_location';
    const payload = { search_mode: mode };
    if (mode !== 'demo') {
        payload.keyword = document.getElementById('scrapeKeyword')?.value?.trim() || '';
        payload.location = mode === 'keyword_location' ? (document.getElementById('scrapeLocation')?.value?.trim() || '') : '';
        payload.sources = [];
        if (document.getElementById('srcLinkedin')?.checked) payload.sources.push('linkedin');
        if (document.getElementById('srcIndeed')?.checked) payload.sources.push('indeed');
    }
    return payload;
}

async function runSearchMode(payload, resultElement, button) {
    if (!payload.search_mode) payload.search_mode = 'keyword_location';
    if (payload.search_mode !== 'demo' && !payload.keyword) {
        showToast('Please enter a keyword', 'error');
        return;
    }
    if (payload.search_mode === 'keyword_location' && !payload.location) {
        showToast('Please enter a location', 'error');
        return;
    }
    if (payload.search_mode !== 'demo' && (!payload.sources || payload.sources.length === 0)) {
        showToast('Select at least one source', 'error');
        return;
    }

    const originalHtml = button ? button.innerHTML : '';
    if (button) {
        button.disabled = true;
        button.innerHTML = payload.search_mode === 'demo'
            ? '<i class="bi bi-hourglass-split me-1"></i> Loading demo...'
            : '<i class="bi bi-hourglass-split me-1"></i> Scraping...';
    }
    if (resultElement) {
        resultElement.classList.remove('d-none');
        resultElement.innerHTML = `<div class="skeleton-line"></div><div class="skeleton-line short"></div><p class="text-muted-light mt-2 mb-0">${payload.search_mode === 'demo' ? 'Loading demo-only MongoDB analytics...' : 'Launching Playwright and collecting jobs...'}</p>`;
    }

    try {
        const resp = await fetch('/scraper/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) throw new Error(data.error || 'Search failed');

        if (payload.search_mode === 'demo') {
            if (resultElement) resultElement.innerHTML = `<strong>Demo dashboard loaded.</strong><br><span>Opening demo-only analytics from saved MongoDB data...</span>`;
            showToast('Demo dashboard loaded', 'success');
            setTimeout(() => window.location.href = (data.dashboard_url || '/dashboard/demo'), 700);
            return;
        }

        const li = data.results?.linkedin || {};
        const ind = data.results?.indeed || {};
        const sourceSummary = (label, src) => {
            if (src.error) return `${label}: <span class="text-danger">${escapeHtml(src.error)}</span>`;
            const fetched = src.fetched ?? src.scraped ?? 0;
            const inserted = src.inserted ?? 0;
            const duplicates = src.duplicates ?? 0;
            const failed = src.failed ?? 0;
            return `${label}: Fetched <b>${fetched}</b> · Inserted <b>${inserted}</b> · Duplicates <b>${duplicates}</b>${failed ? ` · Failed <b>${failed}</b>` : ''}`;
        };
        if (resultElement) {
            resultElement.innerHTML = `
                <strong>Search complete</strong>
                <div class="result-grid">
                    <span>Mode: <b>${escapeHtml(data.mode)}</b></span>
                    <span>Fetched: <b>${data.results.total_fetched || 0}</b></span>
                    <span>Inserted/New: <b>${data.results.total_new || 0}</b></span>
                    <span>Duplicates skipped: <b>${data.results.total_duplicates || 0}</b></span>
                    <span>Duration: <b>${data.duration || 0}s</b></span>
                </div>
                <small>${sourceSummary('LinkedIn', li)}<br>${sourceSummary('Indeed', ind)}</small>
            `;
        }
        showToast(`${data.results.total_new || 0} new jobs inserted; ${data.results.total_duplicates || 0} duplicates skipped`, 'success');
        setTimeout(() => window.location.reload(), 1800);
    } catch (e) {
        if (resultElement) resultElement.innerHTML = `<strong>Search failed</strong><br><span class="text-danger">${escapeHtml(e.message)}</span>`;
        showToast(e.message, 'error');
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = originalHtml;
        }
    }
}

const runModeSearch = document.getElementById('runModeSearch');
if (runModeSearch) {
    runModeSearch.addEventListener('click', () => runSearchMode(getDashboardPayload(false), document.getElementById('searchModeResult'), runModeSearch));
}

const loadDemoDashboard = document.getElementById('loadDemoDashboard');
if (loadDemoDashboard) {
    loadDemoDashboard.addEventListener('click', () => runSearchMode(getDashboardPayload(true), document.getElementById('searchModeResult'), loadDemoDashboard));
}

const seedDemoBtn = document.getElementById('seedDemoBtn');
if (seedDemoBtn) {
    seedDemoBtn.addEventListener('click', async () => {
        const original = seedDemoBtn.innerHTML;
        seedDemoBtn.disabled = true;
        seedDemoBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Seeding...';
        try {
            const resp = await fetch('/scraper/seed-demo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ count: 90 })
            });
            const data = await resp.json();
            if (!data.success) throw new Error(data.error || 'Seed failed');
            showToast(`${data.result.inserted} demo jobs added`, 'success');
            setTimeout(() => window.location.href = (data.dashboard_url || '/dashboard/demo'), 700);
        } catch (e) {
            showToast(e.message, 'error');
        } finally {
            seedDemoBtn.disabled = false;
            seedDemoBtn.innerHTML = original;
        }
    });
}

const startScrapeBtn = document.getElementById('startScrape');
if (startScrapeBtn) {
    startScrapeBtn.addEventListener('click', async () => {
        const progressDiv = document.getElementById('scrapeProgress');
        const resultDiv = document.getElementById('scrapeResult');
        const statusEl = document.getElementById('scrapeStatus');
        if (progressDiv) progressDiv.style.display = 'block';
        if (resultDiv) resultDiv.style.display = 'none';
        if (statusEl) statusEl.textContent = 'Preparing selected search mode...';
        await runSearchMode(getModalPayload(), resultDiv, startScrapeBtn);
        if (progressDiv) progressDiv.style.display = 'none';
        if (resultDiv) resultDiv.style.display = 'block';
    });
}

async function loadRecentJobs() {
    const tbody = document.getElementById('recentJobsBody');
    if (!tbody) return;
    try {
        const resp = await fetch('/jobs/search?page=1&per_page=10');
        const data = await resp.json();
        if (!data.jobs || data.jobs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No jobs found. Seed demo data or run a search.</td></tr>';
            return;
        }
        tbody.innerHTML = data.jobs.slice(0, 8).map(job => `
            <tr>
                <td><a href="${escapeAttr(job.job_url || '#')}" target="_blank" class="job-title-link">${escapeHtml(job.title)}</a></td>
                <td><span class="company-name">${escapeHtml(job.company)}</span></td>
                <td><span class="location-text"><i class="bi bi-geo-alt"></i> ${escapeHtml(job.location)}</span></td>
                <td>${(job.skills || []).slice(0, 3).map(s => `<span class="skill-badge">${escapeHtml(s)}</span>`).join('')}</td>
                <td><span class="source-badge source-${escapeAttr(job.source)}">${escapeHtml(job.source)}</span></td>
                <td>${job.is_remote ? '<span class="badge-remote">Remote</span>' : '<span class="badge-onsite">Onsite</span>'}</td>
            </tr>
        `).join('');
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Failed to load jobs.</td></tr>';
    }
}

function animateCounters() {
    document.querySelectorAll('.count-up').forEach(el => {
        const target = parseFloat(el.dataset.count || '0');
        const duration = 900;
        const start = performance.now();
        function tick(now) {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const value = target * eased;
            el.textContent = Number.isInteger(target) ? Math.round(value) : value.toFixed(1);
            if (progress < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    });
}

function refreshAnalytics() {
    showToast('Refreshing analytics...');
    setTimeout(() => window.location.reload(), 400);
}

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}
function escapeAttr(str) {
    return String(str || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
