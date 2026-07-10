// Dashboard chart initialization
const chartCanvas = document.getElementById('myPieChart');
const ctx = chartCanvas.getContext('2d');

const labels = JSON.parse(chartCanvas.dataset.labels);
const values = JSON.parse(chartCanvas.dataset.values);



// ======== Month Logic ======== 
const months = Array.from({ length: 12 }, (_, i) => {
  return new Intl.DateTimeFormat('en', { month: 'long' }).format(new Date(2000, i));
});


const monthDropdown = document.getElementById("monthDropdown");

window.addEventListener("DOMContentLoaded", ()=>{
    months.forEach(month =>{
        const option = document.createElement("option")
        option.text = month
        monthDropdown.appendChild(option);
    })
    monthDropdown.value = months[curr_month-1];
    
})
function navigateToMonth(selectedMonth) {
    if (!selectedMonth) return;

    // Directs the browser to /dashboard/january, /dashboard/february, etc.
    selectedMonth = months.indexOf(selectedMonth) + 1; // Convert month name to month number (1-12)
    window.location.href = `/dashboard/${selectedMonth}`;
}

// console.log(month_spending)
// console.log(prev_month_Transaction_amount)


    
const expense = document.querySelector(".expense");
window.addEventListener("DOMContentLoaded", ()=>{
    labels.forEach((label, index) => {
        const elm = document.createElement("p");
        elm.textContent = `${label} : ₹${values[index]}`
        elm.style.fontWeight = "bold";
        elm.style.fontSize = "18px"; 
        elm.style.display = "block";
        elm.style.marginBottom = "0.3rem"
        if(label === "Food & Dining"){
            elm.style.color = "rgb(255, 99, 132)";
        }
        else if(label === "Shopping"){
            elm.style.color = "rgb(54, 162, 235)";
        }else if(label === "Health & Fitness"){
            elm.style.color = "rgb(255, 206, 86)";
        }else if(label === "Bills & Utilities"){
            elm.style.color = "rgb(75, 192, 192)";
        }else if(label === "Groceries"){
            elm.style.color = "rgb(153, 102, 255)";
        }
        else{
            elm.style.color === "rgb(153, 102, 255)";
        }
        expense.appendChild(elm);
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
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: pieLabels,
                datasets: [{
                    label: 'Total Spent (₹)',
                    data: pieValues,
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(255, 206, 86, 0.7)',
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(153, 102, 255, 0.7)'
                    ],
                    borderColor: '#ffffff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top' },
                    title: { display: true, text: 'Spending Distribution' }
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
    const barLabels = JSON.parse(barCanvas.dataset.labels || "[]");
    const barValues = JSON.parse(barCanvas.dataset.values || "[]");
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

    new Chart(barCanvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: barLabels,
        datasets: [{
          label: 'Amount Spent (₹)',
          data: barValues,
          backgroundColor: 'rgba(54, 162, 235, 0.7)',
          borderColor: 'rgb(54, 162, 235)',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          title: { display: true, text: 'Weekly Spending Trend' },
          subtitle: { display: true, text: 'Current Month' },
          tooltip: {
            callbacks: {
              label: (context) => `Total spending: ${formatAmount(context.parsed.y)}`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            suggestedMax: suggestedMax,
            ticks: {
              stepSize: stepSize,
              callback: (value) => formatAmount(value)
            },
            title: { display: true, text: 'Amount (₹)' }
          },
          x: {
            title: { display: true, text: 'Week' }
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
