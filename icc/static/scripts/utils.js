function byID(id) { return document.getElementById(id); }
function byClass (el, cl) { return el ? el.getElementsByClassName(cl) : [] }
function allof (cl) { return byClass(document, cl) }
function newEl(el, cl) {
        var el = document.createElement(el);
        el.className = cl;
        return el;
}

function get_parent(el, prefix="") {
    string = ["^", prefix, "\\d+"];
    var re = new RegExp(string.join(""), "g");
    while(!el.id || !el.id.match(re)) {
        el = el.parentNode;
    }
    return el
}
function get_parent_id(el, prefix="") {
    return get_parent(el, prefix).id;
}
