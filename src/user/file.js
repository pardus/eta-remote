const CHUNK_SIZE = 64 * 1024;

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
            if (chunkIndex < totalChunks) {
                readAndSendChunk();
            }
        };
        reader.readAsDataURL(slice);
    }

    readAndSendChunk();
}