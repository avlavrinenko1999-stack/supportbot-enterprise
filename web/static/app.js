const clock = document.querySelector("#clock");
const status = document.querySelector("#status");

function updateClock() {
  clock.textContent = new Intl.DateTimeFormat("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

document.querySelectorAll(".app").forEach((button) => {
  button.addEventListener("click", () => {
    status.textContent = `Раздел «${button.dataset.section}» будет доступен на следующем этапе.`;
  });
});

updateClock();
window.setInterval(updateClock, 30_000);
