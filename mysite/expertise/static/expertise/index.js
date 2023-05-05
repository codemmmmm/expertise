"use strict";

function formatLabel(item) {
    /**display optgroup name before the element for items of some optgroups */
    const labels = {
        "Persons": "Person",
        "Advisors": "Advisor",
        "Offered expertise": "Offered",
        "Wanted expertise": "Wanted",
    };

    const option = $(item.element);
    const optgroup = option.closest("optgroup").attr("label");
    const label = labels[optgroup];
    return label ? label + " | " + item.text : item.text;
}

function createTag(params) {
    const selections = $(".search-filter").select2("data");
    const searchSelection = selections.find((element) => element.newTag === true);
    // don't allow more than one tag (= search word)
    if (searchSelection) {
        return null;
    }

    var term = $.trim(params.term);
    if (term === "") {
        return null;
    }

    return {
        id: term,
        text: term,
        newTag: true,
    };
}

function showLoading(button) {
    button.innerHTML = "<span class=\"spinner-border spinner-border-sm me-1\" role=\"status\" aria-hidden=\"true\"></span>Searching...";
}

function hideLoading(button) {
    button.textContent = "Search";
}

async function getPersons(searchWord) {
    const url = "persons";
    try {
        const response = await fetch(`${url}?search=${encodeURIComponent(searchWord)}`);
        if (!response.ok) {
            throw new Error("Network response was not OK");
        }
        return response.json();
    } catch (error) {
        console.error("There has been a problem with your fetch operation:", error);
    }
}

function search(e) {
    e.preventDefault();
    showLoading(e.target);
    // get search parameter
    const selections = $(".search-filter").select2("data");
    const searchSelection = selections.find((element) => element.newTag === true);
    const searchWord = searchSelection === undefined ? "" : searchSelection.text;

    getPersons(searchWord).then((data) => {
        if (data === undefined) {
            // set the sessionStorage to empty array to prevent other actions
            // possibly using outdated search results
            sessionStorage.setItem("persons", JSON.stringify([]));
            updateAlert(null);
            hideLoading(e.target);
            return;
        }
        const persons = data.persons;
        //console.log(persons);
        sessionStorage.setItem("persons", JSON.stringify(persons));
        hideLoading(e.target);
        fillTable(filter_persons(persons));
        updateAlert(persons.length);
    });
}

function updateAlert(length) {
    const alertEl = document.querySelector(".search-alert");
    alertEl.classList.remove("d-none");
    alertEl.classList.add("d-inline-block");
    if (length === null) {
        alertEl.textContent = "Search failed!";
        alertEl.classList.remove("alert-success");
        alertEl.classList.add("alert-warning");
    } else {
        alertEl.textContent = `${length} result${length === 1 ? "" : "s"} found (before filtering).`;
        alertEl.classList.remove("alert-warning");
        alertEl.classList.add("alert-success");
    }
}

function drawG6Graph(data, containerId){
    const nodes = [
        { id: "1", label: "Max Muster" },
        { id: "2", label: "Jana Schuster von Grafhausen die Dritte" },
        { id: "3", label: "NLP" },
        { id: "4", label: "TU Dresden" },
        { id: "5", label: "Prof. Hagel" },
    ];

    const edges = [
        { source: "1", target: "3", label: "WANTS" },
        { source: "2", target: "3", label: "OFFERS" },
        { source: "1", target: "2", label: "ADVISED_BY" },
        { source: "2", target: "4", label: "MEMBER_OF" },
        { source: "5", target: "4", label: "MEMBER_OF" },
    ];

    // TODO remove
    data = {
        nodes: nodes,
        edges: edges,
    };

    const graph = new G6.Graph({
        container: containerId,
        width: 2000,
        height: 800,
        defaultNode: {
            type: "ellipse",
            color: "#5B8FF9",
            style: {
                fill: "#9EC9FF",
                lineWidth: 1,
            },
        },
        defaultEdge: {
            style: {
                stroke: "#7fb0f1",
                // TODO: fill arrow or make more obvious in other ways
                endArrow: true,
            },
        },
        renderer: "svg",
        layout: {
            type: "force2",
            animate: false,
            maxSpeed: 100,
            linkDistance: 300,
            //preventOverlap: true,
        },
        modes: {
            // TODO: make highlight only on click?
            default: ["drag-canvas", "zoom-canvas", "activate-relations", "drag-node"],
        },
    });

    graph.data(data);
    graph.render();

    // the resizing for long labels is called in this event or otherwise
    // it won't work with SVG (likely because it isn't drawn right after function call)
    graph.on("afterrender", () => {
        graph.getNodes().forEach((node) => {
            // find the text shape by its name
            const labelShape = node.getContainer().find((e) => e.get("name") === "text-shape");
            // get the bounding box of the label
            const labelBBox = labelShape.getBBox();
            graph.updateItem(node, {
                size: [labelBBox.width + 15, labelBBox.height + 15],
            });
        });
    });
}

function showGraph(data) {
    const containerId = "graph-container";
    const container = document.querySelector("#" + containerId);
    drawG6Graph(data, containerId);

    container.classList.remove("d-none");
    const networkEl = document.querySelector("#" + containerId + " > svg");
    networkEl.classList.add("border", "border-info");
    container.scrollIntoView();
}

async function getGraph(personId) {
    // what happens in case of timeout?
    const url = "graph";
    try {
        const response = await fetch(`${url}?personId=${encodeURIComponent(personId)}`);
        if (!response.ok) {
            throw new Error("Network response was not OK");
        }
        return response.json();
    } catch (error) {
        console.error("There has been a problem with your fetch operation:", error);
    }
}

function makeGraph(e) {
    // clicking the email link won't cause the graph to be drawn
    if (e.target.nodeName === "A") {
        return;
    }

    const personId = e.currentTarget.dataset.id;
    console.log("getting graph data...");
    getGraph(personId).then((data) => {
        if (data === undefined) {
            console.log("... graph request returned undefined");
            return;
        }
        const graphData = data.graph;
        console.log(graphData);
        showGraph(graphData);
    });
}

function group_filters(filters, id) {
    return filters.filter((filter) => filter.id.substring(0, 4) === id);
}

/**
 * return true if any of the values is in the filters list or if filters list is empty
 * @param {Array} filters
 * @param {Array} values
 * @returns {boolean}
 */
function isMatching(filters, values) {
    if (filters.length === 0) {
        return true;
    }

    // values.forEach can't be used because you can't return from inside it
    for (const value of values) {
        if (filters.some((filter) => filter.id.slice(5) === value.pk)) {
            return true;
        }
    }
    return false;
}

function isMatchingPerson(filters, person) {
    if (filters.length === 0) {
        return true;
    }

    if (filters.some((filter) => filter.id.slice(5) === person.pk)) {
        return true;
    }
    return false;
}

/**
 * returns filtered array of persons.
 * @param {Array} persons
 */
function filter_persons(persons) {
    const selections = $(".search-filter").select2("data");
    // excluding the user created selections here is only necessary
    // because a user might create a tag with e.g. the value "inst-xxx"
    const filters = selections.filter((element) => element.newTag === undefined);

    // group the filters by category
    // the id is the key prepended to the suggestions in the Django template
    const person_filters = group_filters(filters, "pers");
    const interests_filters = group_filters(filters, "inte");
    const institutes_filters = group_filters(filters, "inst");
    const faculties_filters = group_filters(filters, "facu");
    const departments_filters = group_filters(filters, "depa");
    const roles_filters = group_filters(filters, "role");
    const advisors_filters = group_filters(filters, "advi");
    const offered_filters = group_filters(filters, "offe");
    const wanted_filters = group_filters(filters, "want");

    const filtered = persons.filter((person) => {
        return isMatchingPerson(person_filters, person.person) &&
            isMatching(interests_filters, person.interests) &&
            isMatching(institutes_filters, person.institutes) &&
            isMatching(faculties_filters, person.faculties) &&
            isMatching(departments_filters, person.departments) &&
            isMatching(roles_filters, person.roles) &&
            isMatching(advisors_filters, person.advisors) &&
            isMatching(offered_filters, person.offered) &&
            isMatching(wanted_filters, person.wanted);
    });
    return filtered;
}

function concatTitleName(title, name) {
    return title === "" ? name : title + " " + name;
}

function makePill(text, id) {
    const pill = document.createElement("span");
    pill.classList.add("pill");
    pill.textContent = text;
    // TODO: add category to id?
    pill.dataset.pk = id;
    return pill;
}

function appendBasicTableCell(tableRow, values) {
    const td = document.createElement("td");
    values.forEach((value) => {
        td.appendChild(makePill(value.name, value.pk));
    });
    tableRow.appendChild(td);
}

function appendEmailCell(tableRow, email) {
    // TODO: if email empty, don't create a link
    const emailEl = document.createElement("td");
    const emailLink = document.createElement("a");
    emailLink.href = "mailto:" + email;
    emailLink.textContent = email;
    emailEl.appendChild(emailLink);
    tableRow.appendChild(emailEl);
}

function fillTable(persons) {
    // TODO: tabindex to pills and tr, keyboard event handlers etc.
    const tableBody = document.querySelector(".persons-table tbody");
    // remove all children
    tableBody.replaceChildren();
    persons.forEach((p) => {
        const tr = document.createElement("tr");
        tr.dataset.pk = p.person.pk;

        const personEl = document.createElement("td");
        const personText = concatTitleName(p.person.title, p.person.name);
        const personPill = makePill(personText, p.person.pk);
        personEl.appendChild(personPill);
        tr.appendChild(personEl);

        appendEmailCell(tr, p.person.email);
        appendBasicTableCell(tr, p.interests);
        appendBasicTableCell(tr, p.institutes);
        appendBasicTableCell(tr, p.faculties);
        appendBasicTableCell(tr, p.departments);
        // should advisor titles be shown?
        appendBasicTableCell(tr, p.advisors);
        appendBasicTableCell(tr, p.roles);
        appendBasicTableCell(tr, p.offered);
        appendBasicTableCell(tr, p.wanted);

        tr.addEventListener("click", makeGraph);
        tr.setAttribute("role", "button");
        tableBody.appendChild(tr);
    });
}

$(".search-filter").select2({
    placeholder: "Select filters or enter new value for searching",
    maximumSelectionLength: 20,
    tags: true,
    tokenSeparators: [","],
    allowClear: true,
    templateSelection: formatLabel,
    createTag: createTag,
    debug: true,
    width: "100%",
});

$(".search-filter").on("change", function () {
    const persons = JSON.parse(sessionStorage.getItem("persons")) ?? [];
    fillTable(filter_persons(persons));
});

const searchEl = document.querySelector("#search-button");
searchEl.addEventListener("click", search);

// after refreshing the page the user should have to search again
// if I don't clear the storage it would show the results of the
// previous search as soon as a search word or filter is entered
sessionStorage.removeItem("persons");
