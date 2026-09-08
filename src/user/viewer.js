const canvas = document.getElementById("screen");
const context = canvas.getContext("2d");

let sourceWidth = 800;
let sourceHeight = 600;

let scale = 1.0;
let offsetX = 0;
let offsetY = 0;

let pendingPatches = null;
let busy = false;

function resizeCanvas() {
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;

    scale = Math.min(
        windowWidth / sourceWidth,
        windowHeight / sourceHeight
    );

    const displayedWidth = sourceWidth * scale;
    const displayedHeight = sourceHeight * scale;

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

        pendingPatches = patch;
        processNext();
    };
});

function patchSrc(patch) {
    let format = String(patch.format || "jpeg").toLowerCase();
    if (format === "jpg") {
        format = "jpeg";
    }
    const pixels = String(patch.pixels).replace(
        /^data:image\/[^;]+;base64,/,
        ""
    );
    return `data:image/${format};base64,${pixels}`;
}

async function decodePatch(patch) {
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
        throw new Error("Invalid patch dimensions");
    }

    let bitmap;
    if (typeof createImageBitmap === "function") {
        const response = await fetch(patchSrc(patch));
        bitmap = await createImageBitmap(await response.blob());
    } else {
        bitmap = await new Promise((resolve, reject) => {
            const image = new Image();
            image.onload = () => resolve(image);
            image.onerror = () => reject(new Error("Could not decode image patch"));
            image.src = patchSrc(patch);
        });
    }

    return {
        bitmap,
        drawX: x * scale,
        drawY: y * scale,
        drawWidth: width * scale,
        drawHeight: height * scale
    };
}

async function processNext() {
    if (busy) {
        return;
    }

    busy = true;

    const patch = pendingPatches;
    pendingPatches = null;

    if (!patch) {
        busy = false;
        return;
    }

    try {
        const item = await decodePatch(patch);

        if (pendingPatches) {
            if (item.bitmap.close) {
                item.bitmap.close();
            }
        } else {
            context.drawImage(
                item.bitmap,
                item.drawX,
                item.drawY,
                item.drawWidth,
                item.drawHeight
            );
            if (item.bitmap.close) {
                item.bitmap.close();
            }
        }
    } catch (error) {
        console.error("Patch draw error:", error.message);
    }

    busy = false;

    processNext();
}

function drawPatch(patch) {
    pendingPatches = patch;
    processNext();
}
