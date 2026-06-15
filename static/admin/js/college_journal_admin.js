(function () {
    "use strict";

    function getCookie(name) {
        const cookie = document.cookie
            .split(";")
            .map((item) => item.trim())
            .find((item) => item.startsWith(`${name}=`));
        return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : "";
    }

    function setupAssignmentDeleteButtons() {
        document.querySelectorAll(".assignment-delete-control").forEach((button) => {
            if (button.dataset.ready === "true") {
                return;
            }
            button.dataset.ready = "true";
            button.addEventListener("click", async () => {
                const confirmed = window.confirm(
                    "Удалить это назначение дисциплины? Связанные занятия, оценки и посещаемость также будут удалены."
                );
                if (!confirmed) {
                    return;
                }

                const response = await fetch(button.dataset.deleteUrl, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCookie("csrftoken"),
                        "X-Requested-With": "XMLHttpRequest",
                    },
                });
                if (response.ok) {
                    window.location.reload();
                    return;
                }
                window.alert("Не удалось удалить назначение.");
            });
        });
    }

    function setupInlineDeleteButtons() {
        document
            .querySelectorAll(".inline-group .tabular thead th.column-DELETE")
            .forEach((heading) => {
                heading.textContent = "Удалить";
            });

        document.querySelectorAll(".inline-related").forEach((row) => {
            const checkbox = row.querySelector(".delete input[type='checkbox']");
            if (!checkbox || checkbox.dataset.ready === "true") {
                return;
            }

            checkbox.dataset.ready = "true";
            checkbox.hidden = true;

            const button = document.createElement("button");
            button.type = "button";
            button.className = "inline-delete-control";
            button.textContent = "×";
            button.title = "Удалить строку";
            button.setAttribute("aria-label", "Удалить строку");
            button.addEventListener("click", () => {
                const confirmed = window.confirm(
                    "Удалить эту запись? Изменение будет применено после сохранения формы."
                );
                if (!confirmed) {
                    return;
                }
                checkbox.checked = true;
                row.classList.add("is-marked-for-delete");
            });
            checkbox.parentElement.appendChild(button);
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        setupAssignmentDeleteButtons();
        setupInlineDeleteButtons();

        document.body.addEventListener("formset:added", setupInlineDeleteButtons);
    });
})();
