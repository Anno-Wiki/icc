function $(sel) { return document.querySelector(sel); }

window.onload = function () {
    tags = $("#tags");
    tags.onkeyup = function () { autocomplete(tags.value); };
};

function autocomplete(prefix) {
    var request = new XMLHttpRequest();
    request.open("POST", "/autocomplete/tags/");
    request.onload = function () {
        const data = JSON.parse(request.responseText);
        if (data.success) {
            console.log(data);
        } else {
            console.log("nope");
        }
    };

    const data = new FormData();
    data.append("tags", prefix);
    request.send(data);
};

