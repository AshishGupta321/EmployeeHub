const $ = id => document.getElementById(id);
const API = "/employees";

const state = {
    employees: [],
    editing: null,
    confirm: null,
    activity: []
};

const palettes = [
    ["#eeeaff", "#6655e8"],
    ["#e4f7ef", "#198b65"],
    ["#fff0df", "#b87520"],
    ["#e7f2ff", "#3575bd"],
    ["#ffe9ef", "#be4f77"]
];

const money = n =>
    new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0
    }).format(Number(n || 0));

const desig = e => e.desig ?? e.designation ?? "";

const esc = s =>
    String(s ?? "").replace(/[&<>"']/g, c => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    }[c]));

const initials = s =>
    String(s || "?")
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map(x => x[0] || "")
        .join("")
        .toUpperCase();

async function api(path = "", opts = {}) {
    const response = await fetch(API + path, {
        ...opts,
        headers: {
            "Content-Type": "application/json",
            ...(opts.headers || {})
        }
    });

    const text = await response.text();
    let data;

    try {
        data = text ? JSON.parse(text) : null;
    } catch {
        data = text;
    }

    if (!response.ok) {
        throw Error(
            typeof data?.detail === "string"
                ? data.detail
                : data?.message || `Request failed (${response.status})`
        );
    }

    return data;
}

function toast(title, message = "", bad = false) {
    const node = document.createElement("div");
    node.className = "toast" + (bad ? " bad" : "");

    node.innerHTML = `
        <b>${bad ? "!" : "✓"}</b>
        <div>
            <strong>${esc(title)}</strong>
            <span>${esc(message)}</span>
        </div>
    `;

    $("toasts").append(node);
    setTimeout(() => node.remove(), 4000);
}

function log(title, detail, mark = "✓") {
    state.activity.unshift({
        title,
        detail,
        mark,
        time: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit"
        })
    });

    state.activity = state.activity.slice(0, 5);

    $("activity").innerHTML = state.activity.map(a => `
        <div class="activity-item">
            <i>${esc(a.mark)}</i>
            <div>
                <b>${esc(a.title)}</b>
                <small>${esc(a.detail)} · ${esc(a.time)}</small>
            </div>
        </div>
    `).join("");
}

function filtered() {
    const query = $("search").value.trim().toLowerCase();
    const designation = $("designationFilter").value;

    const min = $("minSalary").value === ""
        ? null : Number($("minSalary").value);

    const max = $("maxSalary").value === ""
        ? null : Number($("maxSalary").value);

    const sort = $("sort").value;

    return state.employees
        .filter(e =>
            (!query ||
                String(e.id).includes(query) ||
                e.name.toLowerCase().includes(query)) &&
            (!designation || desig(e) === designation) &&
            (min === null || Number(e.salary) >= min) &&
            (max === null || Number(e.salary) <= max)
        )
        .sort((a, b) => {
            const key = sort.replace("-", "");
            const first = key === "designation" ? desig(a) : a[key];
            const second = key === "designation" ? desig(b) : b[key];

            const comparison = typeof first === "string"
                ? first.localeCompare(second)
                : Number(first) - Number(second);

            return comparison * (sort.startsWith("-") ? -1 : 1);
        });
}

function renderRows() {
    const employees = filtered();

    $("rows").innerHTML = employees.length
        ? employees.map(e => {
            const color = palettes[
                Number(e.id) % palettes.length
            ];

            return `
                <tr>
                    <td>
                        <div class="employee">
                            <span class="avatar"
                                style="--avbg:${color[0]};--avfg:${color[1]}">
                                ${esc(initials(e.name))}
                            </span>
                            <div>
                                <b>${esc(e.name)}</b>
                                <small>ID: ${esc(e.id)}</small>
                            </div>
                        </div>
                    </td>

                    <td>${esc(e.age)}</td>
                    <td class="salary">${money(e.salary)}</td>

                    <td>
                        <span class="badge">${esc(desig(e))}</span>
                    </td>

                    <td>
                        <div class="actions">
                            <button class="edit" data-edit="${Number(e.id)}">
                                Edit
                            </button>
                            <button class="delete" data-delete="${Number(e.id)}">
                                Delete
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join("")
        : `
            <tr>
                <td colspan="5" class="empty">
                    ⌕<br>
                    <b>No employees found</b><br>
                    Try changing your search or filters.
                </td>
            </tr>
        `;

    $("resultCount").textContent =
        `Showing ${employees.length} of ${state.employees.length} employees`;

    $("rows").querySelectorAll("[data-edit]").forEach(button => {
        button.onclick = () => edit(Number(button.dataset.edit));
    });

    $("rows").querySelectorAll("[data-delete]").forEach(button => {
        button.onclick = () => deleteOne(Number(button.dataset.delete));
    });
}

function renderOptions() {
    const current = $("designationFilter").value;

    const names = [
        ...new Set(state.employees.map(desig).filter(Boolean))
    ].sort();

    $("designationFilter").innerHTML =
        '<option value="">All designations</option>' +
        names.map(name =>
            `<option>${esc(name)}</option>`
        ).join("");

    $("designationFilter").value = names.includes(current) ? current : "";

    const oldEmployee = $("salaryEmployee").value;

    $("salaryEmployee").innerHTML =
        '<option value="">Select employee</option>' +
        state.employees
            .slice()
            .sort((a, b) => a.name.localeCompare(b.name))
            .map(e => `
                <option value="${Number(e.id)}">
                    ${esc(e.name)} · #${Number(e.id)}
                </option>
            `).join("");

    $("salaryEmployee").value = state.employees.some(
        e => String(e.id) === oldEmployee
    ) ? oldEmployee : "";
}

function renderChart() {
    const groups = {};

    state.employees.forEach(e => {
        const name = desig(e) || "Unspecified";

        groups[name] ??= { count: 0, total: 0 };
        groups[name].count++;
        groups[name].total += Number(e.salary);
    });

    const items = Object.entries(groups)
        .map(([name, value]) => ({
            name,
            average: value.total / value.count
        }))
        .sort((a, b) => b.average - a.average);

    const maximum = Math.max(1, ...items.map(x => x.average));

    $("chart").innerHTML = items.length
        ? items.map(item => `
            <div class="chart-row">
                <b>${esc(item.name)}</b>
                <div>
                    <i style="width:${Math.max(
                        3, item.average / maximum * 100
                    )}%"></i>
                </div>
                <small>${money(item.average)}</small>
            </div>
        `).join("")
        : '<p class="empty">Add employees to see insights.</p>';
}

async function stats() {
    const [count, average, extremes] = await Promise.all([
        api("/stats/count"),
        api("/stats/average-salary"),
        api("/stats/salary-extremes")
    ]);

    $("total").textContent = count.count ?? 0;
    $("average").textContent = money(average.average_salary);

    $("highest").textContent = extremes.highest
        ? money(extremes.highest.salary) : "—";

    $("highName").textContent =
        extremes.highest?.name || "No employee data";

    $("lowest").textContent = extremes.lowest
        ? money(extremes.lowest.salary) : "—";

    $("lowName").textContent =
        extremes.lowest?.name || "No employee data";
}

async function load() {
    try {
        state.employees = await api("");

        $("apiStatus").textContent = "Connected";
        $("profileStatus").textContent = "Connected";
        $("apiStatus").style.color = "#42d3a0";

        renderOptions();
        renderRows();
        renderChart();

        await stats();
    } catch (error) {
        $("apiStatus").textContent = "Offline";
        $("profileStatus").textContent = "Offline";

        $("rows").innerHTML = `
            <tr>
                <td colspan="5" class="empty">
                    <b>Could not load employees</b><br>
                    ${esc(error.message)}. Check that FastAPI is running.
                </td>
            </tr>
        `;

        toast("API connection failed", error.message, true);
    }
}

function clearForm() {
    $("employeeForm").reset();
    state.editing = null;

    $("employeeId").disabled = false;
    $("formLabel").textContent = "NEW TEAM MEMBER";
    $("formTitle").textContent = "Add employee";
    $("formSub").textContent = "Create an employee record.";
    $("submitEmployee").textContent = "Add employee ↗";
    $("cancelEdit").classList.add("hidden");
}

function edit(id) {
    const employee = state.employees.find(e => Number(e.id) === id);
    if (!employee) return;

    state.editing = id;

    $("employeeId").value = employee.id;
    $("employeeId").disabled = true;
    $("employeeName").value = employee.name;
    $("employeeAge").value = employee.age;
    $("employeeSalary").value = employee.salary;
    $("employeeDesignation").value = desig(employee);

    $("formLabel").textContent = `EDITING EMPLOYEE #${id}`;
    $("formTitle").textContent = "Update employee";
    $("formSub").textContent = "Make changes to this employee record.";
    $("submitEmployee").textContent = "Save changes ✓";
    $("cancelEdit").classList.remove("hidden");

    $("employeeFormPanel").scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

// CREATE and UPDATE
$("employeeForm").onsubmit = async event => {
    event.preventDefault();

    const employee = {
        id: Number($("employeeId").value),
        name: $("employeeName").value.trim(),
        age: Number($("employeeAge").value),
        salary: Number($("employeeSalary").value),
        desig: $("employeeDesignation").value.trim()
    };

    const editing = state.editing;

    try {
        if (editing !== null) {
            const { id, ...body } = employee;

            await api("/" + editing, {
                method: "PUT",
                body: JSON.stringify(body)
            });

            toast("Employee updated", `${employee.name}'s details were saved.`);
            log("Employee updated", `${employee.name} · ID ${editing}`, "✎");
        } else {
            await api("", {
                method: "POST",
                body: JSON.stringify(employee)
            });

            toast("Employee added", `${employee.name} was added to the directory.`);
            log("Employee added", `${employee.name} · ID ${employee.id}`, "+");
        }

        clearForm();
        await load();
    } catch (error) {
        toast(
            editing !== null ? "Update failed" : "Could not add employee",
            error.message,
            true
        );
    }
};

$("clearForm").onclick = clearForm;
$("cancelEdit").onclick = clearForm;

// Salary adjustment
$("salaryForm").onsubmit = async event => {
    event.preventDefault();

    const id = Number($("salaryEmployee").value);
    const amount = Number($("increaseAmount").value);

    if (!id || amount <= 0) {
        return toast(
            "Check the details",
            "Choose an employee and enter a positive amount.",
            true
        );
    }

    try {
        const result = await api(
            `/${id}/increase-salary?amount=${amount}`,
            { method: "POST" }
        );

        toast(
            "Salary updated",
            `${result.employee.name}'s salary increased by ${money(amount)}.`
        );

        log(
            "Salary increased",
            `${result.employee.name} · +${money(amount)}`,
            "↗"
        );

        $("increaseAmount").value = "";
        await load();
    } catch (error) {
        toast("Salary increase failed", error.message, true);
    }
};

// Delete confirmation modal
function ask(title, message, action, label = "Confirm delete") {
    $("confirmTitle").textContent = title;
    $("confirmText").textContent = message;
    $("acceptConfirm").textContent = label;

    state.confirm = action;
    $("confirm").classList.remove("hidden");
}

function closeAsk() {
    $("confirm").classList.add("hidden");
    state.confirm = null;
}

$("cancelConfirm").onclick = closeAsk;

$("confirm").onclick = event => {
    if (event.target === $("confirm")) closeAsk();
};

$("acceptConfirm").onclick = async () => {
    if (!state.confirm) return;

    const action = state.confirm;
    $("acceptConfirm").disabled = true;

    try {
        await action();
    } finally {
        $("acceptConfirm").disabled = false;
        closeAsk();
    }
};

// DELETE one employee
function deleteOne(id) {
    const employee = state.employees.find(e => Number(e.id) === id);
    if (!employee) return;

    ask(
        "Delete employee?",
        `Permanently remove ${employee.name} (ID ${id}) from your records.`,
        async () => {
            try {
                await api("/" + id, { method: "DELETE" });

                toast("Employee deleted", `${employee.name} was removed.`);
                log("Employee deleted", `${employee.name} · ID ${id}`, "−");

                if (state.editing === id) clearForm();

                await load();
            } catch (error) {
                toast("Delete failed", error.message, true);
            }
        }
    );
}

// DELETE all employees
$("deleteAll").onclick = () => {
    if (!state.employees.length) {
        return toast("Directory is empty", "There are no records to delete.", true);
    }

    ask(
        "Delete every employee?",
        `This permanently deletes all ${state.employees.length} employee records. This cannot be undone.`,
        async () => {
            try {
                const result = await api("", { method: "DELETE" });

                toast("Directory cleared", `${result.deleted_count} records deleted.`);
                log("All employees deleted", "Employee directory cleared", "!");

                clearForm();
                await load();
            } catch (error) {
                toast("Could not delete records", error.message, true);
            }
        },
        "Delete all records"
    );
};

// Search, sorting and filters
["search", "designationFilter", "sort"].forEach(id => {
    $(id).addEventListener(
        id === "search" ? "input" : "change",
        renderRows
    );
});

$("filterBtn").onclick = () => {
    const min = $("minSalary").value;
    const max = $("maxSalary").value;

    if (min !== "" && max !== "" && Number(min) > Number(max)) {
        return toast(
            "Invalid salary range",
            "Minimum cannot exceed maximum.",
            true
        );
    }

    renderRows();
};

$("resetBtn").onclick = () => {
    $("search").value = "";
    $("designationFilter").value = "";
    $("sort").value = "id";
    $("minSalary").value = "";
    $("maxSalary").value = "";

    renderRows();
};

$("refresh").onclick = load;

// Navigation
function go(id) {
    $(id).scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

    $("crumb").textContent =
        id === "employees" ? "EMPLOYEES" :
        id === "insights" ? "SALARY INSIGHTS" : "OVERVIEW";

    document.querySelectorAll("[data-nav]").forEach(link => {
        link.classList.toggle("active", link.dataset.nav === id);
    });

    $("sidebar").classList.remove("open");
}

document.querySelectorAll("[data-nav]").forEach(link => {
    link.onclick = event => {
        event.preventDefault();
        go(link.dataset.nav);
    };
});

function addNew() {
    clearForm();
    go("employees");

    $("employeeFormPanel").scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

    $("employeeId").focus({ preventScroll: true });
}

$("navAdd").onclick = $("addTop").onclick = addNew;
$("explore").onclick = () => go("employees");

$("menuToggle").onclick = () => {
    $("sidebar").classList.toggle("open");
};

// Dark mode
$("themeToggle").onclick = () => {
    document.body.classList.toggle("dark");

    const dark = document.body.classList.contains("dark");

    $("themeToggle").textContent = dark ? "☀" : "☾";

    try {
        localStorage.setItem("eh-theme", dark ? "dark" : "light");
    } catch {}
};

try {
    if (localStorage.getItem("eh-theme") === "dark") {
        document.body.classList.add("dark");
        $("themeToggle").textContent = "☀";
    }
} catch {}

// Profile modal
$("profileButton").onclick = () =>
    $("profile").classList.remove("hidden");

$("closeProfile").onclick = () =>
    $("profile").classList.add("hidden");

$("profile").onclick = event => {
    if (event.target === $("profile")) {
        $("profile").classList.add("hidden");
    }
};

document.onkeydown = event => {
    if (event.key === "Escape") {
        closeAsk();
        $("profile").classList.add("hidden");
        $("sidebar").classList.remove("open");
    }
};

// Footer and initial load
$("year").textContent = new Date().getFullYear();

$("today").textContent = new Date()
    .toLocaleDateString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric"
    })
    .toUpperCase();

load();