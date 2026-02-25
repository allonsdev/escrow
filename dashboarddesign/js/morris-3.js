
// ========= DATA =========
const segments = [
  { key: "Organic Search", title: "Organic Search", pct: 40, color: "#FF7433", valueText: "3,432", deltaText: "5.6%" },
  { key: "Referrals ",       title: "Referrals ",       pct: 20, color: "#2377FC", valueText: "1,016", deltaText: "2.1%" },
  { key: "Social media",   title: "Social media",   pct: 20, color: "#22C55E", valueText: "172",   deltaText: "0.8%" },
  { key: "Other",   title: "Other",   pct: 20, color: "#8F77F3", valueText: "102",   deltaText: "0.6%" }
];

// base = first item
const base = { ...segments[0] };

// ========= UI refs =========
const $badge = $("#centerBadge");
const $title = $("#centerTitle");
const $value = $("#centerValue");
const $delta = $("#centerDelta");
const $deltaWrap = $("#centerDeltaWrap");

function setCenter(item){
  $badge.css("border-color", item.color);
  $title.text(item.title);
  $value.text(item.valueText);

  $delta.text(item.deltaText);
  $deltaWrap.css("color", item.color);
}

// init center
setCenter(base);

// ========= Morris Donut =========
let donut = null;

function renderDonut() {
  if (donut) {
    $("#morris-donut-3").empty();
    donut = null;
  }

  donut = new Morris.Donut({
    element: "morris-donut-3",
    data: segments.map(s => ({ label: s.key, value: s.pct })),
    colors: segments.map(s => s.color),
    formatter: y => y + "%",
    resize: false 
  });

  setTimeout(bindHover, 0);
}
renderDonut();
// ========= Hover =========
function bindHover(){
  const $svg = $("#morris-donut-3 svg");
  if(!$svg.length) return;

  let $paths = $svg.find("path.morris-donut-segment");
  if(!$paths.length){
    $paths = $svg.find("path").filter(function(){
      const fill = $(this).attr("fill");
      return fill && fill !== "none";
    });
  }

  $paths.each(function(i){
    $(this).attr("data-idx", i).css("cursor","pointer");
  });

  $svg.on("mouseenter", "path[data-idx]", function(){
    const idx = Number($(this).attr("data-idx"));
    const item = segments[idx];
    if(!item) return;
    setCenter(item);
  });

  //return base 
  // $svg.on("mouseleave", function () { setCenter(base); }); 

}

setTimeout(bindHover, 0);

let resizeTimer = null;

$(window).on("resize", function () {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(function () {
    renderDonut();       
    setCenter(base);   
  }, 200);
});
