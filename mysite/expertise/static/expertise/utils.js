"use strict";

export { showAndLogFormErrors, hideFormErrors, showErrorAlert, hideErrorAlert, writeToClipboard };

/**
 *
 * @param {HTMLFormElement} form
 * @param {Object} errors
 * @param {String} prefix for field names
 * @param {Number} id
 */
function showAndLogFormErrors(form, errors, prefix = "", id) {
    for (const [key, fieldErrors] of Object.entries(errors)) {
        const getInputEl = (fieldName) => {
            if (fieldName === "__all__") {
                return form.querySelector("button[type='submit']");
            } else {
                return form.querySelector(`[name="${prefix + key}"]`);
            }
        };
        const inputEl = getInputEl(key);
        inputEl.classList.add("is-invalid");
        const parentEl = inputEl.parentNode;
        fieldErrors.forEach((error) => {
            const feedback = document.createElement("div");
            feedback.className = "invalid-feedback";
            feedback.textContent = error.message;
            parentEl.appendChild(feedback);

            if (error.exception) {
                console.error(`Error for submission with id ${id}: ${error.exception}`);
            }
        });
    }
}

/**
 *
 * @param {HTMLFormElement} form
 */
function hideFormErrors(form) {
    const inputs = form.querySelectorAll(".is-invalid");
    inputs.forEach((input) => {
        input.classList.remove("is-invalid");
    });
    const feedbackMessages = form.querySelectorAll("div.invalid-feedback");
    feedbackMessages.forEach((message) => {
        message.remove();
    });
}

/**
 *
 * @param {HTMLElement} parent the element where the alert will be appended
 * @param {String} error
 */
function showErrorAlert(parent, error) {
    const container = document.createElement("div");
    const alert = document.createElement("div");
    alert.className = "alert alert-danger mt-3 d-inline-block";
    alert.role = "alert";
    alert.textContent = error.message;
    container.appendChild(alert);
    parent.appendChild(container);
}

/**
 *
 * @param {HTMLElement} parent
 */
function hideErrorAlert(parent) {
    const alertContainer = parent.querySelector("div.alert-danger")?.parentNode;
    if (alertContainer) {
        alertContainer.remove();
    }
}

/**
 * handles switching the clipboard image and info and writing to the clipboard
 * @param {HTMLButtonElement} button
 * @param {Function} getValue has to return a Promise resolving to a string
 */
function writeToClipboard(button, getValue) {
    if (button.dataset.inStartState === "false") {
        return false;
    }
    const startTitle = button.title;
    const endTitle = "Copied!";
    const startImage = button.querySelector("svg.bi-clipboard2");
    const endImage = button.querySelector("svg.bi-clipboard2-check");

    // does the site always have permission to write to clipboard in a secure context?
    getValue()
        .then((data) => {
            navigator.clipboard.writeText(data);
        })
        .catch((error) => {
            navigator.clipboard.writeText("");
            console.error(error);
        });

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