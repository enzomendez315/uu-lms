import { $ } from "/static/jquery/src/jquery.js";

function say_hi(elt) {
    console.log("Welcome to", elt.text());
}

function make_table_sortable($table) {
    // Select the last header cell of the table
    const $lastHeader = $table.find("thead th.numeric-column");
    $lastHeader.on("click", () => {
        let isAscending = true;

        // Change order depending on status
        if ($lastHeader.hasClass("sort-desc")) {
            $lastHeader.removeClass("sort-desc");
            $lastHeader.addClass("sort-asc");
        } else if ($lastHeader.hasClass("sort-asc")) {
            $lastHeader.removeClass("sort-asc");
            $lastHeader.addClass("sort-desc");
            isAscending = false;
        } else {
            $lastHeader.addClass("sort-asc");
        }

        // Convert from string to number, then sort
        const rows = $table.find("tbody tr").toArray();
        rows.sort((row1, row2) => {
            const cell1 = parseFloat($(row1).find("td.numeric-column").text()) || 0;
            const cell2 = parseFloat($(row2).find("td.numeric-column").text()) || 0;

            if (isAscending) {
                return cell1 - cell2;
            } else {
                return cell2 - cell1;
            }
        });

        // Put rows back in the right order
        for (const row of rows) {
            $(row).appendTo("tbody");
        }
    })
}

say_hi($("h1"));
make_table_sortable($("table.sortable"));