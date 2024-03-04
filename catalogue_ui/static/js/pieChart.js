function generatePieChart(chartLabels, datasetValues, elemID) {
    var colours = palette('tol-dv', chartLabels.length);

    for (var i=0; i < colours.length; i++) {
        colours[i] = '#' + colours[i];
    }

    const data = {
        labels: chartLabels,
        datasets: [{
          data: datasetValues,
          backgroundColor: colours,
          hoverOffset: 4
        }]
    };

    const config = {
        type: 'pie',
        data: data,
    };

    const chartImages = new Chart(
        document.getElementById(elemID),
        config
    );
}