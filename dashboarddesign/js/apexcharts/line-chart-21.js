(function ($) {
  
  var tfLineChart = (function () {

    var chartBar = function () {
    
      var options = {
          series: [{
          name: 'Revenue',
          type: 'area',
          data: [51, 40, 58, 51, 42, 89, 80, 51, 60, 78, 81, 92]
        }, {
          name: 'Store',
          type: 'line',
          data: [131, 132, 145, 132, 134, 152, 101, 81, 50, 38, 51, 42]
        }],
        chart: {
          height: 362,
          type: 'area',
          stacked: false,
          toolbar: {
            show: false,
          },
          animations: {
            enabled: true,
            easing: 'easeinout',
            speed: 10,
            animateGradually: {
                enabled: true,
                delay: 10
            },
            dynamicAnimation: {
                enabled: true,
                speed: 10
            }
          }
        },
        dataLabels: {
          enabled: false
        },
        legend: {
          show: false,
        },
        stroke: {
          width: [3, 3],
          curve: 'smooth',
          colors: ['#FF7433', '#8D79F6']
        },
        colors: ['#FF7433', '#8D79F6'],
        fill: {
          colors: ['#FF7433'],
          opacity: 0.39
        },
        yaxis: {
          show: false,
        },
        xaxis: {
          labels: {
            style: {
              colors: '#95989D',
            },
          },
          tooltip: {
            enabled: false
          },
          categories: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        },
        };

      chart = new ApexCharts(
        document.querySelector("#line-chart-21"),
        options
      );
      if ($("#line-chart-21").length > 0) {
        chart.render();
      }
    };

    /* Function ============ */
    return {

      load: function () {
        chartBar();
      },
    };
  })();

  jQuery(window).on("load", function () {
    tfLineChart.load();
  });

})(jQuery);