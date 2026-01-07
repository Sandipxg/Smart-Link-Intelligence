// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function () {
    // Get app configuration from data attributes
    const appData = document.getElementById('app-data');
    if (appData) {
        window.APP_CONFIG = {
            loginUrl: appData.dataset.loginUrl,
            analyticsUrl: appData.dataset.analyticsUrl,
            isAuthenticated: appData.dataset.authenticated === 'true'
        };
    }

    // Local Time Conversion Helper
    const localizeTimestamps = () => {
        const timeElements = document.querySelectorAll('.local-time');
        const formatOptions = {
            year: 'numeric', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit',
            hour12: true
        };
        const formatter = new Intl.DateTimeFormat(undefined, formatOptions);

        timeElements.forEach(el => {
            const rawTime = el.textContent.trim();
            if (!rawTime || rawTime === 'N/A') return;

            try {
                // Flask usually gives ISO format
                let date;
                if (rawTime.includes(' ')) {
                    // Handle "YYYY-MM-DD HH:MM:SS" format often used in SQLite
                    date = new Date(rawTime.replace(' ', 'T') + 'Z');
                } else {
                    date = new Date(rawTime.endsWith('Z') ? rawTime : rawTime + 'Z');
                }

                if (!isNaN(date.getTime())) {
                    el.textContent = formatter.format(date);
                    el.classList.remove('local-time'); // Prevent double processing
                    el.title = `Original (UTC): ${rawTime}`;
                }
            } catch (e) {
                console.error("Localization error:", e, rawTime);
            }
        });
    };

    // Initial localization
    localizeTimestamps();

    // Global functions for navigation
    window.showCreateLinkModal = function () {
        if (window.APP_CONFIG && window.APP_CONFIG.isAuthenticated) {
            const modal = new bootstrap.Modal(document.getElementById('quickCreateModal'));
            modal.show();
        } else {
            window.location.href = window.APP_CONFIG ? window.APP_CONFIG.loginUrl : '/login';
        }
    };

    window.showAnalyticsOverview = function () {
        if (window.APP_CONFIG && window.APP_CONFIG.isAuthenticated) {
            window.location.href = window.APP_CONFIG.analyticsUrl;
        } else {
            window.location.href = window.APP_CONFIG ? window.APP_CONFIG.loginUrl : '/login';
        }
    };

    // Toggle form fields based on behavior rule selection
    window.toggleFormFields = function () {
        const behaviorRule = document.getElementById('behaviorRule');
        const progressiveFields = document.getElementById('progressiveFields');
        const standardInfo = document.getElementById('standardInfo');
        const progressionInfo = document.getElementById('progressionInfo');

        if (!behaviorRule || !progressiveFields) {
            return;
        }

        if (behaviorRule.value === 'progression') {
            progressiveFields.style.display = 'block';
            if (standardInfo) standardInfo.style.display = 'none';
            if (progressionInfo) progressionInfo.style.display = 'block';

            // Make returning_url and cta_url required for progression
            const returningUrl = document.querySelector('input[name="returning_url"]');
            const ctaUrl = document.querySelector('input[name="cta_url"]');
            if (returningUrl) returningUrl.required = true;
            if (ctaUrl) ctaUrl.required = true;
        } else {
            progressiveFields.style.display = 'none';
            if (standardInfo) standardInfo.style.display = 'block';
            if (progressionInfo) progressionInfo.style.display = 'none';

            // Remove required attribute for standard redirect
            const returningUrl = document.querySelector('input[name="returning_url"]');
            const ctaUrl = document.querySelector('input[name="cta_url"]');
            if (returningUrl) returningUrl.required = false;
            if (ctaUrl) ctaUrl.required = false;
        }
    };

    // Reset form function
    window.resetForm = function () {
        const form = document.getElementById('linkCreateForm');
        if (form) {
            form.reset();
            const progressiveFields = document.getElementById('progressiveFields');
            const standardInfo = document.getElementById('standardInfo');
            const progressionInfo = document.getElementById('progressionInfo');

            if (progressiveFields) progressiveFields.style.display = 'none';
            if (standardInfo) standardInfo.style.display = 'block';
            if (progressionInfo) progressionInfo.style.display = 'none';

            // Remove required attributes
            const returningUrl = document.querySelector('input[name="returning_url"]');
            const ctaUrl = document.querySelector('input[name="cta_url"]');
            if (returningUrl) returningUrl.required = false;
            if (ctaUrl) ctaUrl.required = false;

            // Remove validation classes
            form.classList.remove('was-validated');
        }
    };

    // Initialize form state
    if (window.toggleFormFields) {
        window.toggleFormFields();
    }

    // Chart.js default configuration
    Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
    Chart.defaults.color = '#6b7280';

    // Dashboard Link Status Chart (for index page)
    if (window.dashboardData && document.getElementById('linkStatusChart')) {
        const linkStats = window.dashboardData.linkStats || [];

        if (linkStats.length > 0) {
            const labels = linkStats.map(item => item.state);
            const data = linkStats.map(item => item.count);
            const colors = {
                'Active': 'rgba(34, 197, 94, 0.8)',
                'High Interest': 'rgba(59, 130, 246, 0.8)',
                'Decaying': 'rgba(251, 191, 36, 0.8)',
                'Inactive': 'rgba(239, 68, 68, 0.8)'
            };

            const backgroundColors = labels.map(label => colors[label] || 'rgba(107, 114, 128, 0.8)');
            const borderColors = labels.map(label => colors[label]?.replace('0.8', '1') || '#6b7280');

            new Chart(document.getElementById('linkStatusChart'), {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: backgroundColors,
                        borderColor: borderColors,
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                usePointStyle: true,
                                pointStyle: 'circle',
                                font: {
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: 12,
                            cornerRadius: 8,
                            callbacks: {
                                label: function (context) {
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((context.parsed * 100) / total).toFixed(1);
                                    return `${context.label}: ${context.parsed} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    // Check if we're on the analytics page
    if (!window.analyticsData) {
        if (document.getElementById('attentionDecayChart')) {
            console.error('Analytics data missing! window.analyticsData is undefined.');
        }
        return;
    }

    const data = window.analyticsData;
    console.log('Analytics data loaded:', data);

    // Helper function to show insufficient data message
    function showInsufficientDataMessage(canvasElement) {
        const container = canvasElement.parentElement;
        canvasElement.style.display = 'none';

        const messageDiv = document.createElement('div');
        messageDiv.className = 'alert alert-info d-flex align-items-center justify-content-center';
        messageDiv.style.height = '280px';
        messageDiv.innerHTML = `
            <div class="text-center">
                <svg width="48" height="48" fill="currentColor" class="text-info mb-3" viewBox="0 0 16 16">
                    <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2z"/>
                </svg>
                <p class="mb-0 fw-medium">Not enough data yet</p>
                <p class="small text-muted mb-0">Waiting for more visitors...</p>
            </div>
        `;
        container.appendChild(messageDiv);
    }

    // Relaxed check: Simply checking if we have ANY data
    function hasData(dataArray) {
        return dataArray && Array.isArray(dataArray) && dataArray.length > 0;
    }

    // 1. Attention Decay Chart
    const attentionCtx = document.getElementById('attentionDecayChart');
    if (attentionCtx) {
        const attentionData = data.attention || [];
        const labels = attentionData.length > 0
            ? attentionData.map(d => d.day)
            : ['No data yet'];
        const chartData = attentionData.length > 0
            ? attentionData.map(d => d.count)
            : [0];

        new Chart(attentionCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Clicks per Day',
                    data: chartData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#3b82f6'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 },
                        grid: { color: 'rgba(0, 0, 0, 0.05)' }
                    },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    // 2. Click Frequency Chart (Hourly)
    const frequencyCtx = document.getElementById('clickFrequencyChart');
    if (frequencyCtx) {
        const hourlyData = Array(24).fill(0);
        const browserOffsetHours = -new Date().getTimezoneOffset() / 60;

        if (data.hourly) {
            data.hourly.forEach(item => {
                // Shift UTC hour to local hour
                let localHour = Math.round(item.hour + browserOffsetHours) % 24;
                if (localHour < 0) localHour += 24;
                hourlyData[localHour] += item.count;
            });
        }

        // Update the card title to indicate localization
        const hourlyTitle = frequencyCtx.closest('.card-body')?.querySelector('h4');
        if (hourlyTitle) {
            hourlyTitle.innerHTML += ' <small class="text-muted fw-normal" style="font-size: 0.75rem;">(Local Time)</small>';
        }

        new Chart(frequencyCtx, {
            type: 'line',
            data: {
                labels: Array.from({ length: 24 }, (_, i) => i + ':00'),
                datasets: [{
                    label: 'Clicks',
                    data: hourlyData,
                    backgroundColor: 'rgba(99, 102, 241, 0.2)',
                    borderColor: '#6366f1',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#6366f1',
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 },
                        grid: { color: 'rgba(0, 0, 0, 0.05)' }
                    },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    // 3. User Intent - Handled via CSS Funnel in HTML now
    // Chart.js initialization removed to prevent errors


    // 4. Traffic Quality Chart
    // 4. Traffic Quality Chart (Gauge Style)
    const qualityCtx = document.getElementById('trafficQualityChart');
    if (qualityCtx && data.quality) {
        const totalQuality = (data.quality.human || 0) + (data.quality.suspicious || 0);
        const labels = ['Human Traffic', 'Suspicious'];
        const chartData = totalQuality === 0
            ? [1, 0]
            : [data.quality.human || 0, data.quality.suspicious || 0];

        new Chart(qualityCtx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: chartData,
                    backgroundColor: [
                        '#22c55e', // Vibrant Green
                        '#ef4444'  // Red
                    ],
                    borderWidth: 0,
                    borderRadius: 20,
                    cutout: '75%',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                rotation: -90,
                circumference: 180,
                layout: {
                    padding: { bottom: 20 }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                if (totalQuality === 0) return context.label + ': No data yet';
                                const percentage = ((context.parsed * 100) / totalQuality).toFixed(1);
                                return context.label + ': ' + context.parsed + ' (' + percentage + '%)';
                            }
                        }
                    }
                }
            }
        });
    }

    // 5. Daily Engagement Trends Chart
    // 5. Daily Engagement Trends Chart (Bar Chart)
    const dailyCtx = document.getElementById('dailyEngagementChart');
    if (dailyCtx) {
        const dailyData = data.daily || [];
        const labels = dailyData.length > 0
            ? dailyData.map(d => d.day)
            : ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const chartData = dailyData.length > 0
            ? dailyData.map(d => d.count)
            : [0, 0, 0, 0, 0, 0, 0];

        new Chart(dailyCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Daily Clicks',
                    data: chartData,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.7)',
                    borderWidth: 1,
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            title: function (context) {
                                return context[0].label;
                            },
                            label: function (context) {
                                if (dailyData.length === 0) return 'No data yet';
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((context.parsed.y * 100) / total).toFixed(1) : 0;
                                return `${context.parsed.y} clicks (${percentage}%)`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 },
                        grid: { color: 'rgba(0, 0, 0, 0.05)' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: {
                            font: { weight: 'bold' }
                        }
                    }
                }
            }
        });
    }

    // 6. Users by Region (World Map SVG)
    const worldMap = document.getElementById('worldMap');
    if (worldMap) {
        const regionData = data.region || [];
        console.log('Updating World Map with data:', regionData);

        // Map backend continent names to SVG IDs
        const continentMap = {
            'North America': 'na',
            'South America': 'sa',
            'Europe': 'eu',
            'Africa': 'af',
            'Asia': 'as',
            'Oceania': 'oc',
            'Australia': 'oc' // Handle alias
        };

        // Reset all labels to 0
        Object.values(continentMap).forEach(code => {
            const label = document.getElementById(`label-${code}`);
            if (label) label.textContent = '0';
        });

        // Update counts based on data
        regionData.forEach(item => {
            const code = continentMap[item.location];
            if (code) {
                const label = document.getElementById(`label-${code}`);
                const path = document.getElementById(`path-${code}`);

                if (label) {
                    label.textContent = item.count;
                    label.classList.add('label-visible');
                }
                if (path) {
                    // Make active continents simplified blue
                    path.classList.add('continent-active');

                    // Add simple tooltip on hover
                    path.addEventListener('mouseenter', () => {
                        label.style.opacity = '1';
                    });
                    path.addEventListener('mouseleave', () => {
                        // Keep opacity if it has significant data, simplified logic
                    });
                }
            }
        });
    }

    // 7. Device Breakdown (Icons Bar)
    // Logic to update the progress bar widths and labels
    const deviceBarContainer = document.getElementById('deviceBarContainer');
    if (deviceBarContainer && data.device) {
        const deviceData = data.device || [];
        let mobileCount = 0;
        let desktopCount = 0;

        deviceData.forEach(d => {
            const name = d.device.toLowerCase();
            if (name.includes('mobile') || name.includes('android') || name.includes('iphone') || name.includes('ipad') || name.includes('tablet')) {
                mobileCount += d.count;
            } else {
                desktopCount += d.count;
            }
        });

        const totalDevices = mobileCount + desktopCount;
        const mobilePct = totalDevices > 0 ? Math.round((mobileCount / totalDevices) * 100) : 0;
        const desktopPct = totalDevices > 0 ? Math.round((desktopCount / totalDevices) * 100) : 0;

        // Update Widths
        const mobileBar = document.getElementById('deviceBarMobile');
        const desktopBar = document.getElementById('deviceBarDesktop');
        if (mobileBar) mobileBar.style.width = `${mobilePct}%`;
        if (desktopBar) desktopBar.style.width = `${desktopPct}%`;

        // Update Labels with LARGE icons
        const mobileLabel = document.getElementById('deviceLabelMobile');
        const desktopLabel = document.getElementById('deviceLabelDesktop');
        // Mobile Icon
        if (mobileLabel) {
            mobileLabel.innerHTML = `
                <i class="bi bi-phone-vibrate fs-3 d-block mb-1 text-primary"></i>
                <span class="fs-5 fw-bold text-dark">${mobilePct}%</span>
             `;
        }
        // Desktop Icon
        if (desktopLabel) {
            desktopLabel.innerHTML = `
                <i class="bi bi-laptop fs-3 d-block mb-1 text-warning"></i>
                <span class="fs-5 fw-bold text-dark">${desktopPct}%</span>
             `;
        }

        // Update Counts
        const mobileCountEl = document.getElementById('deviceCountMobile');
        const desktopCountEl = document.getElementById('deviceCountDesktop');
        if (mobileCountEl) mobileCountEl.textContent = `${mobileCount} Devices`;
        if (desktopCountEl) desktopCountEl.textContent = `${desktopCount} Devices`;
    }

    // 8. Users by ISP Chart (Pie Chart)
    const ispCtx = document.getElementById('ispChart');
    if (ispCtx) {
        try {
            const ispData = data.isp || [];
            console.log('Rendering ISP Chart with data:', ispData);

            const labels = ispData.length > 0
                ? ispData.map(i => i.provider || 'Other/Unknown')
                : ['No data yet'];
            const chartData = ispData.length > 0
                ? ispData.map(i => i.count)
                : [1];

            new Chart(ispCtx, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: chartData,
                        backgroundColor: [
                            'rgba(59, 130, 246, 0.8)',
                            'rgba(168, 85, 247, 0.8)',
                            'rgba(236, 72, 153, 0.8)',
                            'rgba(34, 197, 94, 0.8)',
                            'rgba(245, 158, 11, 0.8)',
                            'rgba(239, 68, 68, 0.8)',
                            'rgba(107, 114, 128, 0.8)',
                            'rgba(99, 102, 241, 0.8)',
                            'rgba(139, 92, 246, 0.8)',
                            'rgba(232, 121, 249, 0.8)'
                        ],
                        borderColor: '#ffffff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                usePointStyle: true,
                                pointStyle: 'circle'
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    if (ispData.length === 0) return 'No ISP data yet';
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((context.parsed * 100) / total).toFixed(1);
                                    return context.label + ': ' + context.parsed + ' (' + percentage + '%)';
                                }
                            }
                        }
                    }
                }
            });
        } catch (e) {
            console.error('Failed to initialize ISP Chart:', e);
        }
    }

    // 9. Users by Country Chart (Doughnut Chart)
    const countryCtx = document.getElementById('countryChart');
    const countryTableBody = document.getElementById('countryTableBody');

    if (countryCtx) {
        try {
            const countryData = data.country || [];
            console.log('Rendering Country Chart with data:', countryData);

            const labels = countryData.length > 0
                ? countryData.map(c => c.country || 'Unknown')
                : ['No data yet'];
            const chartData = countryData.length > 0
                ? countryData.map(c => c.count)
                : [1];

            // Render Chart
            new Chart(countryCtx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: chartData,
                        backgroundColor: [
                            'rgba(16, 185, 129, 0.8)', // Emerald
                            'rgba(59, 130, 246, 0.8)', // Blue
                            'rgba(249, 115, 22, 0.8)', // Orange
                            'rgba(236, 72, 153, 0.8)', // Pink
                            'rgba(107, 114, 128, 0.8)', // Gray
                            'rgba(139, 92, 246, 0.8)', // Violet
                            'rgba(252, 165, 165, 0.8)'  // Light Red
                        ],
                        borderColor: '#ffffff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 10,
                                usePointStyle: true,
                                pointStyle: 'circle',
                                font: { size: 11 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    if (countryData.length === 0) return 'No country data yet';
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((context.parsed * 100) / total).toFixed(1);
                                    return context.label + ': ' + context.parsed + ' (' + percentage + '%)';
                                }
                            }
                        }
                    },
                    layout: {
                        padding: { bottom: 10 }
                    }
                }
            });

            // Iterate and Populate Table
            if (countryTableBody) {
                countryTableBody.innerHTML = ''; // Clear existing
                if (countryData.length > 0) {
                    countryData.slice(0, 10).forEach(item => {
                        const tr = document.createElement('tr');
                        // Calculate percentage based on total unique visitors or total chart data
                        const totalVisitors = ((data.totals || {}).unique_visitors) || chartData.reduce((a, b) => a + b, 0) || 1;
                        const pct_calc = Math.round((item.count * 100) / totalVisitors);

                        tr.innerHTML = `
                             <td class="ps-2">${item.country || 'Unknown'}</td>
                             <td class="text-end pe-2">
                                <span class="fw-bold">${item.count}</span>
                                <span class="text-muted small ms-1">(${pct_calc}%)</span>
                             </td>
                         `;
                        countryTableBody.appendChild(tr);
                    });
                } else {
                    countryTableBody.innerHTML = '<tr><td colspan="2" class="text-center small text-muted py-3">No data available</td></tr>';
                }
            }

        } catch (e) {
            console.error('Failed to initialize Country Chart:', e);
        }
    }

    // Export to CSV Function
    window.exportToCSV = function () {
        if (!data) return;

        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += "Category,Key,Value\n";

        // Add Summary Stats
        csvContent += `Summary,Total Clicks,${(data.intent.curious + data.intent.interested + data.intent.engaged) || 0}\n`;
        csvContent += `Summary,Human Traffic,${data.quality.human || 0}\n`;
        csvContent += `Summary,Suspicious Activity,${data.quality.suspicious || 0}\n`;

        // Add Regional Data (Continents)
        if (data.region) {
            data.region.forEach(r => {
                csvContent += `Continent,${r.location},${r.count}\n`;
            });
        }

        // Add Device Data
        if (data.device) {
            data.device.forEach(d => {
                csvContent += `Device,${d.device},${d.count}\n`;
            });
        }

        // Add ISP Data
        if (data.isp) {
            data.isp.forEach(i => {
                csvContent += `ISP,${i.provider},${i.count}\n`;
            });
        }

        // Add Hourly Data
        if (data.hourly) {
            data.hourly.forEach(h => {
                csvContent += `Hourly Click Pattern,${h.hour}:00,${h.count}\n`;
            });
        }

        // Add Daily Data
        if (data.daily) {
            data.daily.forEach(d => {
                csvContent += `Daily Pattern,${d.day},${d.count}\n`;
            });
        }

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "analytics_report.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };
});