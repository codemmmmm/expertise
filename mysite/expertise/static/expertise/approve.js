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

function removeAccordionItem(id) {
    const selector = "#collapse" + id;
    const accordionBody = document.querySelector(selector);
    const accordionItem = accordionBody.closest("div.accordion-item");
    accordionItem.remove();
}

async function submitSubmission(postData) {
    const url = "approve";
    const response = await fetch(url, {
        method: "POST",
        body: postData,
    });
    if (response.ok) {
        const data = await response.json();
        removeAccordionItem(data.id);
        showAlertIfEmpty();
    } else {
        const data = await response.json();
        if (!data.id) {
            // this should only happen if something is bugged
            console.error("The following error response returned without an id: " + data.errors);
            return;
        }
        const form = document.querySelector(`#collapse${data.id} form.approve`);
        const prefix = data.id + "new-";
        showAndLogFormErrors(form, data.errors, prefix, data.id);
        const firstError = document.querySelector("div.invalid-feedback");
        if (firstError) {
            firstError.scrollIntoView();
        }
    }
}

function submit(e) {
    e.preventDefault();
    const form = e.target;
    hideFormErrors(form);
    hideErrorAlert(form);
    const submitter = e.submitter || form.querySelector("button[value='approve'");
    const data = new FormData(form, submitter);
    // TODO: sucess message? / loading spinner
    submitSubmission(data).catch((error) => {
        showErrorAlert(form, error);
    });
}

function initForms() {
    const forms = document.querySelectorAll("form.approve");
    forms.forEach((form) => {
        form.addEventListener("submit", submit);
    });
}

/**
 * show the alert if no accordion item exists
 */
function showAlertIfEmpty() {
    const submissions = document.querySelectorAll("div.accordion-item");
    if (submissions.length === 0) {
        const alert = document.querySelector("div.alert-success.no-todo");
        alert.classList.remove("d-none");
    }
}

initMultiSelects();
initForms();
showAlertIfEmpty();