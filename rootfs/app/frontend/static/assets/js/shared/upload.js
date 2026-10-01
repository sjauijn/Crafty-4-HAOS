let activeUploads = 0;
let last_tree_view = "";
const uploadProgressMap = new Map();
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function uploadChunk(file, url, chunk, start, end, chunk_hash, totalChunks, type, path, fileId, i, file_num, updateProgressBar) {
    return fetch(url, {
        method: 'POST',
        body: chunk,
        headers: {
            'Content-Range': `bytes ${start}-${end - 1}/${file.size}`,
            'Content-Length': chunk.size,
            'fileSize': file.size,
            'chunkHash': chunk_hash,
            'chunked': true,
            'totalChunks': totalChunks,
            'fileName': file.name,
            'location': path,
            'fileId': fileId,
            'chunkId': i,
        },
    })
        .then(async response => {
            const rawText = await response.text();
            if (!response.ok) {
                let errorData;
                try {
                    errorData = JSON.parse(rawText);
                } catch (parseErr) {
                    throw new Error(JSON.stringify({ error_data: `Non-JSON error response for chunk ${i} (status ${response.status}): ${rawText}` }));
                }
                throw new Error(JSON.stringify(errorData) || 'Unknown error occurred');
            }
            try {
                return JSON.parse(rawText);
            } catch (parseErr) {
                throw new Error(JSON.stringify({ error_data: `Non-JSON success response for chunk ${i} (status ${response.status}): ${rawText}` }));
            }
        })
        .then(data => {
            if (data.status !== "completed" && data.status !== "partial") {
                throw new Error(data.message || 'Unknown error occurred');
            }
            // Update progress bar
            const progress = Math.round(((i + 1) / totalChunks) * 100);
            const previousProgress = uploadProgressMap.get(fileId) || 0;
            const newProgress = Math.max(previousProgress, progress);
            uploadProgressMap.set(fileId, newProgress);
            updateProgressBar(newProgress, type, file_num, fileId);
        });
}

async function uploadFile(type, file = null, path = null, file_num = 0, fileId = null, _onProgress = null) {
    if (file == null) {
        try {
            file = $("#file")[0].files[0];
        } catch {
            bootbox.alert("Please select a file first.");
            return;
        }
    }
    if (!fileId) {
        fileId = uuidv4();
    }
    const token = getCookie("_xsrf");
    if (type !== "server_upload") {
        document.getElementById("upload_input").innerHTML = '<div class="progress" style="width: 100%;"><div id="upload-progress-bar" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100" style="width: 100%">&nbsp;<i class="ph-bold ph-spinner-gap"></i></div></div>';
    }

    let url = '';
    if (type === "server_upload") {
        url = `/api/v2/servers/${serverId}/files/upload/`;
    } else if (type === "background") {
        url = `/api/v2/crafty/admin/upload/`;
    } else if (type === "import") {
        url = `/api/v2/servers/import/upload/`;
    }
    console.log(url);

    const chunkSize = 1024 * 1024 * 10; // 10MB
    const totalChunks = Math.ceil(file.size / chunkSize);

    const errors = [];
    const batchSize = 30; // Number of chunks to upload in each batch

    try {
        let res = await fetch(url, {
            method: 'POST',
            headers: {
                'X-XSRFToken': token,
                'chunked': true,
                'fileSize': file.size,
                'type': type,
                'totalChunks': totalChunks,
                'fileName': file.name,
                'location': path,
                'fileId': fileId,
            },
            body: null,
        });

        const initRawText = await res.text();

        if (!res.ok) {
            let errorResponse;
            try {
                errorResponse = JSON.parse(initRawText);
            } catch (parseErr) {
                throw new Error(JSON.stringify({ error_data: `Non-JSON error response (status ${res.status}): ${initRawText}` }));
            }
            throw new Error(JSON.stringify(errorResponse));
        }

        let responseData;
        try {
            responseData = JSON.parse(initRawText);
        } catch (parseErr) {
            throw new Error(JSON.stringify({ error_data: `Non-JSON success response (status ${res.status}): ${initRawText}` }));
        }

        if (responseData.status !== "ok") {
            throw new Error(JSON.stringify(responseData));
        }

        const upload_ready_promise = new Promise(resolve => {
            const interval = setInterval(() => {
                if (activeUploads < 2) { // Do not overload browser
                    clearInterval(interval);
                    resolve();
                }
            }, 100);
        });

        await upload_ready_promise;
        activeUploads++;
        for (let i = 0; i < totalChunks; i += batchSize) {
            const batchPromises = [];

            for (let j = 0; j < batchSize && (i + j) < totalChunks; j++) {
                const start = (i + j) * chunkSize;
                const end = Math.min(start + chunkSize, file.size);
                const chunk = file.slice(start, end);
                const chunk_hash = await calculateFileHash(chunk);

                const uploadPromise = uploadChunk(file, url, chunk, start, end, chunk_hash, totalChunks, type, path, fileId, i + j, file_num, updateProgressBar)
                    .catch(error => {
                        errors.push(error); // Store the error
                    });

                batchPromises.push(uploadPromise);
            }

            // Wait for the current batch to complete before proceeding to the next batch
            await Promise.all(batchPromises);

            // Optional delay between batches to account for rate limiting
            await delay(2000); // Adjust the delay time (in milliseconds) as needed
        }
    } catch (error) {
        errors.push(error); // Store the error
    }

    if (errors.length > 0) {

        const errorMessage = errors.map(error => {
            let rawString = typeof error === 'string' ? error : (error.message || '');

            if (rawString.startsWith("Error: ")) {
                rawString = rawString.replace("Error: ", "").trim();
            }

            try {
                const parsed = JSON.parse(rawString);
                return parsed.error_data || 'Unknown error occurred';
            } catch (parseErr) {
                return rawString || 'Unknown error occurred';
            }
        }).join('<br>');
        console.log(errorMessage);
        bootbox.alert({
            title: 'Error',
            message: errorMessage,
            callback: function () {
                window.location.reload();
            },
        });
    } else if (type !== "server_upload") {
        // All promises resolved successfully
        $("#upload_input").html(`<div class="card-header header-sm d-flex justify-content-between align-items-center" style="width: 100%;"><input value="${file.name}" type="text" id="file-uploaded" disabled></input> 🔒</div>`);
        if (type === "import") {
            document.getElementById("lower_half").classList.remove("d-none");
            document.getElementById("lower_half").hidden = false;
            $("#root_upload_button").click();
        } else if (type === "background") {
            setTimeout(function () {
                location.href = `/panel/custom_login`;
            }, 2000);
        }
    } else {

        $(`#upload-progress-bar-${fileId}`).removeClass("progress-bar-striped");
        $(`#upload-progress-bar-${fileId}`).addClass("bg-success");
        $(`#upload-progress-bar-${fileId}`).html('<i style="color: black;" class="ph ph-box-check"></i>');
        removeProgressItem(fileId);

        if (activeUploads == 1) {
            getTreeView($("#table-nav").attr("data-cur-path"));
        }
    }
    activeUploads--;
}

const SHA256_K = new Uint32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]);

function sha256Rotr(x, n) {
    return ((x >>> n) | (x << (32 - n))) >>> 0;
}

function sha256Fallback(arrayBuffer) {
    let h0 = 0x6a09e667, h1 = 0xbb67ae85, h2 = 0x3c6ef372, h3 = 0xa54ff53a;
    let h4 = 0x510e527f, h5 = 0x9b05688c, h6 = 0x1f83d9ab, h7 = 0x5be0cd19;

    const bytes = new Uint8Array(arrayBuffer);
    const bitLen = bytes.length * 8;
    const padLen = (((bytes.length + 8) >> 6) + 1) << 6;
    const padded = new Uint8Array(padLen);
    padded.set(bytes);
    padded[bytes.length] = 0x80;
    const view = new DataView(padded.buffer);
    view.setUint32(padLen - 4, bitLen >>> 0, false);
    view.setUint32(padLen - 8, Math.floor(bitLen / 4294967296), false);

    const w = new Uint32Array(64);
    for (let offset = 0; offset < padLen; offset += 64) {
        for (let i = 0; i < 16; i++) {
            w[i] = view.getUint32(offset + i * 4, false);
        }
        for (let i = 16; i < 64; i++) {
            const s0 = sha256Rotr(w[i - 15], 7) ^ sha256Rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
            const s1 = sha256Rotr(w[i - 2], 17) ^ sha256Rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
            w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
        }

        let a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, h = h7;
        for (let i = 0; i < 64; i++) {
            const S1 = sha256Rotr(e, 6) ^ sha256Rotr(e, 11) ^ sha256Rotr(e, 25);
            const ch = (e & f) ^ (~e & g);
            const temp1 = (h + S1 + ch + SHA256_K[i] + w[i]) >>> 0;
            const S0 = sha256Rotr(a, 2) ^ sha256Rotr(a, 13) ^ sha256Rotr(a, 22);
            const maj = (a & b) ^ (a & c) ^ (b & c);
            const temp2 = (S0 + maj) >>> 0;

            h = g; g = f; f = e;
            e = (d + temp1) >>> 0;
            d = c; c = b; b = a;
            a = (temp1 + temp2) >>> 0;
        }

        h0 = (h0 + a) >>> 0; h1 = (h1 + b) >>> 0; h2 = (h2 + c) >>> 0; h3 = (h3 + d) >>> 0;
        h4 = (h4 + e) >>> 0; h5 = (h5 + f) >>> 0; h6 = (h6 + g) >>> 0; h7 = (h7 + h) >>> 0;
    }

    return [h0, h1, h2, h3, h4, h5, h6, h7].map(v => v.toString(16).padStart(8, '0')).join('');
}

async function calculateFileHash(file) {
    const arrayBuffer = await file.arrayBuffer();

    if (globalThis.crypto && globalThis.crypto.subtle) {
        const hashBuffer = await globalThis.crypto.subtle.digest('SHA-256', arrayBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    return sha256Fallback(arrayBuffer);
}

function updateProgressBar(progress, type, _i, file_id) {
    if (type !== "server_upload") {
        if (progress === 100) {
            $(`#upload-progress-bar`).removeClass("progress-bar-striped")

            $(`#upload-progress-bar`).removeClass("progress-bar-animated")
        }
        $(`#upload-progress-bar`).css('width', progress + '%');
        $(`#upload-progress-bar`).html(progress + '%');
    } else {
        if (progress === 100) {
            $(`#upload-progress-bar-${file_id}`).removeClass("progress-bar-striped")

            $(`#upload-progress-bar-${file_id}`).removeClass("progress-bar-animated")
        }
        $(`#upload-progress-bar-${file_id}`).css('width', progress + '%');
        $(`#upload-percent-${file_id}`).html(progress + '%');
        $("#operation-total").html(`<span id="notif-count" class="badge bg-primary">${$("#upload-progress-bar-parent").children().length}</span>`);
    }
}


function removeProgressItem(item_id) {
    $(`#upload-progress-bar-${item_id}-container`).remove();
    const total_items = $("#upload-progress-bar-parent").children().length
    if (total_items > 0) {
        $("#operation-total").html(`<span id="notif-count" class="badge bg-primary">${total_items}</span>`);
    } else {
        $("#operation-total").html(``); //remove badge if no items
    }
}

function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replaceAll(/[xy]/g, function (c) {
        const r = Math.trunc(Math.random() * 16),
            v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}


if (webSocket) {
    webSocket.on('upload_process', function (data) {
        if (data.total_files === data.cur_file) {
            updateProgressBar(100, data.type, data.cur_file, data.file_id)
        } else {
            let progress = Math.round((data.cur_file / data.total_files) * 100, 1);
            updateProgressBar(progress, data.type, data.cur_file, data.file_id)
        }
    });
}
globalThis.addEventListener('beforeunload', (e) => {
    console.log(activeUploads)
    if (activeUploads > 0) {
        e.preventDefault();
        globalThis.alert('Uploads active. Are you sure you want to leave?');
    }
});
