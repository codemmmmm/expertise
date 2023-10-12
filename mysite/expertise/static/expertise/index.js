/*global G6, bootstrap*/
"use strict";

import { writeToClipboard } from "./utils.js";

function initializeClipboardButtons() {
    const formButton = document.querySelector("button.clipboard-button.filters");
    formButton.addEventListener("click", copyShareLink);
    const graphButton = document.querySelector("button.clipboard-button.filters-graph");
    graphButton.addEventListener("click", copyShareLink);
}

function copyShareLink(e) {
    const button = e.currentTarget;
    const shareGraph = e.currentTarget.classList.contains("filters-graph");
    writeToClipboard(button, () => {
        return getShareUrl(shareGraph);
    });
}

/**
 * @param {Boolean} shareGraph
 * @returns {String}
 */
async function getShareUrl(shareGraph) {
    const url = new URL(document.URL);
    const shareParams = getShareParametersFromSelection(shareGraph);
    // return the URL with the query arguments removed
    if (shareParams.size === 0) {
        return url.href.split("?")[0];
    }

    let shortenedParams = "";
    try {
        const data = await fetchShortenedParams(shareParams.toString());
        shortenedParams = data.value;
    } catch (error) {
        console.error("Failed to compress the parameters: " + error);
    }
    // sets the search parameter while keeping other parameters
    const params = url.searchParams;
    params.set("share", String(shortenedParams));
    url.search = params.toString();
    return url.toString();
}

/**
 * @param {Boolean} shareGraph
 * @returns {URLSeachParams}
 */
function getShareParametersFromSelection(shareGraph) {
    const params = new URLSearchParams();

    const selections = $(".search-filter").select2("data");
    const filters = selections.filter((element) => element.element.dataset.newTag !== "true");
    if (filters.length) {
        filters.forEach((filter) => {
            // don't discard the id prefix because it is needed for selecting the right
            // elements when loading the shared state
            params.append("filter", filter.id);
        });
    }

    const searchPhrases = selections.filter((element) => element.element.dataset.newTag === "true");
    if (searchPhrases.length) {
        searchPhrases.forEach((phrase) => {
            params.append("search", phrase.text);
        });
    }

    if (shareGraph) {
        const personId = document.querySelector("#graph-container").dataset.personId;
        params.append("graph-node", personId);
    }
    return params;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * save a short representation of longValue to the database and return that
 * @param {String} longValue
 * @returns {Promise.<Object>}
 */
async function fetchShortenedParams(longValue) {
    const CsrfToken = getCookie("csrftoken");
    const response = await fetch("shorten", {
        method: "POST",
        headers: { "X-CSRFToken": CsrfToken },
        mode: "same-origin",
        body: JSON.stringify({ parameters: longValue }),
    });
    if (!response.ok) {
        throw new Error("Request failed");
    }
    return response.json();
}

/**
 * get the data for a shared view from the HTML element, populate the table and input,
 * trigger the graph
 */
function loadSharedViewFromHtml() {
    const dataEl = document.querySelector("#share-data");
    const searchPhrases = JSON.parse(dataEl.dataset.search);
    searchPhrases.forEach((phrase) => appendSearchPhraseToGroup(phrase));

    const tableData = JSON.parse(dataEl.dataset.table);
    if (tableData.length) {
        const searchData = {
            searchPhrases: searchPhrases,
            data: tableData,
        };
        sessionStorage.setItem("personData", JSON.stringify(searchData));
        updateTable(tableData);
        document.querySelector(".persons-table-container").classList.remove("d-none");
    }
    initializeSelect2(false);

    const nodeId = dataEl.dataset.graph;
    if (nodeId) {
        makeGraph(nodeId);
    }
}

function showSearchLoading(button) {
    button.innerHTML = "<span class=\"spinner-border spinner-border-sm me-1\" role=\"status\" aria-hidden=\"true\"></span>Searching...";
}

function hideSearchLoading(button) {
    button.textContent = "Search";
}

/**
 *
 * @param {Array.<String>} searchPhrases
 * @returns
 */
async function getPersons(searchPhrases) {
    const path = "persons";
    const params = new URLSearchParams();
    if (searchPhrases.length) {
        searchPhrases.forEach((phrase) => {
            params.append("search", phrase);
        });
    } else {
        params.append("search", "");
    }

    try {
        const response = await fetch(`${path}?${params.toString()}`);
        if (!response.ok) {
            throw new Error("Network response was not OK");
        }
        return response.json();
    } catch (error) {
        console.error("There has been a problem with your fetch operation:", error);
    }
}

function searchAndUpdate(e) {
    e.preventDefault();

    // get search phrases
    const selections = $(".search-filter").select2("data");
    const searchSelections = selections.filter((element) => element.element.dataset.newTag === "true");
    const searchPhrases = searchSelections.map((phrase) => phrase.text);

    // don't fetch data from the server if it's the same search phrases
    const personData = JSON.parse(sessionStorage.getItem("personData"));
    if (personData) {
        const lastSearchPhrases = personData?.searchPhrases ?? [];
        if (JSON.stringify(lastSearchPhrases) === JSON.stringify(searchPhrases)) {
            const searchResults = personData.data;
            updateTable(searchResults);
            return;
        }
    }

    showSearchLoading(e.target);
    getPersons(searchPhrases).then((data) => {
        hideSearchLoading(e.target);
        if (data === undefined) {
            updateAlert(null);
            return;
        }
        const searchData = {
            searchPhrases: searchPhrases,
            data: data.persons,
        };
        sessionStorage.setItem("personData", JSON.stringify(searchData));
        updateTable(data.persons);
        document.querySelector(".persons-table-container").classList.remove("d-none");
    });
}

function updateTable(personData) {
    const filteredPersonData = filter_persons(personData);
    fillTable(filteredPersonData);
    updateAlert(personData.length, filteredPersonData.length);
}

function updateAlert(searchedLength, filteredLength) {
    const alertEl = document.querySelector(".search-alert");
    alertEl.classList.remove("d-none");
    alertEl.classList.add("d-inline-block");
    if (searchedLength === null) {
        alertEl.textContent = "Search failed!";
        alertEl.classList.remove("alert-success");
        alertEl.classList.add("alert-warning");
    } else {
        alertEl.textContent = `${filteredLength} ${filteredLength === 1 ? "entry" : "entries"}` +
        ` shown / ${searchedLength} ${searchedLength === 1 ? "entry" : "entries"} found`;
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
            case "INTERESTED_IN":
                rel.label = "INTERESTED IN";
                break;
            case "HAS":
                rel.label = "IS";
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

function wrapNodeLabels(str, pattern) {
    return str.replace(pattern, "$1\n");
}

/**
 * gets pattern for inserting line breaks at or before the max length with String.replace
 * https://stackoverflow.com/a/51506718/15707077
 * @param {number} maxLength
 */
function getWordWrapPattern(maxLength) {
    return new RegExp(`(?![^\n]{1,${maxLength}}$)([^\n]{1,${maxLength}})\\s`, "g");
}

function prepareGraphData(apiData) {
    const data = convertToGraphData(apiData);
    const colors = getColors();
    const breakStringAt = 22;
    const regexPattern = getWordWrapPattern(breakStringAt);
    data.nodes.forEach((node) => {
        node.label = wrapNodeLabels(node.label, regexPattern);
        node.style = {};
        node.stateStyles = {
            active: {
                lineWidth: 1,
            },
        };
        const label = node.labels[0];
        switch (label) {
            case "Person":
                node.style.fill = colors.person;
                node.stateStyles.active.fill = colors.person;
                break;
            case "ResearchInterest":
                node.style.fill = colors.interest;
                node.stateStyles.active.fill = colors.interest;
                break;
            case "Institute":
                node.style.fill = colors.institute;
                node.stateStyles.active.fill = colors.institute;
                break;
            case "Faculty":
                node.style.fill = colors.faculty;
                node.stateStyles.active.fill = colors.faculty;
                break;
            case "Department":
                node.style.fill = colors.department;
                node.stateStyles.active.fill = colors.department;
                break;
            case "Role":
                node.style.fill = colors.role;
                node.stateStyles.active.fill = colors.role;
                break;
            case "Expertise":
                node.style.fill = colors.expertise;
                node.stateStyles.active.fill = colors.expertise;
                break;
            default:
                console.warn(`The node label '${label}' was not recognized. Default styles applied.`);
        }
    });
    return data;
}

/**
 *
 * @param {*} apiData
 * @param {*} personId
 * @param {*} containerId
 * @param {*} containerWidth
 * @returns {string} name of the person that the graph is about
 */
function drawG6Graph(apiData, containerId, container){
    const data = prepareGraphData(apiData);
    // change this value instead of directly editing renderer and fitView properties
    const useCanvas = true;
    const height = 800;
    const graph = new G6.Graph({
        container: containerId,
        width: 1600, // initial value
        height: height,
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
        renderer: useCanvas ? "canvas" : "svg",
        layout: {
            type: "force2",
            animate: false,
            linkDistance: 280,
            maxSpeed: 1300,
            preventOverlap: true,
        },
        // is the animation configuration bugged?
        // animateCfg: {
        //     duration: 1,
        //     callback: () => { console.log("finished"); },
        // },
        modes: {
            default: ["drag-canvas", "zoom-canvas", "activate-relations", "drag-node"],
        },
        // because I call graph.fitView after setting the correct canvas size
        fitView: false,
    });

    graph.data(data);
    graph.render();
    setGraphEvents(graph, container, useCanvas, height);
    graphGlobal = graph;
}

function handleNodeClick(e) {
    if (e.originalEvent.shiftKey) {
        nodeToggleFilter(e);
    } else {
        changeGraphData(e);
    }
}

function setGraphEvents(graph, container, useCanvas, height) {
    graph.on("beforerender", () => {
        // turn animation off, else afterrender event and resizing of the nodes happens late
        graph.updateLayout({ animate: false });
    });

    graph.on("afterrender", async () => {
        if (!useCanvas) {
            // the svg needs to be visible for getting the element sizes if svg used
            // but the user can see the graph getting resized
            container.querySelector("canvas, svg").classList.remove("d-none");
            // wait till svg is actually drawn
            await new Promise((r) => setTimeout(r, 100));
        }
        graph.getNodes().forEach((node) => {
            // find the text shape by its name
            const labelShape = node.getContainer().find((el) => el.get("name") === "text-shape");
            if (labelShape === null) {
                return;
            }
            // get the bounding box of the label
            const labelBBox = labelShape.getBBox();
            graph.updateItem(node, {
                size: [labelBBox.width + 15, labelBBox.height + 20],
            });
        });
        graph.fitCenter();
        // animation for dragging nodes
        graph.updateLayout({ animate: true });
    });

    graph.on("node:click", handleNodeClick);
    graph.on("node:touchstart", changeGraphData);

    if (useCanvas) {
        graph.on("node:dragstart", function (e) {
            graph.layout();
            refreshDraggedNodePosition(e);
        });
        graph.on("node:drag", function (e) {
            refreshDraggedNodePosition(e);
            graph.layout();
        });
        graph.on("node:dragend", function (e) {
            e.item.get("model").fx = null;
            e.item.get("model").fy = null;
        });
    }

    const modalEl = document.getElementById("graphModal");
    modalEl.addEventListener("shown.bs.modal", () => {
        // needs to be called after modal is shown, else container width = 0
        container.querySelector("canvas, svg")?.classList.remove("d-none");
        graph.changeSize(container.clientWidth, height);
        graph.fitView();
        hideModalSpinner();
    });
    window.addEventListener("resize", () => {
        graph.changeSize(container.clientWidth, height);
    });
}

function refreshDraggedNodePosition(e) {
    const model = e.item.get("model");
    model.fx = e.x;
    model.fy = e.y;
}

function nodeToggleFilter(e) {
    const item = e.item;
    const id = item.get("id");
    const label = item.getModel().labels[0];
    // for person/advisor and offered/wanted expertise toggle both because
    // there is no way to know which the user wanted
    switch (label) {
        case "Person":
            toggleSelection("pers-" + id);
            toggleSelection("advi-" + id);
            break;
        case "ResearchInterest":
            toggleSelection("inte-" + id);
            break;
        case "Institute":
            toggleSelection("inst-" + id);
            break;
        case "Faculty":
            toggleSelection("facu-" + id);
            break;
        case "Department":
            toggleSelection("depa-" + id);
            break;
        case "Role":
            toggleSelection("role-" + id);
            break;
        case "Expertise":
            toggleSelection("offe-" + id);
            toggleSelection("want-" + id);
            break;
    }
}

function changeGraphData(e) {
    const graph = graphGlobal;
    const id = e.item.get("id");
    setGraphId(id);
    getGraph(id)
        .then((data) => {
            data = prepareGraphData(data.graph);
            graph.changeData(data);
            graph.render();
        })
        .catch((error) => {
            hideModalSpinner();
            document.querySelector("#graph-container").textContent = error.message;
        });
}

function showGraph(data) {
    const containerId = "graph-container";
    const container = document.querySelector("#" + containerId);
    if (!data.nodes.length) {
        hideModalSpinner();
        container.textContent = "No nodes found.";
        return;
    }
    drawG6Graph(data, containerId, container);
    // select the svg or canvas element
    const networkEl = document.querySelector("#" + containerId + " > *");
    networkEl.classList.add("border", "border-info", "rounded", "rounded-1", "d-none");
    networkEl.setAttribute("alt", "Network graph");
}

async function getGraph(nodeId) {
    // what happens in case of timeout?
    const path = "graph";
    const response = await fetch(`${path}?id=${encodeURIComponent(nodeId)}`);
    if (!response.ok) {
        throw new Error("Request failed");
    }
    return response.json();
}

function setGraphId(id) {
    document.querySelector("#graph-container").dataset.personId = id;
}

/**
 * if the graph was triggered from a button and not programmatically (share link)
 */
function makeGraphWrapper(e) {
    // don't execute the callback when the email link is clicked
    if (e.target.nodeName === "A") {
        return;
    }

    // for setting focus after modal close
    e.currentTarget.dataset.lastSelected = true;
    const personId = e.currentTarget.dataset.pk;
    makeGraph(personId);
}

function makeGraph(personId) {
    makeModal();
    setGraphId(personId);
    getGraph(personId)
        .then((data) => {
            showGraph(data.graph);
        })
        .catch((error) => {
            hideModalSpinner();
            document.querySelector("#graph-container").textContent = error.message;
    });
}

function makeModal() {
    const modalEl = document.getElementById("graphModal");
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
    resetModalContent();
}

function hideModalSpinner() {
    document.querySelector(".graph-spinner").classList.add("d-none");
}

function resetModalContent() {
    document.querySelector(".graph-spinner").classList.remove("d-none");
    document.querySelector("#graph-container").replaceChildren();
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
function isMatching(filters, values, ignoreEmpty=false) {
    if (filters.length === 0 && !ignoreEmpty) {
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

function isMatchingPerson(filters, person, ignoreEmpty=false) {
    if (filters.length === 0 && !ignoreEmpty) {
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
    const filters = selections.filter((element) => element.element.dataset.newTag !== "true");

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

    // filters of different categories are generally connected by AND
    // the persons/advisors and offered/wanted expertise categories use OR
    const filtered = persons.filter((person) => {
        const matchingPersons = isMatchingPerson(person_filters, person.person, true) ||
            isMatching(advisors_filters, person.advisors, true) ||
            (person_filters.length === 0 && advisors_filters.length === 0);
        const matchingExpertise = isMatching(offered_filters, person.offered, true) ||
            isMatching(wanted_filters, person.wanted, true) ||
            (offered_filters.length === 0 && wanted_filters.length === 0);

        return matchingPersons &&
            isMatching(interests_filters, person.interests) &&
            isMatching(institutes_filters, person.institutes) &&
            isMatching(faculties_filters, person.faculties) &&
            isMatching(departments_filters, person.departments) &&
            isMatching(roles_filters, person.roles) &&
            matchingExpertise;
    });
    return filtered;
}

function concatTitleName(title, name) {
    return title === "" ? name : title + " " + name;
}

/**
 * adds the id or removes it if it's already selected
 * @param {string} id
 */
function toggleSelection(id) {
    const $searchFilter = $(".search-filter");
    const values = $searchFilter.val();
    const index = values.indexOf(id);
    if (index === -1) {
        $searchFilter.val([id, ...values]);
    } else {
        // remove the element in-place
        values.splice(index, 1);
        $searchFilter.val(values);
    }
    $searchFilter.trigger("change");
}

function pillClick(e) {
    e.stopPropagation();
    toggleSelection(e.target.dataset.pk);
}

function makePill(text, id) {
    const pill = document.createElement("button");
    pill.classList.add("pill");
    pill.textContent = text;
    pill.dataset.pk = id;
    pill.tabIndex = -1;
    pill.addEventListener("click", pillClick);
    pill.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            e.stopPropagation();
            e.target.click();
        }
    });
    return pill;
}

/**
 * emulate button behavior for elements that can't be a button, e.g. tr.
 * might not work for buttons in forms
 * @param {HTMLElement} element
 * @param {Function} func the function that will be executed on click and keydown
 */
function emulateButton(element, func) {
    element.setAttribute("role", "button");
    element.tabIndex = -1;
    element.addEventListener("click", func);
    element.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            // prevent scrolling from spacebar input
            e.preventDefault();
            e.target.click();
        }
    });
}

function appendBasicTableCell(tableRow, values, pkPrefix) {
    const td = document.createElement("td");
    values.forEach((value) => {
        // the prefix is needed for select2
        const pk = pkPrefix + "-" + value.pk;
        td.appendChild(makePill(value.name, pk));
    });
    tableRow.appendChild(td);
}

function appendEmailCell(tableRow, email) {
    const container = document.createElement("td");
    tableRow.appendChild(container);
    if (!email) {
        return;
    }
    const emailLink = document.createElement("a");
    emailLink.href = "mailto:" + email;
    emailLink.textContent = email;
    emailLink.tabIndex = -1;
    container.appendChild(emailLink);
}

function fillTable(personData) {
    const tableBody = document.querySelector(".persons-table tbody");
    // remove all children
    tableBody.replaceChildren();
    personData.forEach((p) => {
        const tr = document.createElement("tr");
        tr.dataset.pk = p.person.pk;
        emulateButton(tr, makeGraphWrapper);

        const personEl = document.createElement("td");
        const personText = concatTitleName(p.person.title, p.person.name);
        const personPill = makePill(personText, "pers-" + p.person.pk);
        personEl.appendChild(personPill);
        tr.appendChild(personEl);

        appendEmailCell(tr, p.person.email);
        appendBasicTableCell(tr, p.interests, "inte");
        appendBasicTableCell(tr, p.institutes, "inst");
        appendBasicTableCell(tr, p.faculties, "facu");
        appendBasicTableCell(tr, p.departments, "depa");
        // should advisor titles be shown?
        appendBasicTableCell(tr, p.advisors, "advi");
        appendBasicTableCell(tr, p.roles, "role");
        appendBasicTableCell(tr, p.offered, "offe");
        appendBasicTableCell(tr, p.wanted, "want");

        tableBody.appendChild(tr);
    });
    // to enable tabbing into the table
    if (personData.length > 0) {
        tableBody.firstChild.tabIndex = 0;
    }
}

/**
 * handles tabs and arrow key presses in table body
 *
 * left/right switches between the children in a tr.
 * up/down switches between the trs.
 * @param {KeyboardEvent} e
 */
function handleTableFocus(e) {
    switch (e.key) {
        case "ArrowUp":
            changeRowFocus(e, -1);
            break;
        case "ArrowDown":
            changeRowFocus(e, 1);
            break;
        case "ArrowLeft":
            changeRowChildrenFocus(e, -1);
            break;
        case "ArrowRight":
            changeRowChildrenFocus(e, 1);
            break;
        default:
            return;
    }
}

function changeRowFocus(e, direction) {
    const tbody = e.target.closest("tbody");
    const rows = tbody.querySelectorAll("tr");
    const currentRow = document.activeElement.closest("tr");
    const indexCurrentRow = Array.prototype.indexOf.call(rows, currentRow);
    const nextRow = (() => {
        const next = rows[indexCurrentRow + direction];
        // special case in case the activeElement is a child of the first or last row
        return next || rows[direction === -1 ? 0 : rows.length - 1];
    })();
    nextRow.focus();
    e.preventDefault();
}

function changeRowChildrenFocus(e, direction) {
    if (e.target.nodeName === "TR") {
        if (direction === 1) {
            e.target.querySelector("button").focus();
        }
    } else {
        const activeElement = document.activeElement;
        const rowChildren = activeElement.closest("tr").querySelectorAll("button, a");
        const indexActive = Array.prototype.indexOf.call(rowChildren, activeElement);
        const newTarget = rowChildren[indexActive + direction];
        newTarget?.focus();
    }
    e.preventDefault();
}

function initializeTableBody() {
    const tbody = document.querySelector(".persons-table tbody");
    tbody.addEventListener("keydown", handleTableFocus);
    tbody.addEventListener("focusin", (e) => {
        tbody.querySelector("[tabindex='0']").tabIndex = -1;
        // to remember the last focused element in the tbody
        e.target.tabIndex = 0;
    });
}

function initializeSearch() {
    const searchEl = document.querySelector("#search-button");
    searchEl.addEventListener("click", searchAndUpdate);
}

function handleMinimize() {
    // should clicking on backdrop minimize or close?
    // and then could I distinguish between pressing escape and clicking backdrop?
    const minimizeEl = document.querySelector(".btn-close.graph-minimize");
    const maximizeEl = document.querySelector(".graph-maximize");
    if (minimizeEl.dataset.usedMinimize) {
        maximizeEl.classList.remove("d-none");
        delete minimizeEl.dataset.usedMinimize;
    } else {
        maximizeEl.classList.add("d-none");
    }
}

/**
 * update the table data by searching with the search phrases and applying the filters.
 * cached search results may be used
 */
function updateData() {
    const searchEl = document.querySelector("#search-button");
    searchEl.click();
}

function setFocus() {
    // if filters are changed by clicking on graph nodes this won't work
    const target = document.querySelector("tbody > tr[data-last-selected]");
    delete target?.dataset.lastSelected;
    target?.focus();
}

function initializeModal() {
    const modalEl = document.getElementById("graphModal");
    // because this event needs to be triggered before the modal.close it is attached
    // to the modal div and is activated during capture
    modalEl.addEventListener("click", (e) => {
        e.target.dataset.usedMinimize = true;
    }, true);
    modalEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            e.target.click();
        }
    });
    modalEl.addEventListener("hide.bs.modal", handleMinimize);
    modalEl.addEventListener("hidden.bs.modal", setFocus);
}

/**
 * add a new option to the select2. the option is not deleted automatically if it is
 * unselected or not selected
 * @param {String} text
 * @param {Boolean} temporary if true, the option is marked for deletion and not selected
 */
function appendNewOption(text, temporary) {
    const id = temporary ? "temp-" + text : text;
    const newOption = new Option(text, id, false, true);
    $(".search-filter").append(newOption);

    const selections = $(".search-filter").select2("data");
    if (temporary) {
        const valuesForSelectionsWithoutNewOption = selections.filter((element) => element.id !== id)
            .map((element) => element.id);
        $(".search-filter").val(valuesForSelectionsWithoutNewOption);
    }
    // triggers only select2 change to prevent the table/search update happening every time
    $(".search-filter").trigger("change.select2");
}

/**
 * append a new option with the text entered by the user so options with the same text as
 * an existing option can be selected as search phrase
 * @param {InputEvent} e
 * @returns
 */
function updateSearchPhrase(e) {
    const text = e.currentTarget.value.trim();
    // delete the temporary options except the one created from the current input
    const options = document.querySelectorAll(".search-filter > option");
    options.forEach((element) => {
        if (element.value !== "temp-" + text) {
            element.remove();
        }
    });

    if (text === "") {
        return;
    }

    const createdOptions = document.querySelectorAll(".search-filter > option, .search-filter optgroup.search option");
    const optionExists = Array.from(createdOptions)
        .map((element) => element.text.toLowerCase())
        .includes(text.toLowerCase());
    if (optionExists) {
        return;
    }

    appendNewOption(text, true);
}

function appendSearchPhraseToGroup(optionText, optionId) {
    const newOption = new Option(optionText, optionId, false, true);
    // mark the option as search phrase
    newOption.dataset.newTag = true;
    const select = document.querySelector("select.search-filter");
    const optgroup = select.querySelector("optgroup.search");
    optgroup.appendChild(newOption);
    return select;
}

function handleAppendSearchPhraseToGroup(e) {
    const data = e.params.args.data;
    if (!data.id.startsWith("temp-")) {
        return;
    }

    const select = appendSearchPhraseToGroup(data.text, data.text);

    // remove the temp option created after this event
    Array.from(select.querySelectorAll(".search-filter > option"))
        .forEach((element) => element.remove());
    // reinitialize to make select2 recognize the new option in the optgroup
    initializeSelect2(false);
}

function templateResult(item, container) {
    // if I wanted to color the search results, the color of the
    // exclude/highlight states would need to be handled too
    if (item.element) {
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

/**
 * sort select2 results so that the user-created options appear at the top
 * @param {Array} data Array of objects representing options and option groups
 * @returns
 */
function sortResults(data) {
    const optionsOutsideGroups = data.filter((element) => element.children === undefined);
    const groups = data.filter((element) => element.children !== undefined);
    return optionsOutsideGroups.concat(groups);
}

/**
 * initialize select2 and the events. reinitializing would remove all custom properties on the options' select2 objects
 * @param {Boolean} addEvents if the select2 events should be added (to prevent adding them more than once)
 * @returns
 */
function initializeSelect2(addEvents) {
    const $searchFilter = $(".search-filter").select2({
        placeholder: "Select filters or enter search phrases",
        maximumSelectionLength: 20,
        tokenSeparators: [","],
        allowClear: true,
        templateSelection: templateSelection,
        templateResult: templateResult,
        sorter: sortResults,
        debug: true,
        width: "100%",
    });

    // this input (and the event) is destroyed on each reinitialization
    $(".select2-search__field").on("input", updateSearchPhrase);

    if (!addEvents) {
        return;
    }

    $searchFilter.on("change", updateData);

    $searchFilter.on("select2:selecting", handleAppendSearchPhraseToGroup);

    // prevents opening the dropdown after unselecting an item
    $searchFilter.on("select2:unselecting", function () {
        $(this).on("select2:opening", function (ev) {
            ev.preventDefault();
            $(this).off("select2:opening");
        });
    });
}

// after refreshing the page the user should have to search again
// if I don't clear the storage it would show the results of the
// previous search as soon as a search word or filter is entered
sessionStorage.removeItem("personData");

initializeSelect2(true);
initializeTableBody();
initializeSearch();
initializeModal();
initializeClipboardButtons();
loadSharedViewFromHtml();

var graphGlobal = null;
