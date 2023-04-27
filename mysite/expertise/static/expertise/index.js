function formatLabel(item) {
    /**display optgroup before the element for items of some optgroups */
    option = $(item.element);
    optgroup = option.closest('optgroup').attr('label');
    showGroupFor = ["Persons", "Advisors", "Offered expertise", "Wanted expertise"];
    return showGroupFor.includes(optgroup) ? optgroup + ' | ' + item.text : item.text;
};

function createTag(params) {
    var term = $.trim(params.term);
    if (term === '') {
        return null;
    }

    return {
        id: term,
        text: term,
        newTag: true,
    };
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
    // TODO: add spinner on search button
    e.preventDefault();
    // get search parameter
    const selections = $('.search-filter').select2("data");
    const searchSelection = selections.find((element) => element.newTag === true);
    const searchWord = searchSelection === undefined ? "" : searchSelection.text;

    getPersons(searchWord).then((data) => {
        if (data === undefined) {
            // set the sessionStorage to empty array to prevent other actions
            // possibly using outdated search results
            sessionStorage.setItem("persons", JSON.stringify([]));
            updateAlert(null);
            return;
        }
        const persons = data.persons;
        //console.log(persons);
        sessionStorage.setItem("persons", JSON.stringify(persons));
        // persons list should be filtered first
        fillTable(persons);
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

function drawGraph(data) {
    console.log("drawing");

    var nodes = new vis.DataSet([
        { id: 1, label: "Max Muster" },
        { id: 2, label: "Jana Schuster von Grafhausen die Dritte" },
        { id: 3, label: "NLP" },
        { id: 4, label: "TU Dresden" },
        { id: 5, label: "Prof. Hagel" },
    ]);

    var edges = new vis.DataSet([
        { from: 1, to: 3, label: "WANTS" },
        { from: 2, to: 3, label: "OFFERS" },
        { from: 1, to: 2, label: "ADVISED_BY"},
        { from: 2, to: 4, label: "MEMBER_OF" },
        { from: 5, to: 4, label: "MEMBER_OF" },
    ]);

    var container = document.querySelector("#graph");
    var data = {
        nodes: nodes,
        edges: edges,
    };

    var options = {
        nodes: {
            widthConstraint: {
                maximum: 200,
            },
        },
        edges: {
            arrows: "to",
            smooth: true,
        },
        physics: {
            barnesHut: {
                springConstant: 0.04,
                // avoidOverlap: 0.1,
                springLength: 250,
                // gravitationalConstant: -3000,
            },
        },
    };
    var network = new vis.Network(container, data, options);
    container.classList.remove("d-none");
    const networkEl = document.querySelector(".vis-network");
    networkEl.classList.add("border", "border-info");
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
        drawGraph(graphData);
        // TODO: maybe jump to drawn graph
    });
}

function concatTitleName(title, name) {
    return title === "" ? name : title + " " + name;
}

function appendBasicTableCell(tableRow, values) {
    // TODO: add line breaks after each entry?
    td = document.createElement("td");
    td.textContent = values.join(", ");
    tableRow.appendChild(td);
}

function fillTable(persons) {
    const tableBody = document.querySelector(".persons-table tbody");
    // remove all children
    tableBody.replaceChildren();
    persons.forEach((p) => {
        const tr = document.createElement("tr");
        tr.dataset.pk = p.person.pk;
        personEl = document.createElement("td");
        personEl.textContent = concatTitleName(p.person.title, p.person.name);
        tr.appendChild(personEl);

        emailEl = document.createElement("td");
        emailLink = document.createElement("a");
        emailLink.href = "mailto:" + p.person.email;
        emailLink.textContent = p.person.email;
        emailEl.appendChild(emailLink);
        tr.appendChild(emailEl);

        appendBasicTableCell(tr, p.interests);
        appendBasicTableCell(tr, p.institutes);
        appendBasicTableCell(tr, p.faculties);
        appendBasicTableCell(tr, p.departments);
        appendBasicTableCell(tr, p.advisors);
        appendBasicTableCell(tr, p.roles);
        appendBasicTableCell(tr, p.offered);
        appendBasicTableCell(tr, p.wanted);

        tr.addEventListener("click", makeGraph);
        // TODO: maybe add role=button to table row
        tableBody.appendChild(tr);
    });
}

// TODO: add an eventListener which prevents adding more than 1 new search word

// TODO: maybe add a property that saves with category/optgroup it belongs to
// if that is necessary
// TODO: I think the primary key of the entities should be mapped so
// select2 knows which the primary key is? probably as value of the option?
$('.search-filter').select2({
    placeholder: "Select filters or enter new value for searching",
    maximumSelectionLength: 20,
    tags: true,
    tokenSeparators: [','],
    allowClear: true,
    templateSelection: formatLabel,
    minimumInputLength: 1, // not sure if this is good
    createTag: createTag,
    debug: true,
    width: "100%",
});

// TODO: remove
// for logging
$('.search-filter').on('select2:select', function (e) {
    data = $('.search-filter').select2("data");
    console.log("all selected elements:");
    data.forEach(element => {
        console.log(element);
    });
});

const searchEl = document.querySelector("#search-button");
searchEl.addEventListener("click", search);
