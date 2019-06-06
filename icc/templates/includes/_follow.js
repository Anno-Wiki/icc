<script nonce="{{ csp_nonce() }}">
    atload(function () {
        let follows = allof('follow');
        for (let i = 0; i < follows.length; i++)
            follows[i].removeAttribute('href');
    });

    function follow(el) {
        let xhttp = new XMLHttpRequest();
        xhttp.onload = function () {
            console.log(this.responseText);
            data = JSON.parse(this.responseText);
            if (data.success)
                el.innerHTML = data.status;
        };
        let url = `{{ url_for("ajax.follow") }}?id=${el.dataset.id}&entity=${el.dataset.entity}`;
        xhttp.open('GET', url, true);
        xhttp.send();
    }
</script>
