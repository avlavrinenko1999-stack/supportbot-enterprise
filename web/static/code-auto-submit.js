(function () {
  "use strict";

  function numericCode(input) {
    return /^\d{6}$/.test(input.value.trim());
  }

  function submitWhenComplete(form, changedInput) {
    if (form.dataset.codeSubmitting === "true") return;

    var inputs = Array.prototype.slice.call(
      form.querySelectorAll("[data-auto-code]")
    );
    var currentIndex = inputs.indexOf(changedInput);

    if (!numericCode(changedInput)) return;

    var nextIncomplete = inputs.slice(currentIndex + 1).find(function (input) {
      return !numericCode(input);
    });
    if (nextIncomplete) {
      nextIncomplete.focus();
      return;
    }

    if (!inputs.every(numericCode) || !form.checkValidity()) return;

    form.dataset.codeSubmitting = "true";
    inputs.forEach(function (input) {
      input.readOnly = true;
      input.setAttribute("aria-busy", "true");
    });
    form.requestSubmit();
  }

  document.querySelectorAll("[data-auto-code-form]").forEach(function (form) {
    form.querySelectorAll("[data-auto-code]").forEach(function (input) {
      input.addEventListener("input", function () {
        if (!input.hasAttribute("data-allow-recovery-code")) {
          input.value = input.value.replace(/\D/g, "").slice(0, 6);
        }
        submitWhenComplete(form, input);
      });
    });

    form.addEventListener("submit", function (event) {
      if (form.dataset.codeSubmitting === "true") return;
      if (!form.checkValidity()) {
        event.preventDefault();
        form.reportValidity();
      }
    });
  });
}());
