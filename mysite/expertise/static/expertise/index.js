"use strict";

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

function convertToGraphData(apiData) {
    apiData.nodes = apiData.nodes.map((node) => {
        node.label = node.properties.name;
        delete node.properties;
        return node;
    });

    // maybe copy values with delete Object.assign(..) instead
    apiData.edges = apiData.relationships.map((rel) => {
        rel.source = rel.startNode;
        rel.target = rel.endNode;
        switch (rel.type) {
            case "ADVISED_BY":
                rel.label = "ADVISED BY";
                break;
            case "MEMBER_OF":
                rel.label = "MEMBER OF";
                break;
            default:
                rel.label = rel.type;
                break;
        }
        return rel;
    });
    delete apiData.relationships;
    return apiData;
}

function getColors() {
    const rootStyle = getComputedStyle(document.documentElement);
    const colors = {
        person: rootStyle.getPropertyValue("--color-person"),
        interest: rootStyle.getPropertyValue("--color-interest"),
        institute: rootStyle.getPropertyValue("--color-institute"),
        faculty: rootStyle.getPropertyValue("--color-faculty"),
        department: rootStyle.getPropertyValue("--color-department"),
        role: rootStyle.getPropertyValue("--color-role"),
        expertise: rootStyle.getPropertyValue("--color-expertise"),
    };
    return colors;
}

function drawG6Graph(apiData, personId, containerId, containerWidth){
    const data = convertToGraphData(apiData);
    const colors = getColors();
    data.nodes.forEach((node) => {
        node.style = {};
        switch (node.labels[0]) {
            case "Person":
                node.style.fill = colors.person;
                break;
            case "ResearchInterest":
                node.style.fill = colors.interest;
                break;
            case "Institute":
                node.style.fill = colors.institute;
                break;
            case "Faculty":
                node.style.fill = colors.faculty;
                break;
            case "Department":
                node.style.fill = colors.department;
                break;
            case "Role":
                node.style.fill = colors.role;
                break;
            case "Expertise":
                node.style.fill = colors.expertise;
                break;
        }
    });
    // highlight the node that the graph is about
    const sourceNode = data.nodes.find((node) => node.id === personId);
    sourceNode.style = {
        ...sourceNode.style,
        lineWidth: 3,
        stroke: "#000000",
        shadowColor: "#555555",
        shadowBlur: 3,
    };

    // TODO: cluster?
    const graph = new G6.Graph({
        container: containerId,
        width: containerWidth,
        height: 800,
        defaultNode: {
            type: "ellipse",
            style: {
                fill: "#ffffff",
                lineWidth: 1,
                stroke: "#a5abb6",
                cursor: "grab",
            },
        },
        defaultEdge: {
            style: {
                stroke: "#a5abb6",
                // TODO: fill arrow or make more obvious in other ways
                endArrow: true,
            },
            labelCfg: {
                style: {
                    opacity: 0.7,
                    fill: "#111111",
                },
            },
        },
        renderer: "canvas",
        layout: {
            type: "force2",
            animate: false,
            maxSpeed: 100,
            linkDistance: 300,
        },
        modes: {
            // TODO: make highlight only on click?
            default: ["drag-canvas", "zoom-canvas", "activate-relations", "drag-node"],
        },
        fitView: true,
    });

    graph.data(data);
    graph.render();

    // the resizing for long labels is called in this event, otherwise it won't
    // work with SVG (likely because it isn't drawn instantly)
    graph.on("afterrender", () => {
        graph.getNodes().forEach((node) => {
            // find the text shape by its name
            const labelShape = node.getContainer().find((e) => e.get("name") === "text-shape");
            // a node with no text/label would cause a layout error, according to
            // the library but I'm not sure if that is actually happening
            if (labelShape === null) {
                return;
            }
            // get the bounding box of the label
            const labelBBox = labelShape.getBBox();
            graph.updateItem(node, {
                size: [labelBBox.width + 15, labelBBox.height + 15],
            });
        });
    });
}

function showGraph(data, personId) {
    const containerId = "graph-container";
    const container = document.querySelector("#" + containerId);
    const containerWidth = 1600;
    container.style.width = containerWidth + "px";
    container.replaceChildren();
    drawG6Graph(data, personId, containerId, containerWidth);

    container.classList.remove("d-none");
    // select the svg or canvas element
    const networkEl = document.querySelector("#" + containerId + " > *");
    networkEl.classList.add("border", "border-info");
    container.scrollIntoView();
}

async function getGraph(personId) {
    // what happens in case of timeout?
    const url = "graph";
    try {
        const response = await fetch(`${url}?person=${encodeURIComponent(personId)}`);
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

    const personId = e.currentTarget.dataset.pk;
    getGraph(personId).then((data) => {
        if (data === undefined) {
            console.log("... graph request returned undefined");
            return;
        }
        showGraph(data.graph, personId);
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

/**
 * emulate button behavior for elements that can't be a button, e.g. tr.
 * might not work for buttons in forms
 * @param {HTMLElement} element
 * @param {Function} func the function that will be executed on click or keydown
 */
function emulateButton(element, func) {
    element.setAttribute("role", "button");
    element.setAttribute("tabindex", "0");
    element.addEventListener("click", func);
    element.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            // prevent scrolling from spacebar input
            e.preventDefault();
            element.click();
        }
        console.log(e.key);
    });
}

function appendEmailCell(tableRow, email) {
    const emailEl = document.createElement("td");
    tableRow.appendChild(emailEl);
    if (!email) {
        return;
    }
    const emailLink = document.createElement("a");
    emailLink.href = "mailto:" + email;
    emailLink.textContent = email;
    emailEl.appendChild(emailLink);
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

        emulateButton(tr, makeGraph);
        tableBody.appendChild(tr);
    });
}

function templateResult(item, container) {
    // if I wanted to color the search results, the color of the
    // exclude/highlight states would need to be handled too
    if (item.element) {
        // currently I only use the class for coloring the optgroup
        // so maybe I should only add the class to the optgroups?
        $(container).addClass($(item.element).attr("class"));
    }
    return item.text;
}

function templateSelection(item, container) {
    $(container).addClass($(item.element).attr("class"));

    // for displaying the optgroup name before the element for some groups
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
    // allow only one tag (= search word)
    if (searchSelection) {
        return null;
    }

    const term = $.trim(params.term);
    if (term === "") {
        return null;
    }

    return {
        id: term,
        text: term,
        newTag: true,
    };
}

$(".search-filter").select2({
    placeholder: "Select filters or enter new value for searching",
    maximumSelectionLength: 20,
    tags: true,
    tokenSeparators: [","],
    allowClear: true,
    templateSelection: templateSelection,
    templateResult: templateResult,
    createTag: createTag,
    debug: true,
    width: "100%",
});

$(".search-filter").on("change", function () {
    const persons = JSON.parse(sessionStorage.getItem("persons")) ?? [];
    fillTable(filter_persons(persons));
});

// prevents opening the dropdown after unselecting an item
$(".search-filter").on("select2:unselecting", function () {
    $(this).on("select2:opening", function (ev) {
        ev.preventDefault();
        $(this).off("select2:opening");
    });
});

const searchEl = document.querySelector("#search-button");
searchEl.addEventListener("click", search);

// after refreshing the page the user should have to search again
// if I don't clear the storage it would show the results of the
// previous search as soon as a search word or filter is entered
sessionStorage.removeItem("persons");
