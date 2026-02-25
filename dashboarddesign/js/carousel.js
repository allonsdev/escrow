if ($(".thumbs-slider").length) {
    var direction = $(".tf-product-media-thumbs").data("direction");
    var thumbs = new Swiper(".tf-product-media-thumbs", {
        spaceBetween: 10,
        slidesPerView: "auto",
        freeMode: true,
        watchSlidesProgress: true,
        breakpoints: {
            0: {
                direction: "horizontal",
            },
            1441: {
                direction: direction,
            }
        },
    });
    var main = new Swiper(".tf-product-media-main", {
        spaceBetween: 10,
        thumbs: {
            swiper: thumbs,
        },
    });
}
