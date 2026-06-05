/**
 * AI Trend premium Chart.js visualizations.
 */
const CHART_DEFAULTS = {
    color: {
        text: '#a9afc3',
        grid: 'rgba(255,255,255,0.06)',
        blue: '#4f9eff',
        green: '#3ecf8e',
        purple: '#a78bfa',
        orange: '#fb923c',
        red: '#f87171',
        cyan: '#22d3ee'
    }
};

if (typeof Chart !== 'undefined') {
    Chart.defaults.color = CHART_DEFAULTS.color.text;
    Chart.defaults.font.family = "'DM Sans', sans-serif";
    Chart.defaults.plugins.tooltip.backgroundColor = '#0f1117';
    Chart.defaults.plugins.tooltip.borderColor = 'rgba(255,255,255,0.12)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
}

function gradient(ctx, area, from, to) {
    if (!area) return from;
    const g = ctx.createLinearGradient(0, area.bottom, 0, area.top);
    g.addColorStop(0, to);
    g.addColorStop(1, from);
    return g;
}

function initDashboardCharts(analytics) {
    if (!analytics || typeof Chart === 'undefined') return;
    initDailyTrendChart(analytics);
    initRemoteChart(analytics);
    initCompaniesChart(analytics);
    initSkillsChart(analytics);
    initWeeklySkillChart(analytics);
    initMonthlyHeatmap(analytics);
    initSalaryChart(analytics);
    initLocationChart(analytics);
}

function initDailyTrendChart(analytics) {
    const canvas = document.getElementById('trendsChart');
    if (!canvas || !analytics.daily_trends?.length) return;
    const ctx = canvas.getContext('2d');
    const labels = analytics.daily_trends.map(d => new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    const data = analytics.daily_trends.map(d => d.count);
    new Chart(canvas, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Jobs Scraped',
                data,
                borderColor: CHART_DEFAULTS.color.blue,
                backgroundColor: (context) => gradient(ctx, context.chart.chartArea, 'rgba(79,158,255,0.36)', 'rgba(79,158,255,0.02)'),
                borderWidth: 3,
                pointRadius: 3,
                pointHoverRadius: 6,
                pointBackgroundColor: CHART_DEFAULTS.color.cyan,
                fill: true,
                tension: 0.42
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 1200, easing: 'easeOutQuart' },
            interaction: { intersect: false, mode: 'index' },
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 7 } },
                y: { grid: { color: CHART_DEFAULTS.color.grid }, beginAtZero: true, ticks: { precision: 0 } }
            }
        }
    });
}

function initRemoteChart(analytics) {
    const canvas = document.getElementById('remoteChart');
    if (!canvas) return;
    const remote = analytics.remote_vs_onsite?.remote || 0;
    const onsite = analytics.remote_vs_onsite?.onsite || 0;
    new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: ['Remote / Hybrid', 'Onsite'],
            datasets: [{
                data: [remote, onsite],
                backgroundColor: ['rgba(62,207,142,0.78)', 'rgba(79,158,255,0.72)'],
                borderColor: ['#3ecf8e', '#4f9eff'],
                borderWidth: 2,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            cutout: '72%',
            animation: { animateRotate: true, duration: 1100 },
            plugins: { legend: { position: 'bottom', labels: { padding: 18, usePointStyle: true } } }
        }
    });
}

function initCompaniesChart(analytics) {
    const canvas = document.getElementById('companiesChart');
    if (!canvas || !analytics.top_companies?.length) return;
    const labels = analytics.top_companies.slice(0, 8).map(c => c.company);
    const data = analytics.top_companies.slice(0, 8).map(c => c.count);
    new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Job Postings',
                data,
                backgroundColor: (context) => {
                    const chart = context.chart;
                    const {ctx, chartArea} = chart;
                    return gradient(ctx, chartArea, 'rgba(79,158,255,0.84)', 'rgba(167,139,250,0.28)');
                },
                borderColor: CHART_DEFAULTS.color.blue,
                borderWidth: 1,
                borderRadius: 10,
                maxBarThickness: 40
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 1200, easing: 'easeOutCubic' },
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: CHART_DEFAULTS.color.grid }, beginAtZero: true, ticks: { precision: 0 } },
                y: { grid: { display: false } }
            }
        }
    });
}

function initSkillsChart(analytics) {
    const canvas = document.getElementById('skillsChart');
    if (!canvas || !analytics.top_skills?.length) return;
    const labels = analytics.top_skills.slice(0, 12).map(s => s.skill);
    const data = analytics.top_skills.slice(0, 12).map(s => s.count);
    new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Mentions',
                data,
                backgroundColor: labels.map((_, i) => `hsla(${195 + i * 14}, 82%, 62%, 0.30)`),
                borderColor: labels.map((_, i) => `hsl(${195 + i * 14}, 82%, 62%)`),
                borderWidth: 1,
                borderRadius: 8,
                maxBarThickness: 34
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 1000, delay: ctx => ctx.dataIndex * 35 },
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { maxRotation: 45, minRotation: 0 } },
                y: { grid: { color: CHART_DEFAULTS.color.grid }, beginAtZero: true, ticks: { precision: 0 } }
            }
        }
    });
}

function initWeeklySkillChart(analytics) {
    const canvas = document.getElementById('weeklySkillChart');
    const growth = analytics.weekly_skill_growth;
    if (!canvas || !growth?.labels?.length || !growth?.datasets?.length) return;
    const colors = [CHART_DEFAULTS.color.blue, CHART_DEFAULTS.color.green, CHART_DEFAULTS.color.purple, CHART_DEFAULTS.color.orange, CHART_DEFAULTS.color.cyan];
    new Chart(canvas, {
        type: 'line',
        data: {
            labels: growth.labels,
            datasets: growth.datasets.map((set, i) => ({
                label: set.skill,
                data: set.data,
                borderColor: colors[i % colors.length],
                backgroundColor: colors[i % colors.length] + '33',
                borderWidth: 2,
                tension: 0.38,
                pointRadius: 3,
                pointHoverRadius: 6
            }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            animation: { duration: 1200 },
            plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 14 } } },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: CHART_DEFAULTS.color.grid }, beginAtZero: true, ticks: { precision: 0 } }
            }
        }
    });
}

function initMonthlyHeatmap(analytics) {
    const target = document.getElementById('monthlyHeatmap');
    if (!target) return;
    const rows = analytics.monthly_heatmap || [];
    if (!rows.length) {
        target.innerHTML = '<div class="empty-chart">No monthly history yet</div>';
        return;
    }
    const max = Math.max(...rows.map(r => r.count), 1);
    target.innerHTML = rows.map(row => {
        const level = Math.max(8, Math.round((row.count / max) * 100));
        return `<div class="heat-cell" style="--heat:${level}%" title="${escapeHtml(row.period)} · ${escapeHtml(row.source)} · ${row.count}">
            <span>${escapeHtml(row.period)}</span><strong>${row.count}</strong><small>${escapeHtml(row.source)}</small>
        </div>`;
    }).join('');
}

function initSalaryChart(analytics) {
    const canvas = document.getElementById('salaryChart');
    if (!canvas || !analytics.salary_distribution?.ranges?.length) return;
    const labels = analytics.salary_distribution.ranges.map(r => r.range);
    const data = analytics.salary_distribution.ranges.map(r => r.count);
    new Chart(canvas, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Jobs', data, backgroundColor: 'rgba(167,139,250,0.28)', borderColor: CHART_DEFAULTS.color.purple, borderWidth: 1, borderRadius: 8 }] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { x: { grid: { display: false } }, y: { grid: { color: CHART_DEFAULTS.color.grid }, beginAtZero: true, ticks: { precision: 0 } } }
        }
    });
}

function initLocationChart(analytics) {
    const canvas = document.getElementById('locationChart');
    if (!canvas || !analytics.location_analytics?.length) return;
    const labels = analytics.location_analytics.slice(0, 8).map(l => String(l.location).split(',')[0]);
    const data = analytics.location_analytics.slice(0, 8).map(l => l.count);
    new Chart(canvas, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Jobs', data, backgroundColor: 'rgba(62,207,142,0.28)', borderColor: CHART_DEFAULTS.color.green, borderWidth: 1, borderRadius: 8 }] },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { x: { grid: { color: CHART_DEFAULTS.color.grid }, beginAtZero: true, ticks: { precision: 0 } }, y: { grid: { display: false } } }
        }
    });
}

function initAnalyticsCharts(analytics) {
    if (!analytics || typeof Chart === 'undefined') return;

    const skillsCtx = document.getElementById('analyticsSkillsChart');
    if (skillsCtx && analytics.top_skills?.length) {
        const labels = analytics.top_skills.slice(0, 15).map(s => s.skill);
        const data = analytics.top_skills.slice(0, 15).map(s => s.count);
        new Chart(skillsCtx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Demand',
                    data,
                    backgroundColor: labels.map((_, i) => `hsla(${200 + i * 11}, 82%, 62%, 0.28)`),
                    borderColor: labels.map((_, i) => `hsl(${200 + i * 11}, 82%, 62%)`),
                    borderWidth: 1,
                    borderRadius: 8
                }]
            },
            options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { grid: { color: CHART_DEFAULTS.color.grid }, beginAtZero: true, ticks: { precision: 0 } } } }
        });
    }

    const sourceCtx = document.getElementById('sourceChart');
    if (sourceCtx && analytics.source_breakdown?.length) {
        new Chart(sourceCtx, {
            type: 'pie',
            data: {
                labels: analytics.source_breakdown.map(s => s.source),
                datasets: [{
                    data: analytics.source_breakdown.map(s => s.count),
                    backgroundColor: ['rgba(79,158,255,0.7)', 'rgba(62,207,142,0.7)', 'rgba(167,139,250,0.7)'],
                    borderColor: ['#4f9eff', '#3ecf8e', '#a78bfa'],
                    borderWidth: 1
                }]
            },
            options: { responsive: true, plugins: { legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true } } } }
        });
    }

    const longCtx = document.getElementById('longTrendChart');
    if (longCtx && analytics.daily_trends?.length) {
        const labels = analytics.daily_trends.map(d => new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        const data = analytics.daily_trends.map(d => d.count);
        new Chart(longCtx, {
            type: 'line',
            data: { labels, datasets: [{ label: 'Jobs Posted', data, borderColor: CHART_DEFAULTS.color.purple, backgroundColor: 'rgba(167,139,250,0.22)', borderWidth: 2, tension: 0.4, fill: true, pointRadius: 2 }] },
            options: { responsive: true, interaction: { intersect: false, mode: 'index' }, plugins: { legend: { display: false } }, scales: { x: { grid: { color: CHART_DEFAULTS.color.grid }, ticks: { maxTicksLimit: 10 } }, y: { grid: { color: CHART_DEFAULTS.color.grid }, beginAtZero: true } } }
        });
    }

    const compCtx = document.getElementById('analyticsCompaniesChart');
    if (compCtx && analytics.top_companies?.length) {
        new Chart(compCtx, {
            type: 'bar',
            data: { labels: analytics.top_companies.map(c => c.company), datasets: [{ label: 'Job Postings', data: analytics.top_companies.map(c => c.count), backgroundColor: 'rgba(251,146,60,0.25)', borderColor: CHART_DEFAULTS.color.orange, borderWidth: 1, borderRadius: 4 }] },
            options: { indexAxis: 'y', responsive: true, plugins: { legend: { display: false } }, scales: { x: { grid: { color: CHART_DEFAULTS.color.grid }, beginAtZero: true }, y: { grid: { display: false } } } }
        });
    }

    const salCtx = document.getElementById('analyticsSalaryChart');
    if (salCtx && analytics.salary_distribution?.ranges?.length) {
        new Chart(salCtx, {
            type: 'bar',
            data: { labels: analytics.salary_distribution.ranges.map(r => r.range), datasets: [{ label: 'Jobs', data: analytics.salary_distribution.ranges.map(r => r.count), backgroundColor: 'rgba(167,139,250,0.3)', borderColor: CHART_DEFAULTS.color.purple, borderWidth: 1, borderRadius: 5 }] },
            options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { grid: { color: CHART_DEFAULTS.color.grid }, beginAtZero: true } } }
        });
    }
}

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}
