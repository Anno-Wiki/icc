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
    function flashMessages() {
        let xhttp = new XMLHttpRequest();
        xhttp.onload = function () {
            const messages = JSON.parse(this.responseText);
            let container = allof("flash")[0];
            if (container == null) {
                container = newEl("ul", "flash");
                let par = byID("container");
                par.insertBefore(container, par.childNodes[0]);
            }
            for (let i = 0; i < messages.length; i++) {
                let li = newFlash(messages[i][0], messages[i][1]);
                container.appendChild(li);
            }
        };
        xhttp.open("GET", "{{ url_for("ajax.flashed") }}", true);
        xhttp.send();
    }
</script>
