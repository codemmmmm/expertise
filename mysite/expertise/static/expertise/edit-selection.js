"use strict";

function loadEditor(e) {
    e.preventDefault();
    const selection = $("#name").select2("data")[0];
    window.location.href = `edit?person=${encodeURIComponent(selection.id)}`;
}

// TODO: entering a new person with same name as existing entry should be possible
$("#name").select2({
    tags: true,
    width: "100%",
    debug: true,
});

document.querySelector("form.edit").addEventListener("submit", loadEditor);