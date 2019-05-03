<script>
    document.addEventListener("DOMContentLoaded", function () {
        initTags();
        submit = byID("submit");
        submit.onclick = repopulate;
    });

    function newTag(name, input=false) {
        // utility to create a new tag
        var tag = newEl("div", "tag");
        var tagsInput = byID("tags");
        tag.innerHTML = name;
        if (input) {
            tag.onclick = function () {
                if (this.parentNode.childElementCount == 1)
                    tagsInput.placeholder = "e.g. (explanation freudian reference)";
                this.parentNode.removeChild(this);
                tagsInput.focus();
            }
            tag.innerHTML = name + " &times;"
        }
        return tag;
    }

    function initTags() {
        // init the pre-existing tags
        var tagsInput = byID("tags");
        var rawText = tagsInput.value;
        if (rawText != "") {
            var tagsArray = rawText.split(" ");
            var tagSpans = byID("tag_spans");
            for (var i = 0; i < tagsArray.length; i++) {
                var tag = newTag(tagsArray[i], true);
                tagSpans.appendChild(tag);
            }
            tagsInput.value = "";
            tagsInput.placeholder = "";
        }
        tagsInput.onkeyup = autocomplete;
        tagsInput.onkeydown = function(event) {
            lastInput = this.value;
            var key = event.which || event.keyCode;
            if (key == 8 && lastInput == "")
                autocomplete(event);
        };
    }

    function space() {
        // process a space
        var tagsInput = byID("tags");
        // don't pass true, because placeholder shouldn't be set
        var tag = newTag(tagsInput.value.replace(/(^\s+|\s+$)/g, '') + " &times;");
        tag.onclick = function() { this.parentNode.removeChild(this); };
        var tagSpans = byID("tag_spans");
        tagSpans.appendChild(tag);
        tagsInput.value = "";
        tagsInput.placeholder = "";
        autoBox.innerHTML = "";
    }

    function backspace() {
        // process a backspace
        var autoBox = byID("autocomplete");
        var tagsInput = byID("tags");
        var tagSpans = byID("tag_spans");
        autoBox.style.display = "";
        autoBox.innerHTML = "";
        if (lastInput == "") {
            var last = tagSpans.lastChild;
            if (last) {
                var text = last.innerHTML;
                if (text) {
                    text = text.slice(0, -2);
                    tagsInput.value = text;
                }
                tagSpans.removeChild(last);
                if (tagSpans.childElementCount < 1) {
                    tagsInput.placeholder = "e.g. (explanation freudian reference)";
                }
            }
        }
    }

    function findTags() {
        // This is the actual autocomplete ajax method. Kinda ugly
        var request = new XMLHttpRequest();
        request.open("POST", "{{ url_for('ajax.tags') }}");
        var tagsInput = byID("tags");

        request.onload = function () {
            const data = JSON.parse(request.responseText);
            var autoBox = byID("autocomplete");
            if (data.success) {
                autoBox.innerHTML = "";
                for (var i = 0; i < data.tags.length; i++) {
                    var tag = newTag(data.tags[i]); // autoBox tag
                    var card = newEl("div", "card");
                    var description = newEl("div", "description");
                    description.innerHTML = data.descriptions[i];
                    if (data.descriptions[i].length == 500)
                        description.classList.add("ellipsis");
                    card.appendChild(tag);
                    card.appendChild(description);
                    card.onclick = function() {
                        // input box tag
                        var tag = newTag(this.getElementsByClassName("tag")[0].innerHTML, true);
                        byID("tag_spans").append(tag);
                        autoBox.innerHTML = "";
                        autoBox.style.display = "";
                        tagsInput.value = "";
                        tagsInput.placeholder = "";
                        tagsInput.focus();
                    }
                    autoBox.appendChild(card);
                }
                if (data.tags.length >= 1) {
                    autoBox.style.display = "flex";
                } else {
                    autoBox.style.display = "";
                }

            }
        };
        const data = new FormData();
        data.append("tags", tagsInput.value);
        request.send(data);
    }

    function autocomplete(event) {
        // This executes the autocomplete thing
        var tagsInput = byID("tags");
        var key = event.which || event.keyCode;
        if (key == 32) {
            space();
        } else if (key == 8 && tagsInput.value == "") {
            backspace();
        } else {
            findTags();
       }
    }

    function repopulate() {
        // This is to repopulate the field with a space separated string on
        // submit.
        var tagsInput = byID("tags");
        var tagSpans = byID("tag_spans");
        var tags = tagSpans.children;
        var tagsArray = [];
        for (var i = 0; i < tags.length; i++) {
            tagsArray[i] = tags[i].innerHTML.slice(0,-2);
        }
        var tagString = tagsArray.join(" ");
        if (tagString != "" && tagsInput.value != "" ){
            tagsInput.value = tagString + " " + tagsInput.value;
            tag_spans.innerHTML = "";
        } else if (tagString != "") {
            tagsInput.value = tagString;
            tagSpans.innerHTML = "";
        }
    }

    function focusDiv(x) { x.parentNode.parentNode.classList.add("focus"); }
    function blurDiv(x) { x.parentNode.parentNode.classList.remove("focus"); }
</script>
