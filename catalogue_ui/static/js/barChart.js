function generateBarChart(chartLabels, datasets, elemID, indexAxis = 'x', stacked = true) {
    var colours = palette('tol-dv', datasets.length);

    for (var i=0; i < datasets.length; i++) {
        datasets[i].backgroundColor = "#" + colours[i];
    }

    const data = {
        labels: chartLabels,
        datasets: datasets
    }

    const config = {
        type: 'bar',
        data: data,
        options: {
            indexAxis: indexAxis,
            responsive: true,
            interaction: {
                intersect: false,
            },
            scales: {
                x: {
                    stacked: stacked,
                    suggestedMax: 100,
                    title: {
                        display: true,
                        text: "% of series in modality",
                        font: {size: 14}
                    }
                },
                y: {
                    stacked: stacked,
                }
            }
        },
    };

    const chartImages = new Chart(
        document.getElementById(elemID),
        config
    );
}