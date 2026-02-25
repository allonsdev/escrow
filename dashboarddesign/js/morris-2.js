// ========= DATA =========
const segments = [
  { key: "Completed", title: "Completed Order", pct: 60, color: "#22C55E", valueText: "3,432", deltaText: "5.6%" },
  { key: "New",       title: "New Order",       pct: 30, color: "#2377FC", valueText: "1,716", deltaText: "2.1%" },
  { key: "Pending",   title: "Pending Order",   pct: 10, color: "#8D79F6", valueText: "572",   deltaText: "0.8%" }
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

// ========= Render progress bars =========
$("#pctComplete").text(segments[0].pct + "%");
$("#pctNew").text(segments[1].pct + "%");
$("#pctPending").text(segments[2].pct + "%");

$("#barComplete").css("width", segments[0].pct + "%");
$("#barNew").css("width", segments[1].pct + "%");
$("#barPending").css("width", segments[2].pct + "%");

// ========= Morris Donut =========
let donut = null;

function renderDonut() {
  if (donut) {
    $("#morris-donut-2").empty();
    donut = null;
  }

  donut = new Morris.Donut({
    element: "morris-donut-2",
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
  const $svg = $("#morris-donut-2 svg");
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
