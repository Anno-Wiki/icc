<script>
    atload(function () {
        let arrows = allof('arrows');
        for (let i = 0; i < arrows.length; i++) {
            let updown = byTag(arrows[i], 'a');
            for (let j = 0; j < updown.length; j++) {
                updown[j].removeAttribute('href');
                updown[j].style.cursor = 'pointer';
            }
        }
    });
    function loginNext(route, id) {
        // just a minor complexity reducer for upvote/downvote
        // if the user is not logged in, redirect him to the login with
        // the next param being to upvote the annotation and the next
        // param after that being the page he is currently on
        let next = escape(`/${route}/${id}?next=${window.location.pathname}`);
        return `{{ url_for('main.login') }}?next=${next}`;
    }

    function vote(x, up) {
        let entity = byID(x.dataset['parent']);
        let xhttp = new XMLHttpRequest();
        xhttp.onload = function () {
            let data = JSON.parse(this.responseText);
            let weight = first(entity, 'weight');
            if (data.status == 'login') {
                location.href = loginNext(id, up);
                return;
            }
    }
    function downvote(x) {
        let id = parentNumID(x, 'a').replace(/a/, '');
        let xhttp = new XMLHttpRequest();

        xhttp.onload = function () {
            let data = JSON.parse(this.responseText);
            let weight = byCls(parentNum(x, 'a'), 'weight')[0];
            if (data.situ.includes('login')) {
                // don't let us go any farther if need to login
                location.href = loginNext('downvote', id);
                return;
            }
            if (data.situ.includes('rollback')) {
                if (data.situ.includes('success')) {
                    x.className = 'down';
                    byID(`up${id}`).className = '';
                } else { x.className = ''; }
            } else if (data.situ.includes('success')) { x.className = 'up'; }
            if ('change' in data)
                modWeight(weight, data.change);
            flashMessages();
        }
        xhttp.open('GET', url, true);
        xhttp.send();
    }

    function upvote(x) {
        let id = parentNumID(x, 'a').replace(/a/, '');
        let xhttp = new XMLHttpRequest();

        xhttp.onload = function () {
            let data = JSON.parse(this.responseText);
            let weight = byCls(parentNum(x, 'a'), 'weight')[0];
            if (data.situ.includes('login')) {
                location.href = loginNext('upvote', id);
                return;
            }
            if (data.situ.includes('rollback')) {
                if (data.situ.includes('success')) {
                    x.className = 'up';
                    byID(`down${id}`).className = '';
                } else { x.className = ''; }
            } else if (data.situ.includes('success')) { x.className = 'up'; }
            if ('change' in data)
                modWeight(weight, data.change);
            flashMessages();
        }
        xhttp.open('GET', url, true);
        xhttp.send();
    }

    function modWeight(weight, change) {
        let points = Number(weight.innerHTML);
        let newPoints = points + change;

        let poppers = [];
        let pushers = [];
        if (newPoints > 0) {
            poppers = ['down', 'nil'];
            pushers = ['up'];
        } else if (newPoints < 0) {
            poppers = ['up', 'nil'];
            pushers = ['down'];
        } else {
            poppers = ['up', 'down'];
            pushers = ['nil'];
        }
        pushers.forEach(function(el) { weight.classList.add(el) });
        poppers.forEach(function(el) { weight.classList.remove(el) });
        weight.innerHTML = `${newPoints} `;
    }
</script>
