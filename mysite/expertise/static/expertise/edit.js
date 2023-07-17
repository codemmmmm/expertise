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
    const alert = form.querySelector("div.alert-danger");
    alert.classList.add("d-none");
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
    loadFullForm(selection.id).catch((error) => {
        showAlert(error);
    });
}

function initializeSearch() {
    document.querySelector("form.edit").addEventListener("submit", search);
}

// TODO: entering a new person with same name as existing entry must be possible
$("#name").select2({
    tags: true,
    //width: "100%",
    debug: true,
});

initializeSearch();