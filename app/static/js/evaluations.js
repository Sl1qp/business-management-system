document.addEventListener('DOMContentLoaded', async function() {
    await checkAuth();

    await loadEvaluations();

    await loadTasksForEvaluation();
    await loadUsersForEvaluation();

    document.getElementById('createEvaluationForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        await createEvaluation();
    });
});

async function loadEvaluations() {
    try {
        const response = await authFetch('/evaluations/list');
        if (response.ok) {
            const evaluations = await response.json();
            displayEvaluations(evaluations);
        } else if (response.status === 401) {
            window.location.href = '/auth/login';
        } else {
            console.error('Ошибка загрузки оценок:', response.status);
            const container = document.getElementById('evaluations-container');
            if (container) {
                container.innerHTML = '<p>Ошибка загрузки оценок. Пожалуйста, попробуйте позже.</p>';
            }
        }
    } catch (error) {
        console.error('Error:', error);
        const container = document.getElementById('evaluations-container');
        if (container) {
            container.innerHTML = '<p>Ошибка загрузки оценок. Пожалуйста, попробуйте позже.</p>';
        }
    }
}

async function loadTasksForEvaluation() {
    try {
        const response = await authFetch('/tasks/my-team-tasks');
        if (response.ok) {
            const tasks = await response.json();
            const taskSelect = document.getElementById('taskSelect');

            if (taskSelect) {
                taskSelect.innerHTML = '<option value="">Выберите задачу</option>';
                tasks.forEach(task => {
                    const option = document.createElement('option');
                    option.value = task.id;
                    option.textContent = `${task.title} (${task.team ? task.team.name : 'Без команды'})`;
                    taskSelect.appendChild(option);
                });
            }
        } else {
            await loadTasksAlternative();
        }
    } catch (error) {
        console.error('Ошибка загрузки задач:', error);
        await loadTasksAlternative();
    }
}

async function loadTasksAlternative() {
    try {
        const response = await authFetch('/tasks/list?per_page=100');
        if (response.ok) {
            const tasksData = await response.json();
            const tasks = tasksData.items || tasksData;
            const taskSelect = document.getElementById('taskSelect');

            if (taskSelect) {
                taskSelect.innerHTML = '<option value="">Выберите задачу</option>';
                tasks.forEach(task => {
                    const option = document.createElement('option');
                    option.value = task.id;
                    option.textContent = task.title;
                    taskSelect.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('Ошибка альтернативной загрузки задач:', error);
    }
}

async function loadUsersForEvaluation() {
    try {
        const response = await authFetch('/users/list');
        if (response.ok) {
            const users = await response.json();
            const userSelect = document.getElementById('userSelect');

            if (userSelect) {
                userSelect.innerHTML = '<option value="">Выберите пользователя</option>';
                users.forEach(user => {
                    const option = document.createElement('option');
                    option.value = user.id;
                    option.textContent = `${user.first_name} ${user.last_name} (${user.email})`;
                    userSelect.appendChild(option);
                });
            }
        } else {
            await loadUsersFromTeams();
        }
    } catch (error) {
        console.error('Ошибка загрузки пользователей:', error);
        await loadUsersFromTeams();
    }
}

async function loadUsersFromTeams() {
    try {
        const teamsResponse = await authFetch('/teams/list');
        if (teamsResponse.ok) {
            const teams = await teamsResponse.json();
            const userSelect = document.getElementById('userSelect');

            if (userSelect) {
                userSelect.innerHTML = '<option value="">Выберите пользователя</option>';

                const allUsers = new Map();

                for (const team of teams) {
                    for (const member of team.members) {
                        if (!allUsers.has(member.user.id)) {
                            allUsers.set(member.user.id, member.user);

                            const option = document.createElement('option');
                            option.value = member.user.id;
                            option.textContent = `${member.user.first_name} ${member.user.last_name} (${member.user.email})`;
                            userSelect.appendChild(option);
                        }
                    }
                }
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки пользователей из команд:', error);
    }
}

async function createEvaluation() {
    const form = document.getElementById('createEvaluationForm');
    if (!form) return;

    const formData = new FormData(form);

    const evaluationData = {
        task_id: parseInt(formData.get('task_id')),
        user_id: parseInt(formData.get('user_id')),
        rating: parseInt(formData.get('rating')),
        comment: formData.get('comment')
    };

    try {
        const response = await authFetch('/evaluations/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(evaluationData)
        });

        if (response.ok) {
            alert('Оценка успешно создана!');
            form.reset();
            await loadEvaluations();
        } else {
            const error = await response.json();
            alert(`Ошибка: ${error.detail}`);
        }
    } catch (error) {
        console.error('Ошибка создания оценки:', error);
        alert('Ошибка при создании оценки');
    }
}

function displayEvaluations(evaluations) {
    const container = document.getElementById('evaluations-container');
    if (!container) return;

    if (!evaluations || evaluations.length === 0) {
        container.innerHTML = '<p>Пока нет ни одной оценки.</p>';
        return;
    }

    let tableHtml = `
        <h3>Список оценок</h3>
        <table class="table">
            <thead>
                <tr>
                    <th>Задача</th>
                    <th>Оцениваемый</th>
                    <th>Оценка</th>
                    <th>Комментарий</th>
                    <th>Оценщик</th>
                    <th>Дата оценки</th>
                </tr>
            </thead>
            <tbody>
    `;

    evaluations.forEach(evaluation => {
        const date = new Date(evaluation.created_at);
        const formattedDate = date.toLocaleString('ru-RU');

        tableHtml += `
            <tr>
                <td>${evaluation.task_title || 'Неизвестная задача'}</td>
                <td>${evaluation.user_name || 'Неизвестный пользователь'}</td>
                <td>
                    <span class="rating rating-${evaluation.rating}">
                        ${evaluation.rating}/5
                    </span>
                </td>
                <td>${evaluation.comment || '—'}</td>
                <td>${evaluation.evaluator_name || 'Неизвестный оценщик'}</td>
                <td>${formattedDate}</td>
            </tr>
        `;
    });

    tableHtml += `
            </tbody>
        </table>
    `;

    container.innerHTML = tableHtml;
}