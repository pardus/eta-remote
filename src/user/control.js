"use strict";

function initFloatingControls() {
    const toggleBtn = document.getElementById("fc-toggle");
    const menu = document.getElementById("fc-menu");
    const controls = document.getElementById("floating-controls");

    if (!toggleBtn || !menu) return;

    // Make the control button draggable.
    let dragging = false;
    let moved = false;
    let startX, startY;

    function getPosition() {
        const style = window.getComputedStyle(controls);
        return {
            left: parseFloat(style.left) || null,
            top: parseFloat(style.top) || null
        };
    }

    function setPosition(x, y) {
        controls.style.left = `${x}px`;
        controls.style.top = `${y}px`;
        controls.style.right = "auto";
        controls.style.bottom = "auto";
    }

    function startDrag(e) {
        dragging = true;
        moved = false;
        toggleBtn.classList.add("dragging");

        let left = null, top = null;
        const p = getPosition();
        if (p.left === null || p.top === null) {
            const rect = controls.getBoundingClientRect();
            left = rect.left;
            top = rect.top;
            setPosition(left, top);
        } else {
            left = p.left;
            top = p.top;
        }
        startX = (e.touches ? e.touches[0].clientX : e.clientX) - left;
        startY = (e.touches ? e.touches[0].clientY : e.clientY) - top;
    }

    function moveDrag(e) {
        if (!dragging) return;
        e.preventDefault();
        const cx = e.touches ? e.touches[0].clientX : e.clientX;
        const cy = e.touches ? e.touches[0].clientY : e.clientY;
        const dx = cx - startX;
        const dy = cy - startY;
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) moved = true;

        const maxX = window.innerWidth - controls.offsetWidth;
        const maxY = window.innerHeight - controls.offsetHeight;
        const x = Math.max(0, Math.min(maxX, dx));
        const y = Math.max(0, Math.min(maxY, dy));
        setPosition(x, y);
    }

    function endDrag() {
        if (!dragging) return;
        dragging = false;
        toggleBtn.classList.remove("dragging");
    }

    toggleBtn.addEventListener("mousedown", startDrag);
    window.addEventListener("mousemove", moveDrag);
    window.addEventListener("mouseup", endDrag);
    toggleBtn.addEventListener("touchstart", startDrag, { passive: false });
    window.addEventListener("touchmove", moveDrag, { passive: false });
    window.addEventListener("touchend", endDrag);

    toggleBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (moved) return;
        menu.classList.toggle("show");
    });

    document.addEventListener("click", (e) => {
        if (!menu.contains(e.target) && e.target !== toggleBtn) {
            menu.classList.remove("show");
        }
    });


    document.getElementById("fc-keyboard").addEventListener("click", (e) => {
        e.stopPropagation();
        if (typeof VirtualKeyboard !== "undefined") {
            VirtualKeyboard.toggle();
        }
        menu.classList.remove("show");
    });
    document.getElementById("fc-keyboard").textContent = _("Keyboard")


    document.getElementById("fc-fullscreen").addEventListener("click", (e) => {
        e.stopPropagation();
        if (document.fullscreenElement) {
            document.exitFullscreen();
        } else {
            document.documentElement.requestFullscreen();
        }
        menu.classList.remove("show");
    });
    document.getElementById("fc-fullscreen").textContent = _("Fullscreen")
    const fc_quality = document.getElementById("fc-quality");
    fc_quality.addEventListener("change", (e) => {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        send("quality", {"quality": fc_quality.value});
    });

    window.addEventListener("resize", () => {
        const p = getPosition();
        if(p.left == null || p.top == null){
            return;
        }
        const maxX = window.innerWidth - controls.offsetWidth;
        const maxY = window.innerHeight - controls.offsetHeight;
        if(p.left > maxX){
            p.left = maxX;
            setPosition(p.left, p.top);
        }
        if (p.top > maxY){
            p.top = maxY;
            setPosition(p.left, p.top);
        }
    });

    const touch_mode_button = document.createElement("button");
    touch_mode_button.id = "fc-touch-mode";
    touch_mode_button.textContent = _("Touch: Direct");
    touch_mode_button.addEventListener("click", () => {
        if (touch_mode == "touch"){
            touch_mode = "touchpad";
            touch_mode_button.textContent = _("Touch: Touchpad");
        } else if (touch_mode == "touchpad"){
            touch_mode = "touch";
            touch_mode_button.textContent = _("Touch: Direct");
        }
    });
    menu.appendChild(touch_mode_button);

}

initFloatingControls();
