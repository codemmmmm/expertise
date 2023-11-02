/*global G6, bootstrap*/
"use strict";

import { writeToClipboard, matcher } from "./utils.js";

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
    // I had a bug where the cookie was set twice in firefox and the
    // wrong cookie was chosen for the request
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
        updateTable(tableData, searchPhrases);
        document.querySelector(".persons-table-container").classList.remove("d-none");
        document.querySelector("button.clipboard-button.filters").classList.remove("d-none");
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
            updateTable(searchResults, searchPhrases);
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
        updateTable(data.persons, searchPhrases);
        document.querySelector(".persons-table-container").classList.remove("d-none");
        // to show it only after the first search
        document.querySelector("button.clipboard-button.filters").classList.remove("d-none");
    });
}

function updateTable(personData, searchPhrases) {
    const filteredPersonData = filterPersonData(personData);
    fillTable(filteredPersonData);
    updateAlert(personData.length, filteredPersonData.length);
    highlightSearchPhrases(searchPhrases);
}

/**
 *
 * @param {Array.<String>} searchPhrases
 * @returns
 */
function highlightSearchPhrases(searchPhrases) {
    if (!searchPhrases.length) {
        return;
    }

    const table = document.querySelector("table.persons-table");
    // 1st, 2nd and 7th column is excluded because their contents
    // weren't searched on backend at the time of writing
    const nodes = table.querySelectorAll("\
        td:nth-child(3) > .pill,\
        td:nth-child(4) > .pill,\
        td:nth-child(5) > .pill,\
        td:nth-child(6) > .pill,\
        td:nth-child(8) > .pill,\
        td:nth-child(9) > .pill,\
        td:nth-child(10) > .pill"
    );
    searchPhrases = searchPhrases.map((phrase) => phrase.toLowerCase());
    nodes.forEach((node) => {
        const ranges = [];
        const nodeText = node.textContent.toLowerCase();
        searchPhrases.forEach((searchPhrase) => {
            let start = 0;
            let foundAt = nodeText.indexOf(searchPhrase, start);
            while (foundAt > -1) {
                ranges.push({
                    start: foundAt,
                    end: foundAt + searchPhrase.length - 1, // index of the last character to include
                });
                start = foundAt + 1;
                foundAt = nodeText.indexOf(searchPhrase, start);
            }
        });

        if (!ranges.length) {
            return;
        }
        const mergedRanges = mergeSubstringRanges(ranges);
        highlightSubstrings(node, mergedRanges);
    });
}

/**
 *
 * @param {Array.<Object>} ranges is sorted and guaranteed to not be empty
 */
function mergeSubstringRanges(ranges) {
    ranges.sort((a, b) => a.start - b.start);
    const mergedRanges = [ranges[0]];

    for (let i = 1; i < ranges.length; i++) {
        const current = ranges[i];
        const previous = mergedRanges[mergedRanges.length - 1];

        if (current.start <= previous.end) {
            previous.end = Math.max(previous.end, current.end);
        } else {
            mergedRanges.push(current);
        }
    }

    return mergedRanges;
}

/**
 *
 * @param {HTMLElement} node
 * @param {Array.<Object>} mergedRanges
 */
function highlightSubstrings(node, mergedRanges) {
    const text = node.textContent;
    // remove the text nodes
    node.textContent = "";
    let currentIndex = 0;

    mergedRanges.forEach((range) => {
        const unhighlighted = text.substring(currentIndex, range.start);
        if (unhighlighted.length) {
            node.appendChild(document.createTextNode(unhighlighted));
        }

        const highlighted = text.substring(range.start, range.end + 1);
        const span = document.createElement("span");
        span.classList.add("highlight");
        span.textContent = highlighted;
        node.appendChild(span);

        currentIndex = range.end + 1;
    });

    // add remaining text
    const unhighlighted = text.substring(currentIndex);
    if (unhighlighted.length) {
        node.appendChild(document.createTextNode(unhighlighted));
    }
}

function updateAlert(searchedLength, filteredLength) {
    const alertEl = document.querySelector(".search-alert");
    alertEl.classList.remove("d-none");
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
 * @param {String} containerId
 * @param {HTMLElement} container
 * @returns {string} name of the person that the graph is about
 */
function drawG6Graph(apiData, containerId, container){
    const data = prepareGraphData(apiData);
    // make parallel edges draw properly
    G6.Util.processParallelEdges(data.edges);

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
    const networkEl = container.querySelector("svg, canvas");
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
    const nodeName = e.target.nodeName;
    if (nodeName === "svg" || nodeName === "path" || nodeName === "A") {
        return false;
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
            const errorEl = document.querySelector(".graph-alert");
            errorEl.classList.remove("d-none");
            errorEl.textContent = error.message;
            const helpEl = document.querySelector(".graph-helptext");
            helpEl.classList.add("d-none");
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
    const elements = document.querySelectorAll("\
        #graph-container > svg, \
        #graph-container > canvas, \
        span.error \
    ");
    elements.forEach((element) => element.remove());
    const errorEl = document.querySelector(".graph-alert");
    errorEl.classList.add("d-none");
    const helpEl = document.querySelector(".graph-helptext");
    helpEl.classList.remove("d-none");
}

function groupFilters(filters, id) {
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
 * @param {Array} personData
 */
function filterPersonData(personData) {
    const selections = $(".search-filter").select2("data");
    // excluding the user created selections here is only necessary
    // because a user might create a tag with e.g. the value "inst-xxx"
    const filters = selections.filter((element) => element.element.dataset.newTag !== "true");

    // group the filters by category
    // the id is the key prepended to the suggestions in the Django template
    const personFilters = groupFilters(filters, "pers");
    const interestsFilters = groupFilters(filters, "inte");
    const institutesFilters = groupFilters(filters, "inst");
    const facultiesFilters = groupFilters(filters, "facu");
    const departmentsFilters = groupFilters(filters, "depa");
    const rolesFilters = groupFilters(filters, "role");
    const advisorsFilters = groupFilters(filters, "advi");
    const offeredFilters = groupFilters(filters, "offe");
    const wantedFilters = groupFilters(filters, "want");

    // filters of different categories are generally connected by AND
    // the persons/advisors and offered/wanted expertise categories use OR
    const filtered = personData.filter((entry) => {
        const matchingPersons = isMatchingPerson(personFilters, entry.person, true) ||
            isMatching(advisorsFilters, entry.advisors, true) ||
            (personFilters.length === 0 && advisorsFilters.length === 0);
        const matchingExpertise = isMatching(offeredFilters, entry.offered, true) ||
            isMatching(wantedFilters, entry.wanted, true) ||
            (offeredFilters.length === 0 && wantedFilters.length === 0);

        return matchingPersons &&
            isMatching(interestsFilters, entry.interests) &&
            isMatching(institutesFilters, entry.institutes) &&
            isMatching(facultiesFilters, entry.faculties) &&
            isMatching(departmentsFilters, entry.departments) &&
            isMatching(rolesFilters, entry.roles) &&
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
    toggleSelection(e.currentTarget.dataset.pk);
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

function appendEditCell(tableRow, person) {
    const container = document.createElement("td");
    tableRow.appendChild(container);
    const editLink = document.createElement("a");
    editLink.classList.add("pe-2", "pb-2", "me-3");
    editLink.href = "edit?person=" + person.pk;
    editLink.target = "_blank";
    editLink.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-pencil-square" viewBox="0 0 16 16">
        <path d="M15.502 1.94a.5.5 0 0 1 0 .706L14.459 3.69l-2-2L13.502.646a.5.5 0 0 1 .707 0l1.293 1.293zm-1.75 2.456-2-2L4.939 9.21a.5.5 0 0 0-.121.196l-.805 2.414a.25.25 0 0 0 .316.316l2.414-.805a.5.5 0 0 0 .196-.12l6.813-6.814z"/>
        <path fill-rule="evenodd" d="M1 13.5A1.5 1.5 0 0 0 2.5 15h11a1.5 1.5 0 0 0 1.5-1.5v-6a.5.5 0 0 0-1 0v6a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5v-11a.5.5 0 0 1 .5-.5H9a.5.5 0 0 0 0-1H2.5A1.5 1.5 0 0 0 1 2.5v11z"/>
        </svg>`;

    // to prevent the cell from being tabbed to when only the arrow keys should be used
    editLink.tabIndex = -1;
    container.appendChild(editLink);
}

function appendEmailCell(tableRow, email) {
    const container = document.createElement("td");
    tableRow.appendChild(container);
    if (!email) {
        return;
    }
    const emailLink = document.createElement("a");
    emailLink.classList.add("ps-1", "pb-2");
    emailLink.href = "mailto:" + email;
    emailLink.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-envelope-at" viewBox="0 0 16 16">
        <path d="M2 2a2 2 0 0 0-2 2v8.01A2 2 0 0 0 2 14h5.5a.5.5 0 0 0 0-1H2a1 1 0 0 1-.966-.741l5.64-3.471L8 9.583l7-4.2V8.5a.5.5 0 0 0 1 0V4a2 2 0 0 0-2-2H2Zm3.708 6.208L1 11.105V5.383l4.708 2.825ZM1 4.217V4a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v.217l-7 4.2-7-4.2Z"/>
        <path d="M14.247 14.269c1.01 0 1.587-.857 1.587-2.025v-.21C15.834 10.43 14.64 9 12.52 9h-.035C10.42 9 9 10.36 9 12.432v.214C9 14.82 10.438 16 12.358 16h.044c.594 0 1.018-.074 1.237-.175v-.73c-.245.11-.673.18-1.18.18h-.044c-1.334 0-2.571-.788-2.571-2.655v-.157c0-1.657 1.058-2.724 2.64-2.724h.04c1.535 0 2.484 1.05 2.484 2.326v.118c0 .975-.324 1.39-.639 1.39-.232 0-.41-.148-.41-.42v-2.19h-.906v.569h-.03c-.084-.298-.368-.63-.954-.63-.778 0-1.259.555-1.259 1.4v.528c0 .892.49 1.434 1.26 1.434.471 0 .896-.227 1.014-.643h.043c.118.42.617.648 1.12.648Zm-2.453-1.588v-.227c0-.546.227-.791.573-.791.297 0 .572.192.572.708v.367c0 .573-.253.744-.564.744-.354 0-.581-.215-.581-.8Z"/>
        </svg>`;
    // to prevent the cell from being tabbed to when only the arrow keys should be used
    emailLink.tabIndex = -1;
    container.appendChild(emailLink);
}

function fillTable(personData) {
    const tableBody = document.querySelector(".persons-table tbody");
    // remove all children
    tableBody.replaceChildren();
    personData.forEach((entry) => {
        const tr = document.createElement("tr");
        tr.dataset.pk = entry.person.pk;
        emulateButton(tr, makeGraphWrapper);

        appendEmailCell(tr, entry.person.email);

        const personEl = document.createElement("td");
        const personText = concatTitleName(entry.person.title, entry.person.name);
        const personPill = makePill(personText, "pers-" + entry.person.pk);
        personEl.appendChild(personPill);
        tr.appendChild(personEl);

        appendBasicTableCell(tr, entry.interests, "inte");
        appendBasicTableCell(tr, entry.institutes, "inst");
        appendBasicTableCell(tr, entry.faculties, "facu");
        appendBasicTableCell(tr, entry.departments, "depa");
        // should advisor titles be shown?
        appendBasicTableCell(tr, entry.advisors, "advi");
        appendBasicTableCell(tr, entry.roles, "role");
        appendBasicTableCell(tr, entry.offered, "offe");
        appendBasicTableCell(tr, entry.wanted, "want");

        appendEditCell(tr, entry.person);

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
            e.target.querySelector("button, a").focus();
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
    select.focus();
    // prevent the dropdown opening because of the manual re-focus
    $(".search-filter").on("select2:opening", (e) => e.preventDefault());
    // restore dropdown opening functionality
    setTimeout(() => $(".search-filter").off("select2:opening"), 100);
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
        selectionCssClass: "search-filter-select2",
        templateSelection: templateSelection,
        templateResult: templateResult,
        matcher: matcher,
        sorter: sortResults,
        debug: true,
        width: "100%",
    });

    // this input (and the event) is destroyed on each reinitialization
    $(".select2-search__field").on("input", updateSearchPhrase);

    if (!addEvents) {
        return;
    }

    $searchFilter.on("change", () => {
        const searchEl = document.querySelector("#search-button");
        searchEl.click();
    });

    $searchFilter.on("select2:selecting", handleAppendSearchPhraseToGroup);

    // prevents opening the dropdown after unselecting an item
    $searchFilter.on("select2:unselecting", function () {
        $(this).on("select2:opening", function (e) {
            e.preventDefault();
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
