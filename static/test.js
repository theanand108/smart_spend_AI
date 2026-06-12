{/* <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script> */}
    // let message = alert("hello");
    const chartCanvas = document.getElementById('myPieChart');
    const ctx = chartCanvas.getContext('2d');
    const labels = JSON.parse(chartCanvas.dataset.labels);
    const values = JSON.parse(chartCanvas.dataset.values);
    
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                label: 'Total Spent (₹)',
                data: values,
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

    label = document.createElement("p");
    value = document.createElement("p");
    

// </script>