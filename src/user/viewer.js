const canvas = document.getElementById("screen");
const context = canvas.getContext("2d");

let sourceWidth = 800;
let sourceHeight = 600;

let scale = 1.0;
let offsetX = 0;
let offsetY = 0;

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

});


function handlePatch(message) {
    if (!perms.image) return;
    if (message.screenWidth && message.screenHeight) {
        const w = Number(message.screenWidth);
        const h = Number(message.screenHeight);
        if (w != sourceWidth || h != sourceHeight){
            sourceWidth = w;
            sourceHeight = h;
            resizeCanvas();
            console.log(sourceWidth, sourceHeight);
        }
    }

    drawPatch(message);
}

function handleImagePerms(enabled) {
    if (enabled) {
        setStatus("");
        resizeCanvas();
    } else {
        context.fillStyle = "#111";
        context.fillRect(0, 0, canvas.width, canvas.height);
        setStatus(_("Image disabled"));
    }
}

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
    const url = URL.createObjectURL(new Blob([patch.jpegData], { type: "image/jpeg" }));

    image.onload = function () {
        URL.revokeObjectURL(url);
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
        URL.revokeObjectURL(url);
        console.error("Could not decode image patch");
    };

    image.src = url;
}