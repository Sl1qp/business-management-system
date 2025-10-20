let currentPage = tasksConfig.currentPage;
let perPage = tasksConfig.perPage;
let totalPages = 1;
let currentFilter = 'all';
let currentSort = 'newest';

async function loadTasks(page = currentPage, perPage = perPage) {
    try {
        const filter = document.getElementById('task-filter').value;
        const sort = document.getElementById('task-sort').value;

        const response = await authFetch(`/tasks/list?page=${page}&per_page=${perPage}&filter=${filter}&sort=${sort}`);

        if (response.ok) {
            const data = await response.json();
            const tasks = data.items;
            totalPages = data.total_pages;

            const tasksList = document.getElementById('tasks-list');
            tasksList.innerHTML = '';

            if (tasks.length === 0) {
                tasksList.innerHTML = '<p>Нет задач для отображения</p>';
                return;
            }

            tasks.forEach(task => {
                const taskDiv = document.createElement('div');
                taskDiv.className = 'task-item';

                let statusClass = '';
                switch (task.status) {
                    case 'open':
                        statusClass = 'status-open';
                        break;
                    case 'in_progress':
                        statusClass = 'status-in-progress';
                        break;
                    case 'completed':
                        statusClass = 'status-completed';
                        break;
                }

                const deadline = task.deadline ?
                    new Date(task.deadline).toLocaleString('ru-RU') :
                    'Не установлен';

                const isOverdue = task.deadline && new Date(task.deadline) < new Date() && task.status !== 'completed';

                taskDiv.innerHTML = `
                    <div class="task-header">
                        <h4>${task.title}</h4>
                        <span class="task-status ${statusClass}">${getStatusText(task.status)}</span>
                    </div>
                    <p class="task-description">${task.description || 'Нет описания'}</p>
                    <div class="task-details">
                        <div class="task-detail">
                            <strong>Дедлайн:</strong>
                            <span class="${isOverdue ? 'overdue' : ''}">${deadline}</span>
                        </div>
                        <div class="task-detail">
                            <strong>Исполнитель:</strong>
                            ${task.assignee ? task.assignee.email : 'Не назначен'}
                        </div>
                        <div class="task-detail">
                            <strong>Команда:</strong>
                            ${task.team ? task.team.name : 'Не указана'}
                        </div>
                        <div class="task-detail">
                            <strong>Создана:</strong>
                            ${new Date(task.created_at).toLocaleString('ru-RU')}
                        </div>
                    </div>
                    <div class="task-actions">
                        <button onclick="changeTaskStatus(${task.id}, '${task.status}')">Сменить статус</button>
                    </div>
                `;
                tasksList.appendChild(taskDiv);
            });

            updatePaginationInfo(data);
        } else {
            console.error('Failed to load tasks');
        }
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

function getStatusText(status) {
    const statusMap = {
        'OPEN': 'Открыта',
        'IN_PROGRESS': 'В процессе',
        'COMPLETED': 'Завершена'
    };
    return statusMap[status] || status;
}

async function changeTaskStatus(taskId, currentStatus) {
    let newStatus;
    switch (currentStatus) {
        case 'OPEN':
            newStatus = 'IN_PROGRESS';
            break;
        case 'IN_PROGRESS':
            newStatus = 'COMPLETED';
            break;
        case 'COMPLETED':
            newStatus = 'OPEN';
            break;
        default:
            newStatus = 'OPEN';
    }

    try {
        const response = await authFetch(`/tasks/${taskId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({status: newStatus})
        });

        if (response.ok) {
            alert('Статус задачи обновлен');
            loadTasks(currentPage, perPage);
        } else {
            const error = await response.json();
            alert(`Ошибка: ${error.detail}`);
        }
    } catch (error) {
        console.error('Error updating task status:', error);
        alert('Ошибка при обновлении статуса задачи');
    }
}

function changePage(delta) {
    const newPage = currentPage + delta;
    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        loadTasks(currentPage, perPage);
    }
}

function updatePaginationInfo(data) {
    document.getElementById('page-info').textContent =
        `Страница ${data.page} из ${data.total_pages} (Всего: ${data.total_count})`;

    document.getElementById('prev-page').disabled = data.page <= 1;
    document.getElementById('next-page').disabled = data.page >= data.total_pages;
}

function showCreateTaskForm() {
    document.getElementById('create-task-form').style.display = 'block';
    loadTeamsForTaskCreation();
}

function hideCreateTaskForm() {
    document.getElementById('create-task-form').style.display = 'none';
}

async function loadTeamsForTaskCreation() {
    try {
        const response = await authFetch('/teams/list');

        if (response.ok) {
            const teams = await response.json();
            const teamSelect = document.getElementById('task-team');
            teamSelect.innerHTML = '';

            teams.forEach(team => {
                const option = document.createElement('option');
                option.value = team.id;
                option.textContent = team.name;
                teamSelect.appendChild(option);
            });

            teamSelect.addEventListener('change', (e) => {
                loadTeamMembers(e.target.value);
            });

            if (teams.length > 0) {
                loadTeamMembers(teams[0].id);
            }
        }
    } catch (error) {
        console.error('Error loading teams:', error);
    }
}

async function loadTeamMembers(teamId) {
    try {
        const response = await authFetch(`/teams/${teamId}`);

        if (response.ok) {
            const team = await response.json();
            const assigneeSelect = document.getElementById('task-assignee');
            assigneeSelect.innerHTML = '<option value="">Не назначено</option>';

            team.members.forEach(member => {
                const option = document.createElement('option');
                option.value = member.user.id;
                option.textContent = `${member.user.first_name} ${member.user.last_name} (${member.user.email})`;
                assigneeSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading team members:', error);
    }
}

function setupFormHandler() {
    document.getElementById('create-task').addEventListener('submit', async (e) => {
        e.preventDefault();

        function formatDateForISO(dateString) {
            if (!dateString) return null;

            const date = new Date(dateString);
            const utcDate = new Date(Date.UTC(
                date.getFullYear(),
                date.getMonth(),
                date.getDate(),
                date.getHours(),
                date.getMinutes(),
                date.getSeconds()
            ));

            return utcDate.toISOString();
        }

        const formData = new FormData(e.target);
        const taskData = {
            title: formData.get('title'),
            description: formData.get('description'),
            team_id: parseInt(formData.get('team_id')),
            assignee_id: formData.get('assignee_id') ? parseInt(formData.get('assignee_id')) : null,
            deadline: formData.get('deadline') ? formatDateForISO(formData.get('deadline')) : null
        };

        console.log('Sending task data:', taskData);

        try {
            const response = await authFetch('/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(taskData)
            });

            if (response.ok) {
                const newTask = await response.json();
                alert(`Задача "${newTask.title}" создана успешно!`);
                hideCreateTaskForm();
                loadTasks();
            } else {
                const error = await response.json();
                console.error('Error response:', error);
                alert(`Ошибка: ${error.detail}`);
            }
        } catch (error) {
            console.error('Error creating task:', error);
            alert('Ошибка при создании задачи');
        }
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    await loadTasks(currentPage, perPage);
    setupFormHandler();
});