"use strict";

function initializeMultiSelects() {
    const config = {
        placeholder: "", // required for allowClear
        maximumSelectionLength: 15,
        tags: true,
        allowClear: true,
        debug: true,
        //width: "100%",
    };

    $(".form-select:not(.select2-hidden-accessible)").select2(config);
}

async function submitEdit(post_data) {
    const url = "edit-form";
    const response = await fetch(url, {
        method: "POST",
        body: post_data,
    });
    console.log(response.status);
    if (!response.ok) {
        const message = `An error has occured: ${response.status}`;
        throw new Error(message);
    }
    // TODO: handle errors here
    //const data = await response.json();
    window.location.assign("/expertise/");
}

function edit(e) {
    e.preventDefault();
    const form = document.querySelector("form.edit");
    const data = new FormData(form);
    console.log(data);
    submitEdit(data).catch((error) => console.log(error.message));
}

function initializeEdit() {
    const button = document.querySelector("button[type='submit']");
    button.textContent = "Edit";
    const form = document.querySelector("form");
    form.removeEventListener("submit", search);
    form.addEventListener("submit", edit);
}

async function loadFullForm(parameter) {
    const url = "edit-form";
    const form = document.querySelector("form");
    // TODO: error handling
    const response = await fetch(`${url}?id=${encodeURIComponent(parameter)}`);
    if (!response.ok) {
        const message = `An error has occured: ${response.status}`;
        throw new Error(message);
    }
    const html = await response.text();
    // TODO: check if XSS is possible

    // insert after name input
    form.firstElementChild.insertAdjacentHTML("afterend", html);
    initializeMultiSelects();
    initializeEdit();
}

function search(e) {
    e.preventDefault();
    const selection = $("#name").select2("data")[0];
    loadFullForm(selection.id).catch((error) => console.log(error.message));
}

function initializeSearch() {
    document.querySelector("form.edit").addEventListener("submit", search);
}

// TODO: entering a new person with same name as existing entry is necessary
$("#name").select2({
    tags: true,
    //width: "100%",
    debug: true,
});

initializeSearch();