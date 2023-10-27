"use strict";

import { showAndLogFormErrors, hideFormErrors, showErrorAlert, hideErrorAlert, writeToClipboard } from "./utils.js";

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
    const buttons = form.querySelectorAll("button[type='submit']");
    buttons.forEach((button) => button.disabled = true );
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
    }, 2500);
}

async function submitEdit(postData) {
    const url = "edit";
    const response = await fetch(url, {
        method: "POST",
        body: postData,
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
    const submitter = e.submitter || form.querySelector("button#edit");
    const data = new FormData(form, submitter);

    if (submitter.value === "delete") {
        const message = `Do you want to request the deletion of ${data.get("name")}'s data?`;
        if (!window.confirm(message)) {
            return false;
        }
    }
    hideErrorAlert(form);
    hideFormErrors(form);
    submitEdit(data).catch((error) => {
        showErrorAlert(form, error);
    });
}

function copyPersonId(e) {
    const button = e.currentTarget;
    writeToClipboard(button, async () => {
        const input = document.querySelector("input[name='personId']");
        return input.value;
    });
}

function initCopyButton() {
    const clipboardEl = document.querySelector("button.clipboard-button");
    const nameContainer = document.querySelector("#id_name").parentNode;
    // move it to the name field
    nameContainer.querySelector("label")
        .insertAdjacentElement("afterend", clipboardEl);
    clipboardEl.classList.remove("d-none");
    clipboardEl.addEventListener("click", copyPersonId);
}

// to copy the id of an existing person
if (document.querySelector("input[name='personId']").value) {
    initCopyButton();
}

initMultiSelects();

const form = document.querySelector("form.edit");
form.addEventListener("submit", edit);