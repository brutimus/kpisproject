jQuery.fn.sortElements = (function() {

    var sort = [].sort;

    return function(comparator, getSortable) {

        getSortable = getSortable || function() {
            return this;
        };

        var placements = this.map(function() {

            var sortElement = getSortable.call(this),
                parentNode = sortElement.parentNode,

                // Since the element itself will change position, we have
                // to have some way of storing its original position in
                // the DOM. The easiest way is to have a 'flag' node:
                nextSibling = parentNode.insertBefore(
                    document.createTextNode(''),
                    sortElement.nextSibling
                );

            return function() {

                if (parentNode === this) {
                    throw new Error(
                        "You can't sort elements if any one is a descendant of another."
                    );
                }

                // Insert before flag:
                parentNode.insertBefore(this, nextSibling);
                // Remove flag:
                parentNode.removeChild(nextSibling);

            };

        });

        return sort.call(this, comparator).each(function(i) {
            placements[i].call(getSortable.call(this));
        });

    };

})();

$(document).ready(function() {
    $(function() {
        $('.table-accordion').each(function(index, el) {
            $table = $(el);
            $table.find("tbody tr").not('.accordion').hide();
            $table.find(".accordion").click(function() {
                $(this).siblings().fadeToggle(200);
            });
        });
    });
    $('table.table-sortable').each(function(index, el) {
        $(el).find('th.sort').each(function(index2, el2) {
            $(el2).click(function(event) {
                $(el).find('>tbody').sortElements(function(a, b) {
                    return parseInt($(a).find('thead>tr>th[name="' + el2.getAttribute('name') + '"]').text()) > parseInt($(b).find('thead>tr>th[name="' + el2.getAttribute('name') + '"]').text()) ? -1 : 1;
                })
            });
        });
    });
    $('.tt').tooltip();
});
