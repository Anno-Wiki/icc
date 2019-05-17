<script>
    function newFlash(category, message) {
        let li = newEl("li", category);
        let text = newEl("span", "text");
        text.innerHTML = message;
        let close = newEl("span", "close");
        close.setAttribute("onclick", "closeFlash(this);");
        close.innerHTML = "&times;";
        li.appendChild(text);
        li.appendChild(close);
        return li
    }
    function flashMessage(message) {
        // requires an array of [category, message]
        let container = allof("flash")[0];
        if (container == null) {
            container = newEl("ul", "flash js");
            let par = byID("container");
            par.insertBefore(container, par.childNodes[0]);
            let li = newFlash(message[0], message[1]);
            container.appendChild(li);
        }
    }
    function flashMessages() {
        let xhttp = new XMLHttpRequest();
        xhttp.onload = function () {
            const messages = JSON.parse(this.responseText);
            for (let i = 0; i < messages.length; i++)
                flashMessage(messages[i]);
        };
        xhttp.open("GET", "{{ url_for("ajax.flashed") }}", true);
        xhttp.send();
    }
    function closeFlash(x) {
        let flash = x.parentNode;
        let messages = flash.parentNode;
        messages.removeChild(flash);
        if (byTag(messages, 'li').length  < 1)
            messages.parentNode.removeChild(messages);
    }
</script>
