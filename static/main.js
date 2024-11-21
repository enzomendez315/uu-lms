import { $ } from "/static/jquery/src/jquery.js";

function say_hi(elt) {
    console.log("Welcome to", elt.text());
}

function make_table_sortable($table) {
    // Select the sortable headers of the table
    const $sortableHeaders = $table.find("thead th.sort-column");
    $sortableHeaders.on("click", (e) => {
        const $headerToSort = $(e.target);
        const columnIndex = $headerToSort.index();
        let isAscending = false;
        let unsorted = false;

        // Change order depending on status
        // asc -> desc -> unsorted
        $sortableHeaders.not($headerToSort).removeClass("sort-asc sort-desc").removeAttr("aria-sort");
        if ($headerToSort.hasClass("sort-asc")) {
            // Change to descending order
            $headerToSort.removeClass("sort-asc");
            $headerToSort.addClass("sort-desc");
            $headerToSort.attr("aria-sort", "descending");
        } else if ($headerToSort.hasClass("sort-desc")) {
            // Change to unsorted order
            $headerToSort.removeClass("sort-desc");
            $headerToSort.removeAttr("aria-sort");
            unsorted = true;
        } else {
            // Change to ascending order
            $headerToSort.addClass("sort-asc");
            $headerToSort.attr("aria-sort", "ascending");
            isAscending = true;
        }

        // Convert from string to number, then sort
        const rows = $table.find("tbody tr").toArray();
        rows.sort((row1, row2) => {
            let cell1, cell2;
            let tdElement1 = $(row1).children("td").get(columnIndex);
            let tdElement2 = $(row2).children("td").get(columnIndex);
            
            if (!unsorted) {
                cell1 = parseFloat($(tdElement1).data("value")) || 0;
                cell2 = parseFloat($(tdElement2).data("value")) || 0;
            } else {
                cell1 = $(row1).data("index");
                cell2 = $(row2).data("index");
            }

            if (isAscending || unsorted) {
                return cell1 - cell2;
            } else {
                return cell2 - cell1;
            }
        });

        // Put rows back in the right order
        for (const row of rows) {
            $(row).appendTo("tbody");
        }
    });
}

function make_form_async($form) {
    $form.on("submit", (e) => {
        e.preventDefault();

        const formData = new FormData($form[0]);
        $.ajax({
            url: $form.attr("action"),
            data: formData,
            type: "POST",
            processData: false,
            contentType: false,
            mimeType: $form.attr("enctype"),
            success: () => {
                $form.replaceWith("<p>Upload succeeded</p>");
            },
            error: (error) => {
                console.log("Could not upload document: ", error);
                // Re-enable file input and submit button
                $form.find("input").removeAttr("disabled");
                $form.find("button").removeAttr("disabled");
            }
        });

        // Disable file input and submit button
        $form.find("input").attr("disabled");
        $form.find("button").attr("disabled");
    });
}

say_hi($("h1"));
make_table_sortable($("table.sortable"));
make_form_async($("form.async-form"));