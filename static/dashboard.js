// Dashboard chart initialization
const chartCanvas = document.getElementById('myPieChart');
const ctx = chartCanvas.getContext('2d');

const labels = JSON.parse(chartCanvas.dataset.labels);
const values = JSON.parse(chartCanvas.dataset.values);

// Restrained, categorical palette shared by the pie slices and the legend,
// so every category gets a consistent color by position rather than a
// fragile per-label name match.
const CATEGORY_PALETTE = ['#0d6efd', '#64748b', '#f59e0b', '#10b981', '#94a3b8', '#a855f7'];
const formatRupees = (value) => `₹${Number(value || 0).toLocaleString('en-IN')}`;

function getThemeColor(varName) {
    return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

let pieChartInstance = null;
let barChartInstance = null;

// ======== Month Logic ======== 
const months = Array.from({ length: 12 }, (_, i) => {
  return new Intl.DateTimeFormat('en', { month: 'long' }).format(new Date(2000, i));
});


const monthDropdown = document.getElementById("monthDropdown");

window.addEventListener("DOMContentLoaded", ()=>{
  if (!monthDropdown) return;
  // If server rendered options exist, don't repopulate; just ensure selected value is numeric month
  if (monthDropdown.options.length === 0) {
    months.forEach(month =>{
      const option = document.createElement("option")
      option.text = month
      monthDropdown.appendChild(option);
    })
    monthDropdown.value = months[curr_month-1];
  } else {
    // Server-rendered options use numeric values
    monthDropdown.value = String(curr_month);
  }
})
function navigateToMonth(selectedMonth) {
  if (!selectedMonth) return;

  // If the selected value is numeric (server-rendered), use it directly
  const asNum = parseInt(selectedMonth, 10);
  let monthNumber = !isNaN(asNum) ? asNum : (months.indexOf(selectedMonth) + 1);
  if (!monthNumber) return;
  window.location.href = `/dashboard/${monthNumber}`;
}

// console.log(month_spending)
// console.log(prev_month_Transaction_amount)


    
const legendContainer = document.querySelector(".dashboard-legend");
window.addEventListener("DOMContentLoaded", ()=>{
    if (!legendContainer) return;
    const total = values.reduce((sum, value) => sum + value, 0);

    labels.forEach((label, index) => {
        const value = values[index];
        const share = total ? Math.round((value / total) * 100) : 0;
        const color = CATEGORY_PALETTE[index % CATEGORY_PALETTE.length];

        const item = document.createElement("div");
        item.className = "dashboard-legend-item";

        const dot = document.createElement("span");
        dot.className = "dashboard-legend-dot";
        dot.style.backgroundColor = color;

        const labelEl = document.createElement("span");
        labelEl.className = "dashboard-legend-label";
        labelEl.textContent = label;

        const valueEl = document.createElement("span");
        valueEl.className = "dashboard-legend-value";
        valueEl.textContent = formatRupees(value);

        const shareEl = document.createElement("span");
        shareEl.className = "dashboard-legend-share";
        shareEl.textContent = `${share}%`;

        item.append(dot, labelEl, valueEl, shareEl);
        legendContainer.appendChild(item);
    })
})

const smart_insights = document.querySelector(".smart_insights");
// const para = document.createElement('p');
// para.textContent = `Monthly Spending: ₹${values.reduce((a, b) => a + b, 0).toFixed(2)}`;
// smart_insights.appendChild(para);

const monthlySpending = values.reduce((a, b) => a + b, 0);

function getSmartInsights(label, value) {
    if (!smart_insights) return;

    const elm = document.createElement("p");
    if(label === "Food & Dining" && value > 3000){
        elm.textContent = `${label} accounts for ${((value/monthlySpending * 100).toFixed(2))}%(₹${value}) of your monthly spending.`;
    }
    if(label === "Shopping" && value > 2000){
        elm.textContent = `You have spent ${((value/monthlySpending * 100).toFixed(2))}%(₹${value}) on ${label} this month. Consider reducing your spending in this category.`;
    }
    if(label === "Health & Fitness" && value > 1500){
        elm.textContent = `You have spent ${((value/monthlySpending * 100).toFixed(2))}%(₹${value}) on ${label} this month.`;
    }
    if(label === "Bills & Utilities" && value > 3000){
        elm.textContent = `You have spent ${((value/monthlySpending * 100).toFixed(2))}%(₹${value}) on ${label} this month. Consider reducing your spending in this category.`;
    }
    if(label === "Groceries" && value > 2500){
        elm.textContent = `You have spent ${((value/monthlySpending * 100).toFixed(2))}%(₹${value}) on ${label} this month. Make sure to check for discounts and offers to save money.`;
    }
    elm.style.fontWeight = "bold"; 
    elm.style.fontSize = "18px";
    elm.style.display = "block";
    elm.style.marginBottom = "0.3rem"
    smart_insights.appendChild(elm);
    // return elm;
}

window.addEventListener("DOMContentLoaded", ()=>{
    labels.forEach((label, index) => {
        getSmartInsights(label, values[index]);
    })
})



// new Chart(ctx, {
//     type: 'pie',
//     data: {
//         labels: labels,
//         datasets: [{
//             label: 'Total Spent (₹)',
//             data: values,
//             backgroundColor: [
//                 'rgba(255, 99, 132, 0.7)',
//                 'rgba(54, 162, 235, 0.7)',
//                 'rgba(255, 206, 86, 0.7)',
//                 'rgba(75, 192, 192, 0.7)',
//                 'rgba(153, 102, 255, 0.7)'
//             ],
//             borderColor: '#ffffff',
//             borderWidth: 2
//         }]
//     },
//     options: {
//         responsive: true,
//         plugins: {
//             legend: { position: 'top' },
//             title: { display: true, text: 'Spending Distribution' }
//         }
//     }
// });


// const trendCtx = document.getElementById('trendChart').getContext('2d');
    
//     new Chart(trendCtx, {
//         type: 'line', // This tells Chart.js to make a trend line chart
//         data: {
//             labels:  trend_labels | safe , // Chronological months from Python
//             datasets: [{
//                 label: 'Monthly Spending (₹)',
//                 data:  trend_values | safe, // Matching total spent amounts
//                 borderColor: '#4e73df', // Clean professional blue line
//                 backgroundColor: 'rgba(78, 115, 223, 0.05)', // Light blue shade under the line
//                 tension: 0.3, // Makes the line curved and smooth instead of jagged edges
//                 fill: true, // Fills the area underneath the line
//                 pointBackgroundColor: '#4e73df',
//                 pointRadius: 4
//             }]
//         },
//         options: {
//             responsive: true,
//             maintainAspectRatio: false,
//             scales: {
//                 y: {
//                     beginAtZero: true,
//                     title: { display: true, text: 'Amount Spent (₹)' }
//                 },
//                 x: {
//                     title: { display: true, text: 'Timeline' }
//                 }
//             }
//         }
//     });

// Wait for the DOM to load to ensure elements are ready
document.addEventListener("DOMContentLoaded", () => {
    
    // =========================================================
    // 1. RENDER PIE CHART
    // =========================================================
    const pieCanvas = document.getElementById('myPieChart');
    if (pieCanvas) {
        // Read the JSON strings from HTML data attributes and parse them back to JS arrays
        const pieLabels = JSON.parse(pieCanvas.dataset.labels || "[]");
        const pieValues = JSON.parse(pieCanvas.dataset.values || "[]");
        
        const ctx = pieCanvas.getContext('2d');
        pieChartInstance = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: pieLabels,
                datasets: [{
                    label: 'Total Spent (₹)',
                    data: pieValues,
                    backgroundColor: pieLabels.map((_, i) => CATEGORY_PALETTE[i % CATEGORY_PALETTE.length]),
                    borderColor: getThemeColor('--surface'),
                    borderWidth: 2,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 450, easing: 'easeOutQuart' },
                plugins: {
                    legend: { display: false },
                    title: { display: false },
                    tooltip: {
                        backgroundColor: getThemeColor('--chart-tooltip-bg'),
                        titleColor: getThemeColor('--chart-tooltip-text'),
                        bodyColor: getThemeColor('--chart-tooltip-text'),
                        borderColor: getThemeColor('--chart-grid'),
                        borderWidth: 1,
                        cornerRadius: 10,
                        displayColors: false,
                        padding: 10,
                        callbacks: {
                            label: (context) => formatRupees(context.parsed)
                        }
                    }
                }
            }
        });
    }

    // =========================================================
    // 2. RENDER TREND LINE CHART
    // =========================================================
//     const trendCanvas = document.getElementById('trendChart');
//     // const trendCanvas = document.querySelector('canvas'); // adjust selector if needed
// console.log("Labels:", `"${trendCanvas.dataset.labels}"`);
// console.log("Values:", `"${trendCanvas.dataset.values}"`);
//     if (trendCanvas) {
//         // Read and parse the trend analysis arrays from the dataset
//         const trendLabels = JSON.parse(trendCanvas.dataset.labels || "[]");
//         const trendValues = JSON.parse(trendCanvas.dataset.values || "[]");

        
        
//         const trendCtx = trendCanvas.getContext('2d');
//         new Chart(trendCtx, {
//             type: 'line',
//             data: {
//                 labels: trendLabels,
//                 datasets: [{
//                     label: 'Monthly Spending (₹)',
//                     data: trendValues,
//                     borderColor: '#4e73df',
//                     backgroundColor: 'rgba(78, 115, 223, 0.05)',
//                     tension: 0.3,
//                     fill: true,
//                     pointBackgroundColor: '#4e73df',
//                     pointRadius: 4
//                 }]
//             },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 scales: {
//                     y: {
//                         beginAtZero: true,
//                         title: { display: true, text: 'Amount Spent (₹)' }
//                     },
//                     x: {
//                         title: { display: true, text: 'Timeline' }
//                     }
//                 }
//             }
//         });
//     }
//         console.log("Trend Labels from HTML:", trendCanvas.dataset.labels);

  const barCanvas = document.getElementById('myChart');
  if (barCanvas) {
    const rawBarLabels = JSON.parse(barCanvas.dataset.labels || "[]");
    const rawBarValues = JSON.parse(barCanvas.dataset.values || "[]");

    // If the current month has fewer than five populated weeks, the backend
    // still sends placeholder trailing weeks with no spending. Trim those
    // trailing empty entries only (never a populated week in the middle)
    // so the chart fills its space naturally instead of showing dead bars.
    let lastPopulatedIndex = rawBarValues.length - 1;
    while (lastPopulatedIndex > 0 && !rawBarValues[lastPopulatedIndex]) {
      lastPopulatedIndex--;
    }
    const barLabels = rawBarLabels.slice(0, lastPopulatedIndex + 1);
    const barValues = rawBarValues.slice(0, lastPopulatedIndex + 1);

    const monthlyTotal = barValues.reduce((sum, value) => sum + value, 0);
    const formatAmount = (value) => `₹${Number(value || 0).toLocaleString('en-IN')}`;

    function getNiceStep(value) {
      if (!value || value <= 0) return 1;
      const raw = value / 10;
      const exponent = Math.floor(Math.log10(raw));
      const base = Math.pow(10, exponent);
      const normalized = raw / base;
      let nice = 1;
      if (normalized <= 1) nice = 1;
      else if (normalized <= 2) nice = 2;
      else if (normalized <= 5) nice = 5;
      else nice = 10;
      return nice * base;
    }

    const stepSize = getNiceStep(monthlyTotal);
    const maxValue = barValues.length ? Math.max(...barValues) : 0;
    const suggestedMax = stepSize ? Math.ceil(maxValue / stepSize) * stepSize : undefined;

    barChartInstance = new Chart(barCanvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: barLabels,
        datasets: [{
          label: 'Amount Spent (₹)',
          data: barValues,
          backgroundColor: 'rgba(13, 110, 253, 0.85)',
          hoverBackgroundColor: '#0d6efd',
          borderRadius: 8,
          borderSkipped: false,
          maxBarThickness: 56,
          barPercentage: 0.55,
          categoryPercentage: 0.6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 450, easing: 'easeOutQuart' },
        plugins: {
          legend: { display: false },
          title: { display: false },
          subtitle: { display: false },
          tooltip: {
            backgroundColor: getThemeColor('--chart-tooltip-bg'),
            titleColor: getThemeColor('--chart-tooltip-text'),
            bodyColor: getThemeColor('--chart-tooltip-text'),
            borderColor: getThemeColor('--chart-grid'),
            borderWidth: 1,
            cornerRadius: 10,
            displayColors: false,
            padding: 10,
            callbacks: {
              label: (context) => formatAmount(context.parsed.y)
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            suggestedMax: suggestedMax,
            grid: {
              color: getThemeColor('--chart-grid'),
              drawTicks: false
            },
            border: { display: false },
            ticks: {
              stepSize: stepSize,
              color: getThemeColor('--chart-axis'),
              font: { size: 11 },
              padding: 8,
              callback: (value) => formatAmount(value)
            },
            title: { display: false }
          },
          x: {
            grid: { display: false },
            border: { display: false },
            ticks: {
              color: getThemeColor('--chart-axis'),
              font: { size: 11 }
            },
            title: { display: false }
          }
        }
      }
    });
  }

  const exploreSection = document.getElementById('explore-your-spending');
  const searchForm = document.getElementById('spend-search-form');
  const searchInput = document.getElementById('spend-search-input');

  function submitExploreSearch(value) {
    if (!searchForm || !searchInput) return;

    const currentUrl = new URL(window.location.href);
    const targetUrl = new URL(searchForm.getAttribute('action') || currentUrl.pathname, currentUrl.origin);

    targetUrl.search = currentUrl.search;

    if (value && value.trim()) {
      targetUrl.searchParams.set('q', value.trim());
    } else {
      targetUrl.searchParams.delete('q');
    }

    targetUrl.hash = 'explore-your-spending';
    window.location.href = targetUrl.toString();
  }

  if (searchForm && searchInput) {
    searchForm.addEventListener('submit', function (event) {
      event.preventDefault();
      submitExploreSearch(searchInput.value);
    });

    document.querySelectorAll('.dashboard-chip').forEach(function (chip) {
      chip.addEventListener('click', function (event) {
        event.preventDefault();
        searchInput.value = this.getAttribute('data-chip') || '';
        searchForm.requestSubmit();
      });
    });

    const clearLink = searchForm.querySelector('a.btn-outline-secondary');
    if (clearLink) {
      clearLink.addEventListener('click', function (event) {
        event.preventDefault();
        searchInput.value = '';
        submitExploreSearch('');
      });
    }
  }

  if (exploreSection && window.location.hash === '#explore-your-spending') {
    exploreSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

});

// Re-color both charts live when the theme toggle fires, since the toggle
// button and these charts live on the same page - a page reload shouldn't
// be required to see them match.
document.addEventListener('theme-changed', function () {
  if (pieChartInstance) {
    pieChartInstance.data.datasets[0].borderColor = getThemeColor('--surface');
    pieChartInstance.options.plugins.tooltip.backgroundColor = getThemeColor('--chart-tooltip-bg');
    pieChartInstance.options.plugins.tooltip.titleColor = getThemeColor('--chart-tooltip-text');
    pieChartInstance.options.plugins.tooltip.bodyColor = getThemeColor('--chart-tooltip-text');
    pieChartInstance.options.plugins.tooltip.borderColor = getThemeColor('--chart-grid');
    pieChartInstance.update();
  }
  if (barChartInstance) {
    barChartInstance.options.plugins.tooltip.backgroundColor = getThemeColor('--chart-tooltip-bg');
    barChartInstance.options.plugins.tooltip.titleColor = getThemeColor('--chart-tooltip-text');
    barChartInstance.options.plugins.tooltip.bodyColor = getThemeColor('--chart-tooltip-text');
    barChartInstance.options.plugins.tooltip.borderColor = getThemeColor('--chart-grid');
    barChartInstance.options.scales.y.grid.color = getThemeColor('--chart-grid');
    barChartInstance.options.scales.y.ticks.color = getThemeColor('--chart-axis');
    barChartInstance.options.scales.x.ticks.color = getThemeColor('--chart-axis');
    barChartInstance.update();
  }
});
