function generate3LineChart(chartLabels, line1Label, line1Data, line2Label, line2Data, line3Label, line3Data, elemID) {
    const data = {
        labels: chartLabels,
        datasets: [
            {label: line1Label,
                backgroundColor: 'rgb(240, 173, 78)',
                borderColor: 'rgb(240, 173, 78)',
                data: line1Data,
            },
            {label: line2Label,
                backgroundColor: 'rgb(91, 192, 222)',
                borderColor: 'rgb(91, 192, 222)',
                data: line2Data,
            },
            {label: line3Label,
                backgroundColor: 'rgb(92, 184, 92)',
                borderColor: 'rgb(92, 184, 92)',
                data: line3Data,
            }
        ]
    };

    const config = {
        type: 'line',
        data: data,
        options: {}
    };

    const chartImages = new Chart(
        document.getElementById(elemID),
        config
    );
}

function generateLineChart(chartLabels, chartVars, elemID) {
    var colours = [
        'rgb(240, 173, 78)',
        'rgb(91, 192, 222)',
        'rgb(92, 184, 92)',
        'rgb(235, 64, 52)',
        'rgb(214, 235, 52)',
        'rgb(52, 73, 235)',
        'rgb(128, 52, 235)',
        'rgb(235, 52, 134)',
        'rgb(235, 89, 52)',
        'rgb(53, 176, 143)',
        'rgb(46, 28, 138)',
        'rgb(123, 28, 138)',
        'rgb(138, 28, 28)'
    ]

    var datasets = []
    var count = 0

    for (const mod in chartVars) {
        const dataset = {
            label: mod,
            backgroundColor: colours[count],
            borderColor: colours[count],
            data: chartVars[mod]
        }

        datasets.push(dataset)
        count += 1
    }

    const data = {
        labels: chartLabels,
        datasets: datasets
    }

    const config = {
        type: 'line',
        data: data,
        options: {}
    };

    const chartImages = new Chart(
        document.getElementById(elemID),
        config
    );
}