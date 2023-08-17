"use strict";

import { showAndLogFormErrors, hideFormErrors, showErrorAlert, hideErrorAlert } from "./utils.js";

function initMultiSelects() {
    const config = {
        placeholder: "", // required for allowClear
        maximumSelectionLength: 15,
        tags: true,
        allowClear: true,
        debug: true,
        width: "100%",
    };

    $(".form-select:not(.select2-hidden-accessible)").select2(config);
}

function alertAndRedirect(form) {
    form.onSubmit = (e) => {
        e.preventDefault();
    };
    const button = form.querySelector("button[type='submit']");
    button.disabled = true;
    const container = document.createElement("div");
    const alert = document.createElement("div");
    alert.className = "alert alert-success mt-3 d-inline-block";
    alert.role = "alert";
    alert.textContent = "Your changes were submitted. Redirecting...";
    container.appendChild(alert);
    form.appendChild(container);
    container.scrollIntoView();
    setTimeout(() => {
        window.location.assign("/expertise/");
    }, 3000);
}

async function submitEdit(post_data) {
    const url = "edit-form";
    const response = await fetch(url, {
        method: "POST",
        body: post_data,
    });
    const form = document.querySelector("form.edit");
    if (response.ok) {
        alertAndRedirect(form);
    } else {
        const errors = await response.json();
        showAndLogFormErrors(form, errors);
        const firstError = document.querySelector("div.invalid-feedback");
        if (firstError) {
            firstError.scrollIntoView();
        }
    }
}

function edit(e) {
    e.preventDefault();
    const form = document.querySelector("form.edit");
    const data = new FormData(form);
    hideErrorAlert(form);
    hideFormErrors(form);
    // TODO: sucess message? / loading spinner
    submitEdit(data).catch((error) => {
        showErrorAlert(form, error);
    });
}

function initEdit() {
    const button = document.querySelector("button[type='submit']");
    button.textContent = "Submit for approval";
    const form = document.querySelector("form");
    form.removeEventListener("submit", search);
    form.addEventListener("submit", edit);
}

function copyToClipboard(e) {
    const button = e.currentTarget;
    if (button.dataset.inStartState === "false") {
        return false;
    }
    const input = document.querySelector("input[name='personId']");
    const startTitle = button.title;
    const endTitle = "Copied!";
    const startImage = button.querySelector("svg.bi-clipboard2");
    const endImage = button.querySelector("svg.bi-clipboard2-check");

    // does the site always have permission to write to clipboard in a secure context?
    navigator.clipboard.writeText(input.value);
    button.dataset.inStartState = false;
    button.title = endTitle;
    startImage.classList.add("d-none");
    endImage.classList.remove("d-none");
    setTimeout(() => {
        button.title = startTitle;
        startImage.classList.remove("d-none");
        endImage.classList.add("d-none");
        button.dataset.inStartState = true;
    }, 2000);
}

function initCopyButton() {
    const clipboardEl = document.querySelector("button.clipboard-button");
    const nameContainer = document.querySelector("#id_name").parentNode;
    // move it to the intended position because the full form was loaded
    nameContainer.querySelector("label").insertAdjacentElement("afterend", clipboardEl);
    clipboardEl.classList.remove("d-none");
    clipboardEl.addEventListener("click", copyToClipboard);
}

async function loadFullForm(selectedPerson) {
    const url = "edit-form";
    const form = document.querySelector("form");
    hideErrorAlert(form);
    const response = await fetch(`${url}?id=${encodeURIComponent(selectedPerson.id)}`);
    if (!response.ok) {
        const message = `An error has occured: ${response.status}`;
        throw new Error(message);
    }
    const html = await response.text();
    // TODO: check if XSS is possible, e.g. in title

    const personName = selectedPerson.text;
    form.querySelector("div.person-select").remove();
    form.insertAdjacentHTML("afterbegin", html);
    const nameInput = form.querySelector("input[name='name']");
    nameInput.value ||= personName;
    initMultiSelects();
    initEdit();
    // only enable copy button if the person was already created and thus has an ID
    if (document.querySelector("input[name='personId']").value) {
        initCopyButton();
    }
}

function search(e) {
    e.preventDefault();
    const form = e.target;
    const selection = $("#name").select2("data")[0];
    loadFullForm(selection).catch((error) => {
        showErrorAlert(form, error);
    });
}

function initSearch() {
    document.querySelector("form.edit").addEventListener("submit", search);
}

// TODO: entering a new person with same name as existing entry must be possible
$("#name").select2({
    tags: true,
    width: "100%",
    debug: true,
});

initSearch();