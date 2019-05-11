<script>
    document.addEventListener("DOMContentLoaded", function () {
        tagsInput = byID("tags");
        tagSpans = byID("tag_spans");
        autoBox = byID("autocomplete");
        master = byID("master_div");

        initTags();
        let submit = byID("submit");
        submit.onclick = repopulate;
    });

    function newTag(name, input=false) {
        // utility to create a new tag
        let tag = newEl("div", "tag");
        tag.innerHTML = name;
        if (input) {
            tag.onclick = function () {
                if (this.parentNode.childElementCount == 1)
                    tagsInput.placeholder = "e.g. (explanation freudian reference)";
                this.parentNode.removeChild(this);
                limitTags();
                tagsInput.focus();
            }
            tag.innerHTML = name + " &times;"
        }
        return tag;
    }

    function limitTags() {
        if (tagSpans.childNodes.length >= 5) {
            tagsInput.style.display = "none";
            let complain = newEl("div", "complain");
            complain.id = "complain";
            complain.innerHTML = "You cannot enter more than five tags.";
            master.parentNode.insertBefore(complain, master);
        } else {
            tagsInput.style.display = "";
            let complain = byID("complain");
            if (complain)
                complain.parentNode.removeChild(complain);
        }
    }

    function initTags() {
        // init the pre-existing tags
        let rawText = tagsInput.value;
        if (rawText != "") {
            let tagsArray = rawText.split(" ");
            for (let i = 0; i < tagsArray.length; i++) {
                let tag = newTag(tagsArray[i], true);
                tagSpans.appendChild(tag);
            }
            tagsInput.value = "";
            tagsInput.placeholder = "";
            limitTags();
        }
        tagsInput.onkeyup = autocomplete;
        tagsInput.onkeydown = function(event) {
            lastInput = this.value;
            let key = event.which || event.keyCode;
            if (key == 8 && lastInput == "")
                autocomplete(event);
        };
    }

    function space() {
        // process a space
        // don't pass true, because placeholder shouldn't be set
        let tag = newTag(tagsInput.value.replace(/(^\s+|\s+$)/g, '') + " &times;");
        tag.onclick = function() {
            this.parentNode.removeChild(this);
            limitTags();
        };
        tagSpans.appendChild(tag);
        tagsInput.value = "";
        tagsInput.placeholder = "";
        autoBox.innerHTML = "";
        limitTags();
    }

    function backspace() {
        // process a backspace
        autoBox.style.display = "";
        autoBox.innerHTML = "";
        if (lastInput == "") {
            let last = tagSpans.lastChild;
            if (last) {
                let text = last.innerHTML;
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
        limitTags();
    }

    function findTags() {
        // This is the actual autocomplete ajax method. Kinda ugly
        let request = new XMLHttpRequest();
        request.open("POST", "{{ url_for('ajax.tags') }}");
        limitTags();
        if (tagSpans.childNodes.length >= 5)
            console.log("yeah");

        request.onload = function () {
            const data = JSON.parse(request.responseText);
            let autoBox = byID("autocomplete");
            if (data.success) {
                autoBox.innerHTML = "";
                for (let i = 0; i < data.tags.length; i++) {
                    let tag = newTag(data.tags[i]); // autoBox tag
                    let card = newEl("div", "card");
                    let description = newEl("div", "description");
                    description.innerHTML = data.descriptions[i];
                    if (data.descriptions[i].length == 500)
                        description.classList.add("ellipsis");
                    card.appendChild(tag);
                    card.appendChild(description);
                    card.onclick = function() {
                        // input box tag
                        let tag = newTag(this.getElementsByClassName("tag")[0].innerHTML, true);
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
        let key = event.which || event.keyCode;
        if (key == 32)
            space();
        else if (key == 8 && tagsInput.value == "")
            backspace();
        else
            findTags();
    }

    function repopulate() {
        // This is to repopulate the field with a space separated string on
        // submit.
        let tags = tagSpans.children;
        let tagsArray = [];
        for (let i = 0; i < tags.length; i++) {
            tagsArray[i] = tags[i].innerHTML.slice(0,-2);
        }
        let tagString = tagsArray.join(" ");
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
