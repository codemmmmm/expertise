"use strict";

function initMultiSelects() {
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

function hideErrors() {
    const alert = document.querySelector("div.alert-danger");
    alert.classList.add("d-none");
    const inputs = document.querySelectorAll(".is-invalid");
    inputs.forEach((input) => {
        input.classList.remove("is-invalid");
    });
    const feedbackMessages = document.querySelectorAll("div.invalid-feedback");
    feedbackMessages.forEach((element) => {
        element.remove();
    });
}

function showErrors(errors) {
    for (const [key, messages] of Object.entries(errors)) {
        const getInputEl = (fieldName) => {
            if (fieldName === "__all__") {
                return document.querySelector("button[type='submit']");
            } else {
                return document.querySelector(`[name="${key}"]`);
            }
        };
        const inputEl = getInputEl(key);
        inputEl.classList.add("is-invalid");
        const parentEl = inputEl.parentNode;
        messages.forEach((error) => {
            const feedback = document.createElement("div");
            feedback.className = "invalid-feedback";
            feedback.textContent = error.message;
            parentEl.appendChild(feedback);
        });
    }
}

async function submitEdit(post_data) {
    // TODO: only allow submit if all errors (not alerts) are gone?
    // remove error after the respective input was changed

    hideErrors();
    const url = "edit-form";
    const response = await fetch(url, {
        method: "POST",
        body: post_data,
    });
    if (response.ok) {
        window.location.assign("/expertise/");
    } else {
        const errors = await response.json();
        showErrors(errors);
        const firstError = document.querySelector("div.invalid-feedback");
        if (firstError) {
            firstError.scrollIntoView();
        }
    }
}

function showAlert(error) {
    const alert = document.querySelector("div.alert-danger");
    alert.classList.remove("d-none");
    alert.textContent = error.message;
}

function edit(e) {
    e.preventDefault();
    const form = document.querySelector("form.edit");
    const data = new FormData(form);
    // TODO: sucess message? / loading spinner
    submitEdit(data).catch((error) => {
        showAlert(error);
    });
}

function initEdit() {
    const button = document.querySelector("button[type='submit']");
    button.textContent = "Edit";
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
    const alert = form.querySelector("div.alert-danger");
    alert.classList.add("d-none");
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
    const selection = $("#name").select2("data")[0];
    loadFullForm(selection).catch((error) => {
        showAlert(error);
    });
}

function initSearch() {
    document.querySelector("form.edit").addEventListener("submit", search);
}

// TODO: entering a new person with same name as existing entry must be possible
$("#name").select2({
    tags: true,
    //width: "100%",
    debug: true,
});

initSearch();