document.addEventListener("DOMContentLoaded", () => {
    const icon = document.querySelector(".context-icon");
    const menu = document.querySelector(".context-menu");
    const contextArea = document.querySelector("#context-container")
    // Show context menu at click position
    function showMenu(x, y) {
        console.log("Showing menu")
        // Make visible to get dimensions
        menu.style.display = "flex";
        menu.style.position = "fixed";
        menu.style.opacity = "0";
        menu.classList.add("show");

        // Wait one frame so DOM updates before measuring
        requestAnimationFrame(() => {
            const rect = menu.getBoundingClientRect();
            let newX = x + 5;
            let newY = y + 5;

            // Keep inside viewport
            if (newX + rect.width > window.innerWidth) {
                newX = window.innerWidth - rect.width - 10;
            }
            if (newY + rect.height > window.innerHeight) {
                newY = window.innerHeight - rect.height - 10;
            }

            menu.style.left = `${newX}px`;
            menu.style.top = `${newY}px`;
            menu.style.opacity = "1";
        });
    }

    try {
        // Left-click on gear icon
        icon.addEventListener("click", (event) => {
            event.stopPropagation();
            loadMenuContent();
            const isVisible = menu.classList.contains("show");
            const context_menu_items = document.querySelectorAll(".context-menu.show");
            for (let item of context_menu_items) {
                item.classList.remove("show");
            }

            if (!isVisible) showMenu(event.clientX, event.clientY);
        });
    } catch {
        console.log("Could Not find icon to set context")
    }
    // Right-click anywhere
    try {
        contextArea.addEventListener("contextmenu", (event) => {
            const th = event.target.closest("th");
            const tr = event.target.closest("tr");

            if (!th && tr) { //only allow right click menu on folder items
                event.preventDefault();
                loadMenuContent(tr);
                showMenu(event.clientX, event.clientY);
            }
        });
    } catch {
        console.log("Could not find context area to set")
    }
    // long touch anywhere
    try {
        let longPressTimer;

        contextArea.addEventListener("touchstart", (event) => {
            const touch = event.touches[0];

            longPressTimer = setTimeout(() => {
                const th = touch.target.closest("th");
                const tr = touch.target.closest("tr");

                if (!th && tr) {
                    loadMenuContent(tr);
                    showMenu(touch.clientX, touch.clientY);
                }
            }, 500);
        });

        contextArea.addEventListener("touchend", () => {
            clearTimeout(longPressTimer);
        });

        contextArea.addEventListener("touchmove", () => {
            clearTimeout(longPressTimer);
        });

        contextArea.addEventListener("touchcancel", () => {
            clearTimeout(longPressTimer);
        });
    } catch {
        console.log("Could not find context area to set")
    }
    // Right-click anywhere
    try {
        document.addEventListener("click", (event) => {
            const ellipse = event.target.closest(".options");
            if (!ellipse) return;
            event.stopPropagation();

            const tr = ellipse.closest("tr");
            loadMenuContent(tr);
            showMenu(event.clientX, event.clientY);
        });
    } catch {
        console.log("Could not find context area to set")
    }

    // Click outside closes menu
    document.addEventListener("click", (event) => {
        if (!event.target.classList.contains("edit-configure") && !event.target.classList.contains("options")) {
            menu.classList.remove("show");
            menu.style.display = "none";
        }
    });
});
