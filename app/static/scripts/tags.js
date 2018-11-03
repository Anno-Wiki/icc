function $(sel) { return document.querySelector(sel); }

window.onload = function () {
    initial_tag_creation();
};

function initial_tag_creation() {
    var tags = $("#tags");
    var raw_text = tags.value;
    if (raw_text != "") {
        var tags_array = raw_text.split(" ");
        var div = $("#tag_spans");
        var array_length = tags_array.length;
        for (var i = 0; i < array_length; i++) {
            var tag = document.createElement("tag");
            tag.innerHTML = tags_array[i] + " &times;";
            tag.onclick = function() {
                spans = $("#tag_spans");
                this.parentNode.parentNode.removeChild(this.parentNode);
            };
            div.appendChild(tag);
        }
        tags.value = "";
    }
    tags.onkeyup = autocomplete;
};


function autocomplete(event) {
    var key = event.which || event.keyCode;
    var prefix = $("#tags").value;
    if (key == 32) {
        var tag = document.createElement("tag");
        prefix = prefix.replace(/(^\s+|\s+$)/g, '');
        tag.innerHTML = prefix + " &times;";
        tag.onclick = function() {
            spans = $("#tag_spans");
            this.parentNode.parentNode.removeChild(this.parentNode);
        };
        var div = $("#tag_spans");
        div.appendChild(tag);
        $("#tags").value = "";
    } else if (key == 8 && prefix == "") {
        var spans = $("#tag_spans");
        var last = spans.lastChild;
        if (last) {
            var text = last.innerHTML;
            var input = $("#tags");
            if (text) {
                text = text.slice(0, -2); 
                input.value = text;
            }
            spans.removeChild(last);
        }
    } else {
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
    }
};
