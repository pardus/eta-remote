const CHUNK_SIZE = 1024*1024*4; // 4Mb chunk size

const progressEl = document.getElementById("file-progress");

capture.addEventListener("dragover", (e) => e.preventDefault());

function getEntry(item) {
    if (item.webkitGetAsEntry) return item.webkitGetAsEntry();
    if (item.getAsEntry) return item.getAsEntry();
    return null;
}

function readAllEntries(reader) {
    return new Promise((resolve) => {
        const all = [];
        function next() {
            reader.readEntries((batch) => {
                if (!batch.length) {
                    resolve(all);
                    return;
                }
                all.push(...batch);
                next();
            }, () => resolve(all));
        }
        next();
    });
}

function entryToFile(entry) {
    return new Promise((resolve) => {
        entry.file((file) => {
            file.relPath = entry.fullPath ? entry.fullPath.slice(1) : entry.name;
            resolve(file);
        }, () => resolve(null));
    });
}

async function collectEntryFiles(entry, files) {
    if (entry.isFile) {
        const file = await entryToFile(entry);
        if (file) files.push(file);
    } else if (entry.isDirectory) {
        const entries = await readAllEntries(entry.createReader());
        for (const child of entries) {
            await collectEntryFiles(child, files);
        }
    }
}

async function getFilesFromItems(dt) {
    const files = [];
    const items = dt.items ? Array.from(dt.items) : [];
    let usedEntries = false;

    for (const item of items) {
        const entry = getEntry(item);
        if (entry) {
            usedEntries = true;
            await collectEntryFiles(entry, files);
        }
    }

    if (!usedEntries) {
        for (const item of items) {
            const file = item.getAsFile ? item.getAsFile() : null;
            if (file && (file.size > 0 || file.type)) files.push(file);
        }
    }
    return files;
}

capture.addEventListener("drop", async (e) => {
    e.preventDefault();
    const files = await getFilesFromItems(e.dataTransfer);
    for (const file of files) {
        sendFile(file);
    }
});

const pendingFiles = {};

function formatBytes(bytes, decimals = 1) {
    if (bytes === 0) return '0 B';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    let i = 0;
    while (bytes >= k && i < sizes.length - 1) {
        bytes /= k;
        i++;
    }

    return `${parseFloat(bytes.toFixed(dm))} ${sizes[i]}`;
}

function createProgressRow(name, total) {
    progressEl.classList.remove("hidden");

    const item = document.createElement("div");
    item.className = "file-progress-item";

    const nameEl = document.createElement("div");
    nameEl.className = "file-progress-name";
    nameEl.textContent = name;
    nameEl.title = name;

    const trackEl = document.createElement("div");
    trackEl.className = "file-progress-track";
    const barEl = document.createElement("div");
    barEl.className = "file-progress-bar";
    trackEl.appendChild(barEl);

    const infoEl = document.createElement("div");
    infoEl.className = "file-progress-info";
    infoEl.textContent = "0 B / " + formatBytes(total);

    item.appendChild(nameEl);
    item.appendChild(trackEl);
    item.appendChild(infoEl);
    progressEl.appendChild(item);

    return { item, barEl, infoEl };
}

function handleFileAck(name, chunk, complete) {
    const pending = pendingFiles[name];
    if (!pending) return;
    pending.waiting = false;
    if (complete) {
        delete pendingFiles[name];
        pending.row.barEl.style.width = "100%";
        pending.row.item.classList.add("done");
        setTimeout(() => {
            pending.row.item.remove();
            if (progressEl.childElementCount === 0) {
                progressEl.classList.add("hidden");
            }
        }, 400);
    } else {
        pending.readAndSendChunk();
    }
}

function sendFile(file) {
    const name = file.relPath || file.name;
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    let chunkIndex = 0;
    const row = createProgressRow(name, file.size);

    const pending = { waiting: false, readAndSendChunk: null, row };
    pending.readAndSendChunk = function() {
        if (pending.waiting) return;

        const start = chunkIndex * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, file.size);
        const slice = file.slice(start, end);

        const reader = new FileReader();
        reader.onload = () => {
            const base64 = reader.result.split(",")[1];
            pending.waiting = true;
            send("file", {
                name: name,
                mimetype: file.type,
                size: file.size,
                chunk: chunkIndex,
                totalChunks: totalChunks,
                data: base64
            });
            chunkIndex++;
            const transferred = Math.min(chunkIndex * CHUNK_SIZE, file.size);
            const pct = Math.round((transferred / file.size) * 100);
            row.barEl.style.width = pct + "%";
            row.infoEl.textContent = formatBytes(transferred) + " / " + formatBytes(file.size);
        };
        reader.readAsDataURL(slice);
    };

    pendingFiles[name] = pending;
    pending.readAndSendChunk();
}