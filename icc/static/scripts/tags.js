function $(sel) { return document.querySelector(sel); }

window.onload = function () {
    initial_tag_creation();
    submit = $("#submit");
    submit.onclick = repopulate;
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
                $("#tag_spans").removeChild(this);
            };
            div.appendChild(tag);
        }
        tags.value = "";
    }
    tags.onkeyup = autocomplete;
    tags.onkeydown = function(event) {
        var input = $("#tags");
        last_input = tags.value;
    };
}

function autocomplete(event) {
    var key = event.which || event.keyCode;
    var prefix = $("#tags").value;
    if (key == 32) {                            // space
        var tag = document.createElement("tag");
        prefix = prefix.replace(/(^\s+|\s+$)/g, '');
        tag.innerHTML = prefix + " &times;";
        tag.onclick = function() {
            $("#tag_spans").removeChild(this);
        };
        var div = $("#tag_spans");
        div.appendChild(tag);
        $("#tags").value = "";
        var autocomplete_box = $("#autocomplete");
        autocomplete_box.innerHTML = "";
    } else if (key == 8 && prefix == "") {
        var autocomplete_box = $("#autocomplete");
        if (last_input == "") {      // backspace
            var spans = $("#tag_spans");
            var last = spans.lastChild;
            autocomplete_box.innerHTML = "";
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
            autocomplete_box.innerHTML = "";
        }

    } else {
        var request = new XMLHttpRequest();
        request.open("POST", "/ajax/autocomplete/tags/");
        request.onload = function () {
            const data = JSON.parse(request.responseText);
            var autocomplete_box = $("#autocomplete");
            if (data.success) {
                autocomplete_box.innerHTML = "";
                for (var i = 0; i < data.tags.length; i++) {
                    var tag = document.createElement("tag");
                    tag.innerHTML = data.tags[i];
                    tag.onclick = function() {
                        new_tag = document.createElement("tag");
                        new_tag.innerHTML = this.innerHTML + " &times;";
                        new_tag.onclick = function() {
                            $("#tag_spans").removeChild(this)
                        }
                        $("#tag_spans").append(new_tag);
                        $("#autocomplete").innerHTML = "";
                        $("#tags").value = "";
                    }
                    autocomplete_box.appendChild(tag);
                }
            } else {
                autocomplete_box.innerHTML = "No results found.";
            }
        };

        const data = new FormData();
        data.append("tags", prefix);
        request.send(data);
    }
}

function repopulate() {
    var tags_input = $("#tags");
    var tag_spans = $("#tag_spans");
    var tags = tag_spans.children;
    var tags_array = [];
    var num_tags = tags.length;
    for (var i = 0; i < num_tags; i++) {
        tags_array[i] = tags[i].innerHTML.slice(0,-2);
    }
    var tag_string = tags_array.join(" ");
    if (tag_string != "" && tags_input.value != "" ){
        tags_input.value = tag_string + " " + tags_input.value;
        tag_spans.innerHTML = "";
    } else if (tag_string != "") {
        tags_input.value = tag_string;
        tag_spans.innerHTML = "";
    }
}
