const canvas = document.getElementById("screen");
const context = canvas.getContext("2d");

/*
 * Original capture resolution.

 * Change these values to match the actual captured screen size.
 */
let sourceWidth = 800;
let sourceHeight = 600;

let scale = 1.0;
let offsetX = 0;
let offsetY = 0;


/*
 * Resize the canvas to fit the browser window.
 */
function resizeCanvas() {
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
     * Use a high-resolution canvas internally.
     */
    canvas.width = Math.round(displayedWidth);
    canvas.height = Math.round(displayedHeight);

    canvas.style.width = `${displayedWidth}px`;
    canvas.style.height = `${displayedHeight}px`;

    capture.style.width = `${displayedWidth}px`;
    capture.style.height = `${displayedHeight}px`;


    context.fillStyle = "#111";
    context.fillRect(0, 0, windowWidth, windowHeight);
    send("request_full");
}

window.addEventListener("resize", resizeCanvas);

resizeCanvas();



window.addEventListener("load", function(){

    if(!ws){
        connect();
    }
    /*
     * Receive a patch from Python.
     */
    ws.onmessage = function (event) {
        let patch;

        try {
            patch = JSON.parse(event.data);
            if (!patch.pixels) {
                return;
            }

        } catch (error) {
            console.error("Invalid JSON:", event.data);
            return;
        }

        console.log("Patch received: ", patch.pixels.length);

        /*
         * If the server includes the source resolution,
         * use it automatically.
         */
        if (patch.screen_width && patch.screen_height) {
            const w = Number(patch.screen_width);
            const h = Number(patch.screen_height);
            if (w != sourceWidth || h != sourceHeight){
                sourceWidth = w;
                sourceHeight = h;
                resizeCanvas();
                console.log(sourceWidth, sourceHeight);
            }

        }

        drawPatch(patch);
    };
});

/*
 * Draw one received image patch.
 */
function drawPatch(patch) {

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
        const drawX = x * scale;
        const drawY = y * scale;
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
