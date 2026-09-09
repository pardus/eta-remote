const CHUNK_SIZE = 1024*1024*4; // 4Mb chunk size

const progressEl = document.getElementById("file-progress");
const progressBar = document.getElementById("file-progress-bar");
const progressText = document.getElementById("file-progress-text");

capture.addEventListener("dragover", (e) => e.preventDefault());

capture.addEventListener("drop", (e) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    for (const file of files) {
        sendFile(file);
    }
});

function sendFile(file) {
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    let chunkIndex = 0;

    progressEl.classList.remove("hidden");

    function readAndSendChunk() {
        const start = chunkIndex * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, file.size);
        const slice = file.slice(start, end);

        const reader = new FileReader();
        reader.onload = () => {
            const base64 = reader.result.split(",")[1];
            send("file", {
                name: file.name,
                mimetype: file.type,
                size: file.size,
                chunk: chunkIndex,
                totalChunks: totalChunks,
                data: base64
            });
            chunkIndex++;
            const pct = Math.round((chunkIndex / totalChunks) * 100);
            progressBar.style.width = pct + "%";
            progressText.textContent = pct + "%";
            if (chunkIndex < totalChunks) {
                readAndSendChunk();
            } else {
                setTimeout(() => progressEl.classList.add("hidden"), 300);
            }
        };
        reader.readAsDataURL(slice);
    }

    readAndSendChunk();
}