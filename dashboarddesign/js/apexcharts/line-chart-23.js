(function ($) {
  
    var tfLineChart = (function () {
  
      var chartBar = function () {
      
        var options = {
            series: [{
            name: 'Revenue',
            type: 'column',
            data: [51, 40, 58, 51, 42, 89, 80, 51, 60, 78, 81, 92]
          }],
          chart: {
            height: 357,
            type: 'line',
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
          plotOptions: {
            bar: {
              horizontal: false,
              borderRadius: 5,
              borderRadiusApplication: 'end', // 'around', 'end'
              borderRadiusWhenStacked: 'last', // 'all', 'last'
              columnWidth: '10px'
            }
          },
          dataLabels: {
            enabled: false
          },
          legend: {
            show: false,
          },
          colors: ['#FF7433'],
          stroke: {
            width: [0, 3],
            curve: 'smooth'
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
          responsive: [{
            breakpoint: 991,
            options: {
              chart: {
                height: 300
              },
            }
          }],
          yaxis: {
            show: false,
          },
          tooltip: {
            y: {
              title: {
                formatter: function (e) {
                  return e;
                },
              },
            },
          },
        };

        chart = new ApexCharts(
          document.querySelector("#line-chart-23"),
          options
        );
        if ($("#line-chart-23").length > 0) {
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