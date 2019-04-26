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
