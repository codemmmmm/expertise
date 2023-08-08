"use strict";

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

async function submitSubmission(post_data) {
    // TODO: only allow submit if all errors (not alerts) are gone?
    // remove error after the respective input was changed

    //hideErrors();
    const url = "approve";
    const response = await fetch(url, {
        method: "POST",
        body: post_data,
    });
    if (response.ok) {
        console.log("SUCCESS");
    } else {
        const errors = await response.json();
        //showErrors(errors);
        const firstError = document.querySelector("div.invalid-feedback");
        if (firstError) {
            firstError.scrollIntoView();
        }
    }
}

function submit(e) {
    e.preventDefault();
    const form = e.target;
    const submitter = e.submitter || form.querySelector("button[value='approve'");
    const data = new FormData(form, submitter);
    // TODO: sucess message? / loading spinner
    submitSubmission(data).catch((error) => {
        //showAlert(error);
        console.log(error);
    });
}

function initForms() {
    const forms = document.querySelectorAll("form.approve");
    forms.forEach((form) => {
        form.addEventListener("submit", submit);
    });
}

initMultiSelects();
initForms();