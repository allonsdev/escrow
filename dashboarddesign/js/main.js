/**
    * selectImages
    * menuleft
    * tabs
    * collapse_menu
    * showpass
    * select_colors_theme
    * icon_function
    * box_search
    * variant_picker
    * uploadfile
    * writeReview
    * multiselect
*/

; (function ($) {

  "use strict";

  var selectImages = function () {
    if ($(".image-select").length) {
      const selectIMG = $(".image-select");
      selectIMG.find("option").each((idx, elem) => {
        const selectOption = $(elem);
        const imgURL = selectOption.attr("data-thumbnail");
        if (imgURL) {
          selectOption.attr(
            "data-content",
            "<img src='%i'/> %s"
              .replace(/%i/, imgURL)
              .replace(/%s/, selectOption.text())
          );
        }
      });
      selectIMG.selectpicker();
    }
  };

  var menuleft = function () {
    if ($(".section-menu-left").length){
      var bt =$(".section-menu-left").find(".has-children");
      bt.on("click", function () {
        var args = { duration: 200 };
        if ($(this).hasClass("active")) {
          $(this).children(".sub-menu").slideUp(args);
          $(this).removeClass("active");
        } else {
          $(".sub-menu").slideUp(args);
          $(this).children(".sub-menu").slideDown(args);
          $(".menu-item.has-children").removeClass("active");
          $(this).addClass("active");
        }
      });
      $('.sub-menu-item').on('click', function(event){
        event.stopPropagation();
      });
    }
  };

  var tabs = function(){
    $('.widget-tabs').each(function(){
        $(this).find('.widget-content-tab').children().hide();
        $(this).find('.widget-content-tab').children(".active").show();
        $(this).find('.widget-menu-tab').find('li').on('click',function(){
            var liActive = $(this).index();
            var contentActive=$(this).siblings().removeClass('active').parents('.widget-tabs').find('.widget-content-tab').children().eq(liActive);
            contentActive.addClass('active').fadeIn("slow");
            contentActive.siblings().removeClass('active');
            $(this).addClass('active').parents('.widget-tabs').find('.widget-content-tab').children().eq(liActive).siblings().hide();
        });
    });
  };

  $('.dropdown-menu.has-content').on('click', function(event){
    event.stopPropagation();
  });
  $('.button-close-dropdown').on('click', function(){
    $(this).closest('.dropdown').find('.dropdown-toggle').removeClass('show');
    $(this).closest('.dropdown').find('.dropdown-menu').removeClass('show');
  });

  var collapse_menu = function () {
    $(".overplay-menu").on("click", function () {
      $('.layout-wrap').toggleClass('full-width');
    })
    $(".button-show-hide").on("click", function () {
      $('.layout-wrap').toggleClass('full-width');
    })
  }

  var showpass = function() {
    $(".show-pass").on("click", function () {
      $(this).toggleClass("active");
      var input = $(this).parents(".password").find(".password-input");

      if (input.attr("type") === "password") {
        input.attr("type", "text");
      } else if (input.attr("type") === "text") {
        input.attr("type", "password");
      }
    });
  }

  var select_colors_theme = function () {
    if ($(".select-colors-theme").length) {
      $(".select-colors-theme .item").on("click", function (e) {
        $(this).parents(".select-colors-theme").find(".active").removeClass("active");
        $(this).toggleClass("active");
      })
    }
  }

  var icon_function = function () {
    if ($(".list-icon-function").length) {
      $(".list-icon-function .trash").on("click", function (e) {
        e.preventDefault();
        const isOk = confirm("Are you sure you want to delete this item?");
        if (isOk) {
          $(this).parents(".item-row").remove();
        }
      });
      
    }
  }

  var box_search=function(){
        
    $(document).on('click', function (e) {
      var clickID = e.target.id; if ((clickID !== 's')) {
        $('.box-content-search').removeClass('active');
      }
    });
    $(document).on('click', function (e) {
      if (!e.target.classList.contains("a111")) {
        $('.show-search').removeClass('active');
      }
    });
        
    $('.show-search').on('click',function(event){
      event.stopPropagation();}
    );
    $('.search-form').on('click',function(event){
      event.stopPropagation();}
    );
    var input =  $('.header-dashboard').find('.form-search').find('input');
    input.on('input', function() {
      if ($(this).val().trim() !== '') {
        $('.box-content-search').addClass('active');
      } else {
        $('.box-content-search').removeClass('active');
      }
    });
   
  }

  var variant_picker = function () {
    if ($(".variant-picker-item").length) {
      $(".variant-picker-item label").on("click", function (e) {
        $(this)
          .closest(".variant-picker-item")
          .find(".variant-picker-label-value")
          .text($(this).data("value"));
      });
    }
  };

  var uploadfile = function () {
    $(document).on("change", "#myFile", function (e) {
      var file = e.target.files[0];
      if (!file) return;

      var reader = new FileReader();
      reader.onload = function (ev) {
        $("#myFile-input").attr("src", ev.target.result).addClass("has-img");
      };
      reader.readAsDataURL(file);
    });
  };


  var writeReview = function () {
    if ($(".write-cancel-review-wrap").length) {
        $(".btn-comment-review").on("click", function () {
            $(this)
                .closest(".write-cancel-review-wrap")
                .toggleClass("write-review");
        });
    }
  };

  var multiselect = function () {

    document.querySelectorAll(".multi-select").forEach(ms => {
      const selectedTagsContainer = ms.querySelector(".selected-tags");
      const dropdownList = ms.querySelector(".list-dropdown");
      const dropdownToggle = ms.querySelector(".toggle-dropdown");
    
      let selected = [];
      try {
        selected = ms.dataset.default !== undefined
          ? JSON.parse(ms.dataset.default)
          : [];

      } catch (e) {
        selected = [];
      }
    
      function renderTags() {
        selectedTagsContainer.innerHTML = "";
        selected.forEach(color => {
          const tag = document.createElement("div");
          tag.className = "tag";
          tag.innerHTML = `<span class="icon icon-x"></span>${color}`;
          tag.querySelector("span").onclick = (e) => {
            e.stopPropagation();
            selected = selected.filter(c => c !== color);
            renderTags();
          };
          selectedTagsContainer.appendChild(tag);
        });
      }
    
      dropdownToggle.onclick = () => {
        dropdownList.style.display = dropdownList.style.display === "flex" ? "none" : "flex";
      };
    
      dropdownList.querySelectorAll("div").forEach(option => {
        option.onclick = () => {
          const color = option.textContent.trim();
          if (!selected.includes(color)) {
            selected.push(color);
            renderTags();
          }
          dropdownList.style.display = "none";
        };
      });
    
      renderTags();
    });

  }

  // Dom Ready
  $(function () {
    selectImages();
    menuleft();
    tabs();
    collapse_menu();
    showpass();
    select_colors_theme();
    icon_function();
    box_search();
    variant_picker();
    uploadfile();
    writeReview();
    multiselect();
  });

})(jQuery);
