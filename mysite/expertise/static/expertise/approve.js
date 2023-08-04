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

initMultiSelects();