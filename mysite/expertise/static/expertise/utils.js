"use strict";

export { showAndLogFormErrors, hideFormErrors, showErrorAlert, hideErrorAlert };

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