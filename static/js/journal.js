(function () {
    "use strict";

    let activeField = null;
    const saveTimers = new WeakMap();
    const choices = {
        numeric: [
            ["2", "2"],
            ["3", "3"],
            ["4", "4"],
            ["5", "5"],
        ],
        pass_fail: [
            ["З", "Зачёт"],
            ["НЗ", "Незачёт"],
        ],
        attendance: [
            ["Н", "Н"],
            ["У", "У"],
            ["О", "О"],
        ],
    };

    function columnFields(field) {
        return Array.from(
            document.querySelectorAll(
                `[data-journal-field="${field.dataset.journalField}"]` +
                `[data-lesson="${field.dataset.lesson}"]`
            )
        );
    }

    function focusRelative(field, offset) {
        const fields = columnFields(field);
        const index = fields.indexOf(field);
        const target = fields[index + offset];
        if (target) {
            target.focus();
            target.select();
        }
    }

    function normalizeGrade(field) {
        if (field.dataset.gradingScheme === "pass_fail") {
            const value = field.value.trim().toLowerCase();
            const results = {
                "з": "З",
                "зач": "З",
                "p": "З",
                "н": "НЗ",
                "нз": "НЗ",
                "незач": "НЗ",
                "f": "НЗ",
            };
            field.value = results[value] || "";
            return;
        }
        field.value = field.value.replace(/[^2-5]/g, "").slice(0, 1);
    }

    function normalizeAttendance(field) {
        const marks = {
            n: "Н",
            u: "У",
            o: "О",
            "н": "Н",
            "у": "У",
            "о": "О",
        };
        const value = field.value.trim().toLowerCase();
        field.value = marks[value] || "";
    }

    function setAutosaveStatus(message, state) {
        const status = document.querySelector("[data-autosave-status]");
        if (!status) {
            return;
        }
        status.textContent = message;
        status.classList.remove("is-saving", "is-saved", "is-error");
        if (state) {
            status.classList.add(`is-${state}`);
        }
    }

    function getCsrfToken() {
        return document.querySelector(
            ".journal-edit-form input[name='csrfmiddlewaretoken']"
        )?.value || "";
    }

    function updateStudentMetrics(field, data) {
        const studentId = field.dataset.student;
        const averageCell = document.querySelector(
            `[data-average-for="${studentId}"]`
        );
        const absenceCell = document.querySelector(
            `[data-absence-for="${studentId}"]`
        );
        if (averageCell) {
            averageCell.innerHTML = data.average === null
                ? "—"
                : `<strong>${data.average}</strong>`;
        }
        if (absenceCell) {
            absenceCell.textContent = data.absence_count;
        }
    }

    function fieldRequiresReason(field) {
        const isInitialAttendance = (
            field.dataset.journalField === "attendance" &&
            ["", "present"].includes(field.dataset.originalValue)
        );
        return (
            field.dataset.originalExists === "true" &&
            !isInitialAttendance &&
            field.value !== field.dataset.originalValue
        );
    }

    function getChangeReason(form) {
        const reasonSelect = form?.querySelector("[data-change-reason-select]");
        if (!reasonSelect) {
            return "";
        }
        if (reasonSelect.value === "__other__") {
            return form.querySelector("[data-change-reason-other]")?.value.trim() || "";
        }
        return reasonSelect.value.trim();
    }

    function updateOtherReasonField(form) {
        const reasonSelect = form?.querySelector("[data-change-reason-select]");
        const otherField = form?.querySelector("[data-other-reason-field]");
        const otherInput = form?.querySelector("[data-change-reason-other]");
        if (!reasonSelect || !otherField || !otherInput) {
            return;
        }
        const showOther = reasonSelect.value === "__other__";
        otherField.hidden = !showOther;
        otherInput.required = showOther && !form.querySelector("[data-audit-panel]")?.hidden;
    }

    function updateAuditPanel(form) {
        const panel = form?.querySelector("[data-audit-panel]");
        const reasonSelect = form?.querySelector("[data-change-reason-select]");
        if (!panel || !reasonSelect) {
            return false;
        }
        const fields = form.querySelectorAll(
            "[data-journal-field], [data-audit-field]"
        );
        const reasonRequired = Array.from(fields).some(fieldRequiresReason);
        panel.hidden = !reasonRequired;
        reasonSelect.required = reasonRequired;
        updateOtherReasonField(form);
        return reasonRequired;
    }

    async function saveField(field) {
        const form = field.closest(".journal-edit-form");
        if (!form?.dataset.autosaveUrl) {
            return;
        }
        const reason = getChangeReason(form);
        const comment = form.querySelector("[name='change_comment']")?.value.trim();
        if (fieldRequiresReason(field) && !reason) {
            updateAuditPanel(form);
            setAutosaveStatus("Укажите основание", "error");
            const reasonField = form.querySelector("[data-change-reason-select]")?.value === "__other__"
                ? form.querySelector("[data-change-reason-other]")
                : form.querySelector("[data-change-reason-select]");
            reasonField?.focus();
            return;
        }

        setAutosaveStatus("Сохранение…", "saving");
        const body = new URLSearchParams({
            student_id: field.dataset.student,
            lesson_id: field.dataset.lesson,
            field: field.dataset.journalField,
            value: field.value,
            reason: reason || "",
            comment: comment || "",
            original_exists: fieldRequiresReason(field) ? "true" : "false",
        });

        try {
            const response = await fetch(form.dataset.autosaveUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": getCsrfToken(),
                    "X-Requested-With": "XMLHttpRequest",
                },
                body,
            });
            const data = await response.json();
            if (!response.ok) {
                if (data.reason_required) {
                    updateAuditPanel(form);
                    form.querySelector("[data-change-reason-select]")?.focus();
                }
                throw new Error(data.error || "Autosave failed");
            }
            updateStudentMetrics(field, data);
            setAutosaveStatus("Сохранено", "saved");
        } catch (error) {
            setAutosaveStatus("Ошибка сохранения", "error");
        }
    }

    function scheduleAutosave(field) {
        const previousTimer = saveTimers.get(field);
        if (previousTimer) {
            window.clearTimeout(previousTimer);
        }
        const timer = window.setTimeout(() => saveField(field), 180);
        saveTimers.set(field, timer);
    }

    function updateAttendanceCell(field) {
        const cell = field.closest(".lesson-cell");
        if (!cell) {
            return;
        }
        cell.classList.remove("is-absent", "is-excused", "is-late");
        if (field.value === "Н") {
            cell.classList.add("is-absent");
        } else if (field.value === "У") {
            cell.classList.add("is-excused");
        } else if (field.value === "О") {
            cell.classList.add("is-late");
        }
    }

    function getPopover() {
        let popover = document.querySelector(".journal-choice-popover");
        if (popover) {
            return popover;
        }

        popover = document.createElement("div");
        popover.className = "journal-choice-popover";
        popover.hidden = true;
        popover.setAttribute("role", "dialog");
        popover.setAttribute("aria-label", "Выбор значения");
        document.body.appendChild(popover);
        return popover;
    }

    function closePopover() {
        const popover = getPopover();
        popover.hidden = true;
        activeField = null;
    }

    function setFieldValue(value) {
        if (!activeField) {
            return;
        }
        activeField.value = value;
        if (activeField.dataset.journalField === "attendance") {
            updateAttendanceCell(activeField);
        }
        activeField.dispatchEvent(new Event("change", { bubbles: true }));
        scheduleAutosave(activeField);
        activeField.focus();
        closePopover();
    }

    function positionPopover(popover, field) {
        const rect = field.getBoundingClientRect();
        const popoverWidth = popover.offsetWidth;
        const popoverHeight = popover.offsetHeight;
        const gap = 6;
        let left = rect.left + rect.width / 2 - popoverWidth / 2;
        let top = rect.bottom + gap;

        left = Math.max(8, Math.min(left, window.innerWidth - popoverWidth - 8));
        if (top + popoverHeight > window.innerHeight - 8) {
            top = rect.top - popoverHeight - gap;
        }

        popover.style.left = `${left}px`;
        popover.style.top = `${Math.max(8, top)}px`;
    }

    function openPopover(field) {
        activeField = field;
        const popover = getPopover();
        popover.replaceChildren();

        const choiceGroup = field.dataset.journalField === "grade"
            ? field.dataset.gradingScheme
            : "attendance";
        choices[choiceGroup].forEach(([value, label]) => {
            const button = document.createElement("button");
            button.type = "button";
            button.textContent = label;
            if (choiceGroup === "pass_fail") {
                button.classList.add("wide-choice");
            }
            button.setAttribute("aria-label", `Выбрать ${label}`);
            button.addEventListener("mousedown", (event) => {
                event.preventDefault();
            });
            button.addEventListener("click", () => setFieldValue(value));
            popover.appendChild(button);
        });

        const clearButton = document.createElement("button");
        clearButton.type = "button";
        clearButton.className = "clear-choice";
        clearButton.textContent = "—";
        clearButton.setAttribute("aria-label", "Очистить значение");
        clearButton.addEventListener("mousedown", (event) => {
            event.preventDefault();
        });
        clearButton.addEventListener("click", () => setFieldValue(""));
        popover.appendChild(clearButton);

        popover.hidden = false;
        positionPopover(popover, field);
    }

    function setupJournalKeyboard() {
        document.querySelectorAll("[data-journal-field]").forEach((field) => {
            field.addEventListener("focus", () => {
                field.select();
                openPopover(field);
            });
            field.addEventListener("click", () => openPopover(field));

            field.addEventListener("input", () => {
                if (field.dataset.journalField === "grade") {
                    normalizeGrade(field);
                } else {
                    normalizeAttendance(field);
                    updateAttendanceCell(field);
                }

                if (field.value) {
                    closePopover();
                    focusRelative(field, 1);
                }
                updateAuditPanel(field.closest("form"));
                scheduleAutosave(field);
            });

            field.addEventListener("change", () => {
                updateAuditPanel(field.closest("form"));
                scheduleAutosave(field);
            });

            if (field.dataset.journalField === "attendance") {
                updateAttendanceCell(field);
            }

            field.addEventListener("keydown", (event) => {
                if (event.key === "Enter" || event.key === "ArrowDown") {
                    event.preventDefault();
                    focusRelative(field, 1);
                } else if (event.key === "ArrowUp") {
                    event.preventDefault();
                    focusRelative(field, -1);
                } else if (event.key === "ArrowRight" && !field.value) {
                    const row = field.closest("tr");
                    const fields = Array.from(
                        row.querySelectorAll(
                            `[data-journal-field="${field.dataset.journalField}"]`
                        )
                    );
                    const next = fields[fields.indexOf(field) + 1];
                    if (next) {
                        event.preventDefault();
                        next.focus();
                        next.select();
                    }
                } else if (event.key === "ArrowLeft" && !field.value) {
                    const row = field.closest("tr");
                    const fields = Array.from(
                        row.querySelectorAll(
                            `[data-journal-field="${field.dataset.journalField}"]`
                        )
                    );
                    const previous = fields[fields.indexOf(field) - 1];
                    if (previous) {
                        event.preventDefault();
                        previous.focus();
                        previous.select();
                    }
                }
            });
        });
    }

    function setupAuditReasonPanels() {
        document.querySelectorAll("form").forEach((form) => {
            const fields = form.querySelectorAll(
                "[data-journal-field], [data-audit-field]"
            );
            if (!fields.length || !form.querySelector("[data-audit-panel]")) {
                return;
            }
            fields.forEach((field) => {
                if (!field.dataset.journalField) {
                    field.addEventListener("change", () => {
                        updateAuditPanel(form);
                    });
                }
            });
            form.querySelector("[data-change-reason-select]")?.addEventListener(
                "change",
                () => updateOtherReasonField(form)
            );
            updateAuditPanel(form);
        });
    }

    function setupCurriculumTopicSelection() {
        const topicSelect = document.querySelector(
            "select[name='curriculum_item']"
        );
        const dateInput = document.querySelector("input[name='date']");
        if (!topicSelect || !dateInput) {
            return;
        }
        topicSelect.addEventListener("change", () => {
            const option = topicSelect.selectedOptions[0];
            if (option?.dataset.plannedDate) {
                dateInput.value = option.dataset.plannedDate;
            }
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        setupJournalKeyboard();
        setupAuditReasonPanels();
        setupCurriculumTopicSelection();

        document.addEventListener("mousedown", (event) => {
            const popover = getPopover();
            if (
                !popover.contains(event.target) &&
                !event.target.matches("[data-journal-field]")
            ) {
                closePopover();
            }
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                closePopover();
            }
        });
        window.addEventListener("resize", closePopover);
        document.querySelector(".journal-table-wrap")?.addEventListener(
            "scroll",
            closePopover
        );
    });
})();
