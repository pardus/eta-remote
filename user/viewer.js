const canvas = document.getElementById("screen");
const context = canvas.getContext("2d");
const status = document.getElementById("status");

/*
 * Original capture resolution.

 * Change these values to match the actual captured screen size.
 */
let sourceWidth = 2433;
let sourceHeight = 1080;

let scale = 1;
let offsetX = 0;
let offsetY = 0;


/*
 * Resize the canvas to fit the browser window.
 */
function resizeCanvas() {
    const devicePixelRatio = window.devicePixelRatio || 1;

    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;

    /*
     * Preserve aspect ratio and show the complete captured screen.
     */
    scale = Math.min(
        windowWidth / sourceWidth,
        windowHeight / sourceHeight
    );

    const displayedWidth = sourceWidth * scale;
    const displayedHeight = sourceHeight * scale;

    /*
     * Center the captured screen.
     */
    offsetX = (windowWidth - displayedWidth) / 2;
    offsetY = (windowHeight - displayedHeight) / 2;

    /*
     * Use a high-resolution canvas internally.
     */
    canvas.width = Math.round(windowWidth * devicePixelRatio);
    canvas.height = Math.round(windowHeight * devicePixelRatio);

    canvas.style.width = `${windowWidth}px`;
    canvas.style.height = `${windowHeight}px`;

    /*
     * Coordinates after this point use CSS pixels.
     */
    context.setTransform(
        devicePixelRatio,
        0,
        0,
        devicePixelRatio,
        0,
        0
    );

    context.fillStyle = "#111";
    context.fillRect(0, 0, windowWidth, windowHeight);
}

window.addEventListener("resize", resizeCanvas);

resizeCanvas();


/*
 * Connect to the Python WebSocket server.
 */
const websocket = new WebSocket(
    "ws://127.0.0.1:8765/room1"
);

websocket.onopen = function () {
    console.log("WebSocket connected");

    status.textContent = "Connected";

    setTimeout(function () {
        status.style.display = "none";
    }, 1500);
};

websocket.onerror = function (error) {
    console.error("WebSocket error:", error);

    status.style.display = "block";
    status.textContent = "WebSocket error";
};

websocket.onclose = function (event) {
    console.log("WebSocket closed:", event);

    status.style.display = "block";
    status.textContent = "Disconnected";
};


/*
 * Receive a patch from Python.
 */
websocket.onmessage = function (event) {
    let patch;

    try {
        patch = JSON.parse(event.data);
    } catch (error) {
        console.error("Invalid JSON:", event.data);
        return;
    }

    console.log("Received patch:", patch);

    /*
     * If the server includes the source resolution,
     * use it automatically.
     */
    if (patch.screen_width && patch.screen_height) {
        sourceWidth = Number(patch.screen_width);
        sourceHeight = Number(patch.screen_height);

        resizeCanvas();
    }

    drawPatch(patch);
};


/*
 * Draw one received image patch.
 */
function drawPatch(patch) {
    if (!patch.pixels) {
        console.error("No pixels field found:", patch);
        return;
    }

    const x = Number(patch.x);
    const y = Number(patch.y);
    const width = Number(patch.width);
    const height = Number(patch.height);

    if (
        !Number.isFinite(x) ||
        !Number.isFinite(y) ||
        !Number.isFinite(width) ||
        !Number.isFinite(height)
    ) {
        console.error("Invalid patch dimensions:", patch);
        return;
    }

    const image = new Image();

    image.onload = function () {
        /*
         * Convert original capture coordinates to
         * displayed browser coordinates.
         */
        const drawX = offsetX + x * scale;
        const drawY = offsetY + y * scale;
        const drawWidth = width * scale;
        const drawHeight = height * scale;

        context.drawImage(
            image,
            drawX,
            drawY,
            drawWidth,
            drawHeight
        );
    };

    image.onerror = function () {
        console.error("Could not decode image patch");
    };

    let format = String(patch.format || "jpeg").toLowerCase();

    if (format === "jpg") {
        format = "jpeg";
    }

    /*
     * Remove the prefix if pixels already contains
     * something like data:image/jpeg;base64,...
     */
    const pixels = String(patch.pixels).replace(
        /^data:image\/[^;]+;base64,/,
        ""
    );

    image.src = `data:image/${format};base64,${pixels}`;
}
