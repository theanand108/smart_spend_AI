// Dashboard chart initialization
const chartCanvas = document.getElementById('myPieChart');
const ctx = chartCanvas.getContext('2d');
const labels = JSON.parse(chartCanvas.dataset.labels);
const values = JSON.parse(chartCanvas.dataset.values);



// Print to console
// console.log("Labels:", labels);
// console.log("Values:", values);

// Loop through both arrays
// labels.forEach((label, index) => {
    //     console.log(`${label}: ${values[index]}`);
    // });
    
const expense = document.querySelector(".expense");
window.addEventListener("DOMContentLoaded", ()=>{
    labels.forEach((label, index) => {
        const elm = document.createElement("p");
        elm.textContent = `${label} : ₹${values[index]}`
        elm.style.fontWeight = "bold";
        elm.style.fontSize = "18px"; 
        elm.style.display = "block";
        elm.style.marginBottom = "0.3rem"
        expense.appendChild(elm);
    })
})


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



// let p1 = document.createElement("p");
// p1.textContent = "FOOD : 444"
// expense.appendChild(p1);
