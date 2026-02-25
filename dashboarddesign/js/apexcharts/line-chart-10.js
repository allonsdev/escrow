(function ($) {

  var tfLineChart = (function () {

    var chart = null;

    function applyPillRadius(selector, radius){
      const root = document.querySelector(selector);
      if(!root) return;

      // ApexCharts vẽ bar bằng rect trong svg
      const rects = root.querySelectorAll("svg .apexcharts-bar-series rect");
      rects.forEach(r => {
        // bo tròn 2 đầu theo chiều ngang
        r.setAttribute("rx", radius);
        r.setAttribute("ry", radius);
      });
    }

    function chartBar() {
      var dataTop = [44, 55, 41, 67, 22, 43, 21];      // cam (dưới)
      var dataBottom = [13, 23, 20, 8, 13, 27, 33];    // xám (trên)
      var GAP = 6;                                      // khoảng hở giữa 2 đoạn

      function normalizeWithGap(topArr, bottomArr, gap) {
        var outTop = [], outGap = [], outBottom = [];
        for (var i = 0; i < topArr.length; i++) {
          var t = Number(topArr[i]) || 0;
          var b = Number(bottomArr[i]) || 0;
          var sum = t + b;

          if (sum <= 0) { outTop.push(0); outGap.push(0); outBottom.push(0); continue; }

          var scale = (100 - gap) / sum;
          outTop.push(t * scale);
          outGap.push(gap);
          outBottom.push(b * scale);
        }
        return { top: outTop, gap: outGap, bottom: outBottom };
      }

      var norm = normalizeWithGap(dataTop, dataBottom, GAP);

      var options = {
        series: [
          { name: "Active", data: norm.top },
          { name: "Gap",    data: norm.gap },
          { name: "Base",   data: norm.bottom }
        ],

        chart: {
          type: "bar",
          height: 409,
          stacked: true,
          stackType: "100%",
          toolbar: { show: false },
          animations: { enabled: true },

          events: {
            mounted: function () {
              // pill radius: lấy đúng nửa chiều rộng cột (10px -> radius 999 vẫn ok nhưng set 999 hay 20 đều được)
              applyPillRadius("#line-chart-10", 999);
            },
            updated: function () {
              applyPillRadius("#line-chart-10", 999);
            }
          }
        },

        plotOptions: {
          bar: {
            columnWidth: "10px",
            // TẮT borderRadius built-in để tránh lỗi nhọn
            borderRadius: 0
          }
        },

        colors: ["#FF7433", "rgba(0,0,0,0)", "#C3C1CF"],

        xaxis: {
          categories: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
          labels: { show: true, style: { colors: "#95989D" } },
          axisTicks: { show: false },
          axisBorder: { show: false },
          tooltip: { enabled: false }
        },

        yaxis: { show: false },

        grid: {
          show: false,
          xaxis: { lines: { show: false } },
          yaxis: { lines: { show: false } }
        },

        dataLabels: { enabled: false },
        legend: { show: false },

        tooltip: {
          y: {
            formatter: function (val, opts) {
              if (opts.seriesIndex === 1) return ""; // gap
              return Math.round(val) + "%";
            }
          }
        }
      };

      // destroy + render
      if (chart) {
        chart.destroy();
        chart = null;
      }
      chart = new ApexCharts(document.querySelector("#line-chart-10"), options);
      if ($("#line-chart-10").length) chart.render();
    }

    return {
      load: function () { chartBar(); }
    };
  })();

  jQuery(window).on("load", function () {
    tfLineChart.load();
  });

})(jQuery);
