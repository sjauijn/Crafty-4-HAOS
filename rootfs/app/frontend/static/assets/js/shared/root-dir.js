
function show_file_tree() {
    $("#dir_select").modal();
}

// ============= HELPER FUNCTIONS =============

function createIcon(className) {
    const i = document.createElement('i');
    i.className = className;
    return i;
}

function createRadio(className, name, value, disabled = false) {
    const input = document.createElement('input');
    input.type = 'radio';
    input.className = className;
    input.name = name;
    input.value = value;
    input.disabled = disabled;
    return input;
}

// Safe element lookup using CSS.escape for special characters in selectors
function getElementByPath(path, suffix = '') {
    const selector = `[data-path="${CSS.escape(path)}"]${suffix}`;
    return document.querySelector(selector);
}

function getSpanByPath(path) {
    return document.querySelector(
        `.files-tree-title[data-path="${CSS.escape(path)}"]`
    );
}

function getUlByPath(path) {
    return getElementByPath(path, ' > ul.tree-nested');
}

// ============= TREE ITEM CREATION =============

function createTreeItem(dpath, filename, isDir) {
    const li = document.createElement('li');
    li.dataset.path = dpath;  // Safe - browser handles escaping

    if (isDir) {
        li.className = 'tree-item';

        const div = document.createElement('div');
        div.dataset.path = dpath;
        div.dataset.name = filename;
        div.className = 'tree-caret tree-ctx-item tree-folder';

        const input = createRadio('root-input', 'root_path', dpath);

        const span = document.createElement('span');
        span.className = 'files-tree-title';
        span.dataset.path = dpath;
        span.dataset.name = filename;
        span.onclick = getDirView;

        span.appendChild(createIcon('ph ph-folder text-info'));
        span.appendChild(createIcon('ph ph-folder-open text-info'));
        span.appendChild(document.createTextNode(' ' + filename));  // createTextNode prevents HTML insertion

        div.appendChild(input);
        div.appendChild(span);
        li.appendChild(div);
    } else {
        li.className = 'd-block tree-ctx-item tree-file';
        li.dataset.name = filename;

        const input = createRadio('checkBoxClass d-none file-check', 'root_path', dpath, true);

        const iconSpan = document.createElement('span');
        iconSpan.style.marginRight = '6px';
        iconSpan.appendChild(createIcon('far fa-file'));

        li.appendChild(input);
        li.appendChild(iconSpan);
        li.appendChild(document.createTextNode(filename));  // createTextNode prevents HTML insertion
    }

    return li;
}

function createTreeUl(path) {
    const ul = document.createElement('ul');
    ul.className = 'tree-nested d-block';
    ul.dataset.path = path;  // Use data-path instead of id
    return ul;
}

// ============= MAIN PROCESSING =============

function process_tree_response(response) {
    document.getElementById('upload_submit').disabled = false;

    const path = response.data.request_path;
    const ul = createTreeUl(path);

    // Build tree items
    Object.entries(response.data).forEach(([key, value]) => {
        if (key === "top" || key === "request_path") {
            return;  // Skip metadata keys
        }
        const item = createTreeItem(value.path, key, value.dir);
        ul.appendChild(item);
    });

    if (response.data.top) {
        // Top-level: append to main container
        const mainTreeDiv = document.getElementById('main-tree-div');
        const filesTree = document.getElementById('files-tree');

        if (mainTreeDiv) {
            mainTreeDiv.appendChild(ul);
            const mainTree = document.getElementById('main-tree');
            if (mainTree?.parentElement) {
                mainTree.parentElement.classList.add("clicked");
            }
        } else if (filesTree) {
            filesTree.innerHTML = '';
            filesTree.appendChild(ul);
        } else {
            console.error("Could not find main-tree-div or files-tree container");
        }
    } else {
        // Nested: append to parent folder's div
        const parentSpan = getSpanByPath(path);
        const parentDiv = parentSpan?.closest('.tree-folder');

        if (parentSpan && parentDiv) {
            parentSpan.classList.add('tree-caret-down');
            parentDiv.appendChild(ul);
            parentDiv.classList.add("clicked");

            // Add toggle listener
            parentSpan.addEventListener("click", function caretListener() {
                const childUl = getUlByPath(path);
                if (childUl) childUl.classList.toggle("d-block");
                parentSpan.classList.toggle("tree-caret-down");
            });
        } else {
            console.error("Could not find parent element for path:", path);
        }
    }
}

// ============= EVENT HANDLERS =============

function getDirView(event = false) {
    if (event) {
        try {
            const path = event.target.parentElement.dataset.path;
            if (!$(event.target).closest(".tree-folder").hasClass('clicked')) {
                getTreeView(path);
                return;
            }
        } catch {
            console.log("Well that failed");
        }
    } else {
        getTreeView();
    }
}

async function getTreeView(path = "") {
    const token = getCookie("_xsrf");

    try {
        let res = await fetch(`/api/v2/import/archive/select`, {
            method: 'POST',
            headers: {
                'X-XSRFToken': token
            },
            body: JSON.stringify({ "file_name": $("#file-uploaded").val(), "local_path": path, }),
        });
        let responseData = await res.json();

        // Remove loading dialogs
        let x = document.querySelector('.bootbox');
        if (x) {
            x.remove()
        }
        x = document.querySelector('.modal-backdrop');
        if (x) {
            x.remove()
        }

        if (responseData.status === "ok") {
            process_tree_response(responseData);
            show_file_tree();
        } else {
            bootbox.alert({
                title: responseData.error,
                message: responseData.error_data,
                callback: function () {
                    location.reload();
                }
            });
        }
    } catch (error) {
        console.error("Error in getTreeView:", error);
        // Remove loading dialog on error
        let x = document.querySelector('.bootbox');
        if (x) {
            x.remove()
        }
        x = document.querySelector('.modal-backdrop');
        if (x) {
            x.remove()
        }
        bootbox.alert({
            title: "Error",
            message: "Failed to load archive contents: " + error.message
        });
    }
}

function getToggleMain(event) {
    const path = event.target.parentElement.getAttribute('data-path');
    document.getElementById("files-tree").classList.toggle("d-block");
    const span = getSpanByPath(path);
    if (span) {
        span.classList.toggle("tree-caret-down");
        span.classList.toggle("tree-caret");
    }
}

const rootUploadButton = document.getElementById("root_upload_button");
if (rootUploadButton) {
    rootUploadButton.addEventListener("click", function () {
        if (this.classList.contains('clicked')) {
            show_file_tree();
            return;
        } else {
            this.classList.add('clicked')
        }
        bootbox.dialog({
            message: `<i class='ph-fill ph-gear ph-spin'></i>&nbsp; ${$("#lower_half").attr("data-loading")}`,
            closeButton: false
        });
        setTimeout(function () {
            getDirView();
        }, 2000);
    });
}

