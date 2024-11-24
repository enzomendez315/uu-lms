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

function make_grade_hypothesized($table) {
    // Called only for the students table
    if ($table.find("thead th:contains('Score')").length === 0) {
        return;
    }

    const $hypothesizeButton = $("<button>Hypothesize</button>");
    $table.before($hypothesizeButton);

    $hypothesizeButton.on("click", () => {
        if ($table.hasClass("hypothesized")) {
            // Switch back to actual grades
            $table.removeClass("hypothesized");
            $hypothesizeButton.text("Hypothesize");

            // Remove number inputs and restore original text
            $table.find("tbody td").each(function() {
                const $tdElement = $(this);
                const originalText = $tdElement.data("value");

                if (originalText !== undefined) {
                    $tdElement.text(originalText);
                }
            });
        } else {
            // Switch to hypothesized grades
            $table.addClass("hypothesized");
            $hypothesizeButton.text("Actual grades");

            // Replace contents of all "Not Due" or "Ungraded" <td> elements with a new number input
            $table.find("tbody td").each(function() {
                const $tdElement = $(this);
                const status = $tdElement.text();

                if (status === "Not Due" || status === "Ungraded") {
                    $tdElement.html('<input type="number" min="0" max="100" placeholder="">');
                }
            });
        }

        compute_current_grade($table);
    });

    $table.on("keyup", "input[type='number']", compute_current_grade($table));
}

function compute_current_grade($table) {
    let earnedPoints = 0;
    let availablePoints = 0;

    $table.find("tbody td").each(function() {
        const $tdElement = $(this);
        const status = $tdElement.text();
        const assignmentWeight = $tdElement.data("weight");

        if (status === "Not Due" || status === "Ungraded") {
            return;
        } else if (status === "Missing") {
            availablePoints += assignmentWeight;
        } else {
            // grade_percentage = submission.score / assignment.points
            const gradePercentage = parseFloat($tdElement.data("value"));
            // earned_points += grade_percentage * assignment.weight
            earnedPoints += gradePercentage * assignmentWeight;
            // available_points += assignment.weight
            availablePoints += assignmentWeight;
        }
    });

    const currentGrade = Math.round((earnedPoints / availablePoints) * 100);
    $table.find("tfoot td.numeric-column").text(`${currentGrade}%`);
}

say_hi($("h1"));
make_table_sortable($("table.sortable"));
make_form_async($("form.async-form"));
make_grade_hypothesized($("#profile-table"));