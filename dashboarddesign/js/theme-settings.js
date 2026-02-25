; (function ($) {

    "use strict";
                
    var tflight =$('#logo_header').data('light');
    var tfdark =$('#logo_header').data('dark');

    // setting theme style
    // ---------------------------------

    // dark_light
    var dark_light = function () {
        var toggle = $(".button-dark-light");

        // setting dark is default
        // if (localStorage.toggled === 'dark-theme' || localStorage.toggled === 'light-theme' ) {
        // } else {
        //     localStorage.toggled = 'dark-theme';
        // }
        // if (localStorage.toggled === 'dark-theme') {
        //     $("body").addClass("dark-theme");
        // } else {
        //     $("body").addClass("light-theme");
        // }
        // end

        toggle.on("click", function () {
            if (localStorage.toggled !== "dark-theme") {
                $("body").toggleClass("dark-theme", true);
                $("body").toggleClass("light-theme", false);
                localStorage.toggled = "dark-theme";
                $(".theme-dark-light").find(".dark").find("input").prop("checked", true);
                if (!$(".layout-wrap").is("[data-menu-background]")) {
                    $("#logo_header").attr({src:tfdark});
                    $("#logo_header_mobile").attr({src:tfdark});
                }

            } else {
                $("body").toggleClass("dark-theme", false);
                $("body").toggleClass("light-theme", true);
                localStorage.toggled = "light-theme";   
                $(".theme-dark-light").find(".light").find("input").prop("checked", true);
                if (!$(".layout-wrap").is("[data-menu-background]")) {
                    $("#logo_header").attr({src:tflight});
                    $("#logo_header_mobile").attr({src:tflight});
                }
            }
        });
        if ($("body").hasClass("dark-theme")) {
            $(".theme-dark-light").find(".dark").find("input").prop("checked", true);
            $("#logo_header").attr({src:tfdark});
            $("#logo_header_mobile").attr({src:tfdark});
        }
        if (!$("body").hasClass("dark-theme")) {
            $(".theme-dark-light").find(".light").find("input").prop("checked", true);
            $("#logo_header").attr({src:tflight});
            $("#logo_header_mobile").attr({src:tflight});
        }
    }

    // menu style
    var menu_style = function () {

        if (localStorage.menu_style === "menu-style-icon-default") {
            $(".layout-wrap").addClass("menu-style-icon-default");
        } else {
            if (localStorage.menu_style === "menu-style-icon") {
                $(".layout-wrap").addClass("menu-style-icon-default");
            } else {
                $(".layout-wrap").removeClass("menu-style-icon");
                $(".layout-wrap").removeClass("menu-style-icon-default");
            }
        }

        $(".menu-style .icon-hover").on("click", function () {
            $(".layout-wrap").addClass("menu-style-icon");
            $(".layout-wrap").removeClass("menu-style-icon-default");
            localStorage.menu_style = "menu-style-icon";
        })
        if ($(".layout-wrap").hasClass("menu-style-icon")) {
            $(".menu-style").find(".icon-hover").prop("checked", true);
        }
        $(".menu-style .icon-default").on("click", function () {
            $(".layout-wrap").addClass("menu-style-icon-default");
            $(".layout-wrap").removeClass("menu-style-icon");
            localStorage.menu_style = "menu-style-icon-default";
        })
        if ($(".layout-wrap").hasClass("menu-style-icon-default")) {
            $(".menu-style").find(".icon-default").prop("checked", true);
        }
        $(".menu-style .menu-click").on("click", function () {
            $(".layout-wrap").removeClass("menu-style-icon");
            $(".layout-wrap").removeClass("menu-style-icon-default");
            localStorage.menu_style = "";
        })
        if (!$(".layout-wrap").hasClass("menu-style-icon") && !$(".layout-wrap").hasClass("menu-style-icon-default") ) {
            $(".menu-style").find(".menu-click").prop("checked", true);
        }
    }

    // layout width style
    var layout_width = function () {

        if (localStorage.layout_width === "boxed") {
            $(".layout-wrap").addClass("layout-width-boxed");
        } else {
            $(".layout-wrap").removeClass("layout-width-boxed");
        }

        $(".layout-width .boxed").on("click", function () {
            $(".layout-wrap").addClass("layout-width-boxed");
            localStorage.layout_width = "boxed";
        })
        if ($(".layout-wrap").hasClass("layout-width-boxed")) {
            $(".layout-width").find(".boxed").prop("checked", true);
        }
        $(".layout-width .full").on("click", function () {
            $(".layout-wrap").removeClass("layout-width-boxed");
            localStorage.layout_width = "";
        })
        if (!$(".layout-wrap").hasClass("layout-width-boxed")) {
            $(".layout-width").find(".full").prop("checked", true);
        }
    }

    // menu position style
    var menu_position = function () {

        if (localStorage.menu_position === "scrollable") {
            $(".layout-wrap").addClass("menu-position-scrollable");
        } else {
            $(".layout-wrap").removeClass("menu-position-scrollable");
        }

        $(".menu-position .menu-fixed").on("click", function () {
            $(".layout-wrap").removeClass("menu-position-scrollable");
            localStorage.menu_position = "";
        })
        if (!$(".layout-wrap").hasClass("menu-position-scrollable")) {
            $(".menu-position").find(".menu-fixed").prop("checked", true);
        }
        $(".menu-position .menu-scrollable").on("click", function () {
            $(".layout-wrap").addClass("menu-position-scrollable");
            localStorage.menu_position = "scrollable";
        })
        if ($(".layout-wrap").hasClass("menu-position-scrollable")) {
            $(".menu-position").find(".menu-scrollable").prop("checked", true);
        }
    }

    // header position style
    var header_position = function () {

        if (localStorage.header_position === "scrollable") {
            $(".layout-wrap").addClass("header-position-scrollable");
        } else {
            $(".layout-wrap").removeClass("header-position-scrollable");
        }

        $(".header-position .header-fixed").on("click", function () {
            $(".layout-wrap").removeClass("header-position-scrollable");
            localStorage.header_position = "";
        })
        if (!$(".layout-wrap").hasClass("header-position-scrollable")) {
            $(".header-position").find(".header-fixed").prop("checked", true);
        }
        $(".header-position .header-scrollable").on("click", function () {
            $(".layout-wrap").addClass("header-position-scrollable");
            localStorage.header_position = "scrollable";
        })
        if ($(".layout-wrap").hasClass("header-position-scrollable")) {
            $(".header-position").find(".header-scrollable").prop("checked", true);
        }
    }

    // clear-all
    var clear_style = function () {
        $(".form-theme-style .button-clear-select").on("click", function () {
            $("body").removeClass("dark-theme");
            $(".theme-dark-light").find(".light").find("input").prop("checked", true);
            localStorage.toggled = "light-theme";   
            localStorage.menu_style = "";   
            localStorage.layout_width = "";   
            localStorage.menu_position = "";   
            localStorage.header_position = "";   
            $(".layout-wrap").removeClass("menu-style-icon");
            $(".layout-wrap").removeClass("menu-style-icon-default");
            $(".menu-style").find(".menu-click").prop("checked", true);
            $(".layout-wrap").removeClass("layout-width-boxed");
            $(".layout-width").find(".full").prop("checked", true);
            $(".layout-wrap").removeClass("menu-position-scrollable");
            $(".menu-position").find(".menu-fixed").prop("checked", true);
            $(".layout-wrap").removeClass("header-position-scrollable");
            $(".header-position").find(".header-fixed").prop("checked", true);
            $("#logo_header").attr({src:tflight});
            $("#logo_header_mobile").attr({src:tflight});
        })
    }

    // setting theme color
    // ---------------------------------

    // colors-menu
    var colors_menu = function () {

        if (localStorage.colors_menu === "fff") {
            $(".layout-wrap").attr("data-menu-background", "colors-menu-fff");
            $("#logo_header").attr({src:tflight});
        } else {
            if (localStorage.colors_menu === "1E293B") {
                $(".layout-wrap").attr("data-menu-background", "colors-menu-1E293B");
                $("#logo_header").attr({src:tfdark});
            } else {
                if (localStorage.colors_menu === "1B1B1C") {
                    $(".layout-wrap").attr("data-menu-background", "colors-menu-1B1B1C");
                    $("#logo_header").attr({src:tflight});
                } else {
                    if (localStorage.colors_menu === "3A3043") {
                        $(".layout-wrap").attr("data-menu-background", "colors-menu-3A3043");
                        $("#logo_header").attr({src:tflight});
                    }
                }
            }
        }

        $(".colors-menu .color-fff").on("click", function () {
            $(".layout-wrap").attr("data-menu-background", "colors-menu-fff");
            $("#logo_header").attr({src:tflight});
            localStorage.colors_menu = "fff";   
        })
        $(".colors-menu .color-1E293B").on("click", function () {
            $(".layout-wrap").attr("data-menu-background", "colors-menu-1E293B");
            $("#logo_header").attr({src:tfdark});
            localStorage.colors_menu = "1E293B";   
        })
        $(".colors-menu .color-1B1B1C").on("click", function () {
            $(".layout-wrap").attr("data-menu-background", "colors-menu-1B1B1C");
            $("#logo_header").attr({src:tfdark});
            localStorage.colors_menu = "1B1B1C";   
        })
        $(".colors-menu .color-3A3043").on("click", function () {
            $(".layout-wrap").attr("data-menu-background", "colors-menu-3A3043");
            $("#logo_header").attr({src:tfdark});
            localStorage.colors_menu = "3A3043";   
        })
    }

    // colors-header
    var colors_header = function () {

        if (localStorage.colors_header === "fff") {
            $(".layout-wrap").attr("data-colors-header", "colors-header-fff");
        } else {
            if (localStorage.colors_header === "1E293B") {
                $(".layout-wrap").attr("data-colors-header", "colors-header-1E293B");
            } else {
                if (localStorage.colors_header === "1B1B1C") {
                    $(".layout-wrap").attr("data-colors-header", "colors-header-1B1B1C");
                } else {
                    if (localStorage.colors_header === "3A3043") {
                        $(".layout-wrap").attr("data-colors-header", "colors-header-3A3043");
                    }
                }
            }
        }

        $(".colors-header .color-fff").on("click", function () {
            $(".layout-wrap").attr("data-colors-header", "colors-header-fff");
            localStorage.colors_header = "fff";   
        })
        $(".colors-header .color-1E293B").on("click", function () {
            $(".layout-wrap").attr("data-colors-header", "colors-header-1E293B");
            localStorage.colors_header = "1E293B";   
        })
        $(".colors-header .color-1B1B1C").on("click", function () {
            $(".layout-wrap").attr("data-colors-header", "colors-header-1B1B1C");
            localStorage.colors_header = "1B1B1C";   
        })
        $(".colors-header .color-3A3043").on("click", function () {
            $(".layout-wrap").attr("data-colors-header", "colors-header-3A3043");
            localStorage.colors_header = "3A3043";   
        })
    }

    // theme-primary
    var primary_theme = function () {

        if (localStorage.primary_theme === "2377FC") {
            $(".layout-wrap").attr("data-theme-primary", "theme-primary-2377FC");
        } else {
            if (localStorage.primary_theme === "FF7433") {
                $(".layout-wrap").attr("data-theme-primary", "theme-primary-FF7433");
            } else {
                if (localStorage.primary_theme === "35988D") {
                    $(".layout-wrap").attr("data-theme-primary", "theme-primary-35988D");
                } else {
                    if (localStorage.primary_theme === "7047D6") {
                        $(".layout-wrap").attr("data-theme-primary", "theme-primary-7047D6");
                    } else {
                        if (localStorage.primary_theme === "189D72") {
                            $(".layout-wrap").attr("data-theme-primary", "theme-primary-189D72");
                        }
                    }
                }
            }
        }

        $(".colors-theme-primary .color-2377FC").on("click", function () {
            $(".layout-wrap").attr("data-theme-primary", "theme-primary-2377FC");
            localStorage.primary_theme = "2377FC";   
        })
        $(".colors-theme-primary .color-FF7433").on("click", function () {
            $(".layout-wrap").attr("data-theme-primary", "theme-primary-FF7433");
            localStorage.primary_theme = "FF7433";   
        })
        $(".colors-theme-primary .color-35988D").on("click", function () {
            $(".layout-wrap").attr("data-theme-primary", "theme-primary-35988D");
            localStorage.primary_theme = "35988D";   
        })
        $(".colors-theme-primary .color-7047D6").on("click", function () {
            $(".layout-wrap").attr("data-theme-primary", "theme-primary-7047D6");
            localStorage.primary_theme = "7047D6";   
        })
        $(".colors-theme-primary .color-189D72").on("click", function () {
            $(".layout-wrap").attr("data-theme-primary", "theme-primary-189D72");
            localStorage.primary_theme = "189D72";   
        })
    }

    // theme-background
    var theme_background = function () {

        if (localStorage.theme_background === "F6F6F6") {
            $("body").attr("data-theme-background", "theme-background-F6F6F6");
        } else {
            if (localStorage.theme_background === "252E3A") {
                $("body").attr("data-theme-background", "theme-background-252E3A");
            } else {
                if (localStorage.theme_background === "1E1D2A") {
                    $("body").attr("data-theme-background", "theme-background-1E1D2A");
                } else {
                    if (localStorage.theme_background === "1B2627") {
                        $("body").attr("data-theme-background", "theme-background-1B2627");
                    } else {
                        if (localStorage.theme_background === "1F2027") {
                            $("body").attr("data-theme-background", "theme-background-1F2027");
                        }
                    }
                }
            }
        }

        $(".colors-theme-background .color-F6F6F6").on("click", function () {
            $("body").attr("data-theme-background", "theme-background-F6F6F6");
               localStorage.theme_background = "F6F6F6";   
        })
        $(".colors-theme-background .color-252E3A").on("click", function () {
            $("body").attr("data-theme-background", "theme-background-252E3A");
               localStorage.theme_background = "252E3A";   
        })
        $(".colors-theme-background .color-1E1D2A").on("click", function () {
            $("body").attr("data-theme-background", "theme-background-1E1D2A");
               localStorage.theme_background = "1E1D2A";   
        })
        $(".colors-theme-background .color-1B2627").on("click", function () {
            $("body").attr("data-theme-background", "theme-background-1B2627");
               localStorage.theme_background = "1B2627";   
        })
        $(".colors-theme-background .color-1F2027").on("click", function () {
            $("body").attr("data-theme-background", "theme-background-1F2027");
               localStorage.theme_background = "1F2027";   
        })
    }

    // clear-all
    var clear_color = function ()  {
        $(".form-theme-color .button-clear-select").on("click", function () {
            $(".layout-wrap").removeAttr("data-colors-header");
            $(".layout-wrap").removeAttr("data-menu-background");
            $(".layout-wrap").removeAttr("data-theme-primary");
            $("body").removeAttr("data-theme-background");
            $(".select-colors-theme").find(".active").removeClass("active");
            $(".select-colors-theme").find(".default").addClass("active");
            if ($("body").hasClass("dark-theme")) {
                $("#logo_header").attr({src:tfdark});
            } else {
                $("#logo_header").attr({src:tflight});
            }
            localStorage.colors_menu = "fff";
            localStorage.colors_header = "fff";
            localStorage.primary_theme = "FF7433";
            localStorage.theme_background = "F6F6F6";
        })
    }

    // Dom Ready
    $(function () {
        dark_light();
        menu_style();
        layout_width();
        menu_position();
        header_position();
        clear_style();
        colors_menu();
        colors_header();
        primary_theme();
        theme_background();
        clear_color();
    });

})(jQuery);

