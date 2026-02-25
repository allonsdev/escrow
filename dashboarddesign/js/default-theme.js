const layoutWrap = document.querySelector(".layout-wrap");
const logoHeader = document.getElementById("logo_header");

const tflight = logoHeader?.dataset.light;
const tfdark = logoHeader?.dataset.dark;

// DARK
if (localStorage.toggled === "dark-theme") {
    document.body.classList.add('dark-theme');
  }

// MENU STYLE
if (localStorage.menu_style === "menu-style-icon-default") {
    layoutWrap.classList.add("menu-style-icon-default");
} else {
    if (localStorage.menu_style === "menu-style-icon") {
        layoutWrap.classList.add("menu-style-icon-default");
    } else {
        layoutWrap.classList.remove("menu-style-icon");
        layoutWrap.classList.remove("menu-style-icon-default");
    }
}

// LAYOUT WIDTH
if (localStorage.layout_width === "boxed") {
    layoutWrap.classList.add("layout-width-boxed");
} else {
    layoutWrap.classList.remove("layout-width-boxed");
}

// MENU POSITION
if (localStorage.menu_position === "scrollable") {
    layoutWrap.classList.add("menu-position-scrollable");
} else {
    layoutWrap.classList.remove("menu-position-scrollable");
}

// HEADER POSITION
if (localStorage.header_position === "scrollable") {
    layoutWrap.classList.add("header-position-scrollable");
} else {
    layoutWrap.classList.remove("header-position-scrollable");
}

// COLORS MENU + LOGO
if (localStorage.colors_menu === "fff") {
    layoutWrap.setAttribute("data-menu-background", "colors-menu-fff");
    logoHeader.setAttribute("src", tflight);
} else if (localStorage.colors_menu === "1E293B") {
    layoutWrap.setAttribute("data-menu-background", "colors-menu-1E293B");
    logoHeader.setAttribute("src", tfdark);
} else if (localStorage.colors_menu === "1B1B1C") {
    layoutWrap.setAttribute("data-menu-background", "colors-menu-1B1B1C");
    logoHeader.setAttribute("src", tflight);
} else if (localStorage.colors_menu === "3A3043") {
    layoutWrap.setAttribute("data-menu-background", "colors-menu-3A3043");
    logoHeader.setAttribute("src", tflight);
}

// COLORS HEADER
if (localStorage.colors_header === "fff") {
    layoutWrap.setAttribute("data-colors-header", "colors-header-fff");
} else if (localStorage.colors_header === "1E293B") {
    layoutWrap.setAttribute("data-colors-header", "colors-header-1E293B");
} else if (localStorage.colors_header === "1B1B1C") {
    layoutWrap.setAttribute("data-colors-header", "colors-header-1B1B1C");
} else if (localStorage.colors_header === "3A3043") {
    layoutWrap.setAttribute("data-colors-header", "colors-header-3A3043");
}

// PRIMARY THEME
if (localStorage.primary_theme === "2377FC") {
    layoutWrap.setAttribute("data-theme-primary", "theme-primary-2377FC");
} else if (localStorage.primary_theme === "FF7433") {
    layoutWrap.setAttribute("data-theme-primary", "theme-primary-FF7433");
} else if (localStorage.primary_theme === "35988D") {
    layoutWrap.setAttribute("data-theme-primary", "theme-primary-35988D");
} else if (localStorage.primary_theme === "7047D6") {
    layoutWrap.setAttribute("data-theme-primary", "theme-primary-7047D6");
} else if (localStorage.primary_theme === "189D72") {
    layoutWrap.setAttribute("data-theme-primary", "theme-primary-189D72");
}

// BACKGROUND THEME
if (localStorage.theme_background === "F6F6F6") {
    document.body.setAttribute(
        "data-theme-background",
        "theme-background-F6F6F6"
    );
} else if (localStorage.theme_background === "252E3A") {
    document.body.setAttribute(
        "data-theme-background",
        "theme-background-252E3A"
    );
} else if (localStorage.theme_background === "1E1D2A") {
    document.body.setAttribute(
        "data-theme-background",
        "theme-background-1E1D2A"
    );
} else if (localStorage.theme_background === "1B2627") {
    document.body.setAttribute(
        "data-theme-background",
        "theme-background-1B2627"
    );
} else if (localStorage.theme_background === "1F2027") {
    document.body.setAttribute(
        "data-theme-background",
        "theme-background-1F2027"
    );
}
