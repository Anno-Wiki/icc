$(document).ready(function(){
    
    
    var getAllBetween = function (firstEl,lastEl) {
        var firstElement = $(firstEl); // First Element
        var lastElement = $(lastEl); // Last Element
        var collection = new Array(); // Collection of Elements
        collection.push(firstElement.attr('id')); // Add First Element to Collection
        $(firstEl).nextAll().each(function(){ // Traverse all siblings
            var siblingID  = $(this).attr('id'); // Get Sibling ID
            if (siblingID != $(lastElement).attr('id')) { // If Sib is not LastElement
                collection.push($(this).attr('id')); // Add Sibling to Collection
            } else { // Else, if Sib is LastElement
                collection.push(lastElement.attr('id')); // Add Last Element to Collection
                return false; // Break Loop
            }
        });         
        return collection; // Return Collection
    }

    var get_selection = function (event){
        if (window.getSelection) { // non-IE
            userSelection = window.getSelection();
            rangeObject = userSelection.getRangeAt(0);
            if (rangeObject.startContainer == rangeObject.endContainer) {
               // alert(rangeObject.startContainer.parentNode.id);
                return rangeObject.startContainer.parentNode.id;
            } else {
                return getAllBetween(
                    rangeObject.startContainer.parentNode,
                    rangeObject.endContainer.parentNode);
            }

        } else if (document.selection) { // IE lesser
            userSelection = document.selection.createRange();
            var ids = new Array();
            
            if (userSelection.htmlText.toLowerCase().indexOf('span') >= 0) {
                $(userSelection.htmlText).filter('span').each(function(index, span) {
                    ids.push(span.id);
                });
                return ids;
            } else {
                return userSelection.parentElement().id;
            }
        }
    }

    document.addEventListener('selectionchange', function() {
        console.log(get_selection());
    });
});
