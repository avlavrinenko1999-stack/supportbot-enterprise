(function () {
  "use strict";

  var methods = document.querySelectorAll(".auth-method");
  var index;

  function setOpen(method, open) {
    var button = method.querySelector(".auth-method-toggle");
    var panel = method.querySelector(".auth-method-panel");
    var chevron = method.querySelector(".auth-method-chevron");
    method.className = open ? "auth-method is-open" : "auth-method";
    button.setAttribute("aria-expanded", open ? "true" : "false");
    panel.style.display = open ? "block" : "none";
    chevron.innerHTML = open ? "&#8722;" : "+";
  }

  function toggleMethod(selected) {
    var selectedIsOpen = (" " + selected.className + " ").indexOf(" is-open ") !== -1;
    var itemIndex;
    for (itemIndex = 0; itemIndex < methods.length; itemIndex += 1) {
      setOpen(methods[itemIndex], methods[itemIndex] === selected && !selectedIsOpen);
    }
  }

  for (index = 0; index < methods.length; index += 1) {
    (function (method) {
      var button = method.querySelector(".auth-method-toggle");
      setOpen(method, false);
      button.onclick = function () {
        toggleMethod(method);
      };
    }(methods[index]));
  }
}());
