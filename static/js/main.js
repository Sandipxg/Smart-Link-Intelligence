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
        let totalClicks = 0;
        if (data.hourly) {
            data.hourly.forEach(item => {
                hourlyData[item.hour] = item.count;
                totalClicks += item.count;
            });
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

    // 3. User Intent Classification Chart
    const intentCtx = document.getElementById('intentClassificationChart');
    if (intentCtx && data.intent) {
        const totalIntent = (data.intent.curious || 0) + (data.intent.interested || 0) + (data.intent.engaged || 0);
        const labels = ['Curious', 'Interested', 'Engaged'];
        const chartData = totalIntent === 0
            ? [1, 1, 1]
            : [data.intent.curious || 0, data.intent.interested || 0, data.intent.engaged || 0];

        new Chart(intentCtx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: chartData,
                    backgroundColor: [
                        'rgba(107, 114, 128, 0.8)',
                        'rgba(251, 191, 36, 0.8)',
                        'rgba(34, 197, 94, 0.8)'
                    ],
                    borderColor: ['#6b7280', '#fbbf24', '#22c55e'],
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
                                if (totalIntent === 0) return context.label + ': No data yet';
                                const percentage = ((context.parsed * 100) / totalIntent).toFixed(1);
                                return context.label + ': ' + context.parsed + ' (' + percentage + '%)';
                            }
                        }
                    }
                }
            }
        });
    }

    // 4. Traffic Quality Chart
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
                        'rgba(34, 197, 94, 0.8)',
                        'rgba(239, 68, 68, 0.8)'
                    ],
                    borderColor: ['#22c55e', '#ef4444'],
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
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Daily Clicks',
                    data: chartData,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    pointBackgroundColor: '#8b5cf6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
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

    // 6. Users by Region Chart (Pie Chart)
    const regionCtx = document.getElementById('regionChart');
    if (regionCtx) {
        const regionData = data.region || [];
        const labels = regionData.length > 0
            ? regionData.map(r => r.location)
            : ['No data yet'];
        const chartData = regionData.length > 0
            ? regionData.map(r => r.count)
            : [1];

        new Chart(regionCtx, {
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
                        'rgba(239, 68, 68, 0.8)'
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
                                if (regionData.length === 0) return 'No visitors yet';
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed * 100) / total).toFixed(1);
                                return context.label + ': ' + context.parsed + ' (' + percentage + '%)';
                            }
                        }
                    }
                }
            }
        });
    }

    // 7. Users by Device Chart (Pie Chart)
    const deviceCtx = document.getElementById('deviceChart');
    if (deviceCtx) {
        const deviceData = data.device || [];
        const labels = deviceData.length > 0
            ? deviceData.map(d => d.device)
            : ['No data yet'];
        const chartData = deviceData.length > 0
            ? deviceData.map(d => d.count)
            : [1];

        new Chart(deviceCtx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: chartData,
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.8)',
                        'rgba(168, 85, 247, 0.8)',
                        'rgba(236, 72, 153, 0.8)'
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
                                if (deviceData.length === 0) return 'No visitors yet';
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed * 100) / total).toFixed(1);
                                return context.label + ': ' + context.parsed + ' (' + percentage + '%)';
                            }
                        }
                    }
                }
            }
        });
    }

    // 8. Users by ISP Chart (Pie Chart)
    const ispCtx = document.getElementById('ispChart');
    if (ispCtx) {
        const ispData = data.isp || [];
        const labels = ispData.length > 0
            ? ispData.map(i => i.provider)
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