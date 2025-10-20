let currentMeetings = [];
let currentFilter = 'all';
let userTeamsWithRoles = [];
let currentUser = null;

function showCreateMeetingForm() {
    document.getElementById('create-meeting-form').style.display = 'block';
    loadTeamsForMeetingCreation();

    const now = new Date();
    now.setMinutes(0, 0, 0);
    document.getElementById('meeting-start').value = formatDateTimeForInput(now);

    const endTime = new Date(now);
    endTime.setHours(now.getHours() + 1);
    document.getElementById('meeting-end').value = formatDateTimeForInput(endTime);
}

function hideCreateMeetingForm() {
    document.getElementById('create-meeting-form').style.display = 'none';
    document.getElementById('create-meeting').reset();
    document.getElementById('participants-list').innerHTML = '<p class="text-muted">Выберите команду для загрузки участников</p>';
}

async function loadTeamsForMeetingCreation() {
    try {
        const response = await authFetch('/teams/list');

        if (response.ok) {
            const teams = await response.json();
            const teamSelect = document.getElementById('meeting-team');
            teamSelect.innerHTML = '<option value="">Выберите команду</option>';

            teams.forEach(team => {
                const option = document.createElement('option');
                option.value = team.id;
                option.textContent = team.name;
                teamSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading teams:', error);
        alert('Ошибка при загрузке списка команд');
    }
}

async function loadTeamMembers(teamId) {
    if (!teamId) {
        document.getElementById('participants-list').innerHTML = '<p class="text-muted">Выберите команду для загрузки участников</p>';
        return;
    }

    try {
        const response = await authFetch(`/teams/${teamId}`);

        if (response.ok) {
            const team = await response.json();
            const participantsList = document.getElementById('participants-list');
            participantsList.innerHTML = '';

            if (team.members && team.members.length > 0) {
                team.members.forEach(member => {
                    if (member.user.id === currentUser.id) return;

                    const checkbox = document.createElement('div');
                    checkbox.className = 'form-check';
                    checkbox.innerHTML = `
                        <input class="form-check-input" type="checkbox" value="${member.user.id}" id="participant-${member.user.id}">
                        <label class="form-check-label" for="participant-${member.user.id}">
                            ${member.user.first_name || ''} ${member.user.last_name || ''} (${member.user.email}) - ${member.role}
                        </label>
                    `;
                    participantsList.appendChild(checkbox);
                });
            } else {
                participantsList.innerHTML = '<p class="text-muted">В этой команде нет других участников</p>';
            }
        }
    } catch (error) {
        console.error('Error loading team members:', error);
        document.getElementById('participants-list').innerHTML = '<p class="text-danger">Ошибка при загрузке участников</p>';
    }
}

async function loadMeetings() {
    try {
        const filter = document.getElementById('meeting-filter').value;
        currentFilter = filter;

        const response = await authFetch(`/meetings/list?filter=${filter}`);

        if (response.ok) {
            currentMeetings = await response.json();
            renderMeetings(currentMeetings);
        } else {
            console.error('Failed to load meetings');
            document.getElementById('meetings-list').innerHTML = '<p class="text-danger">Ошибка при загрузке встреч</p>';
        }
    } catch (error) {
        console.error('Error loading meetings:', error);
        document.getElementById('meetings-list').innerHTML = '<p class="text-danger">Ошибка при загрузке встреч</p>';
    }
}

function renderMeetings(meetings) {
    const container = document.getElementById('meetings-list');

    if (meetings.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <p class="text-muted">${getNoMeetingsMessage()}</p>
            </div>
        `;
        return;
    }

    let html = '';

    meetings.forEach(meeting => {
        const startTime = new Date(meeting.start_time);
        const endTime = new Date(meeting.end_time);
        const isPast = endTime < new Date();

        const isOrganizer = meeting.organizer.id === currentUser.id;
        const userTeam = userTeamsWithRoles.find(team => team.id === meeting.team.id);
        const isTeamAdmin = userTeam && userTeam.role === 'admin';
        const canDelete = isOrganizer || isTeamAdmin;

        html += `
            <div class="meeting-item ${isPast ? 'meeting-past' : ''}">
                <div class="meeting-header">
                    <h5 class="meeting-title">${meeting.title}</h5>
                    <span class="meeting-status ${isPast ? 'status-past' : 'status-upcoming'}">
                        ${isPast ? 'Завершена' : 'Предстоящая'}
                    </span>
                </div>

                <p class="meeting-description">${meeting.description || 'Нет описания'}</p>

                <div class="meeting-details">
                    <div class="meeting-time">
                        <strong>Время:</strong>
                        ${startTime.toLocaleString('ru-RU')} - ${endTime.toLocaleString('ru-RU')}
                    </div>
                    <div class="meeting-meta">
                        <span class="meeting-organizer">
                            <strong>Организатор:</strong> ${meeting.organizer.email}
                            ${isOrganizer ? ' (Вы)' : ''}
                        </span>
                        <span class="meeting-team">
                            <strong>Команда:</strong> ${meeting.team.name}
                            ${isTeamAdmin ? ' (Вы - админ)' : ''}
                        </span>
                        <span class="meeting-participants">
                            <strong>Участников:</strong> ${meeting.participants.length}
                        </span>
                    </div>
                </div>

                <div class="meeting-actions">
                    <button class="btn btn-sm btn-outline-primary" onclick="viewMeeting(${meeting.id})">
                        Подробнее
                    </button>
                    ${canDelete ? `
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteMeeting(${meeting.id})">
                        Удалить
                    </button>
                    ` : ''}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

async function deleteMeeting(meetingId) {
    if (!confirm('Вы уверены, что хотите удалить эту встречу? Это действие нельзя отменить.')) {
        return;
    }

    try {
        const response = await authFetch(`/meetings/${meetingId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            const result = await response.json();
            alert(result.message);
            loadMeetings();
        } else {
            const error = await response.json();
            alert(`Ошибка: ${error.detail}`);
        }
    } catch (error) {
        console.error('Error deleting meeting:', error);
        alert('Ошибка при удалении встречи');
    }
}

function getNoMeetingsMessage() {
    switch (currentFilter) {
        case 'upcoming':
            return 'Нет предстоящих встреч';
        case 'past':
            return 'Нет прошедших встреч';
        default:
            return 'У вас пока нет встреч';
    }
}

async function viewMeeting(meetingId) {
    try {
        const response = await authFetch(`/meetings/${meetingId}`);

        if (response.ok) {
            const meeting = await response.json();
            const startTime = new Date(meeting.start_time);
            const endTime = new Date(meeting.end_time);

            const isOrganizer = meeting.organizer.id === currentUser.id;
            const userTeam = userTeamsWithRoles.find(team => team.id === meeting.team.id);
            const isTeamAdmin = userTeam && userTeam.role === 'admin';
            const canDelete = isOrganizer || isTeamAdmin;

            let participantsHtml = '';
            meeting.participants.forEach(participant => {
                participantsHtml += `<li>${participant.user.email}</li>`;
            });

            let modalContent = `
                <h4>${meeting.title}</h4>
                <p><strong>Описание:</strong> ${meeting.description || 'Нет описания'}</p>
                <p><strong>Время:</strong> ${startTime.toLocaleString('ru-RU')} - ${endTime.toLocaleString('ru-RU')}</p>
                <p><strong>Команда:</strong> ${meeting.team.name}</p>
                <p><strong>Организатор:</strong> ${meeting.organizer.email} ${isOrganizer ? '(Вы)' : ''}</p>
                <p><strong>Участники (${meeting.participants.length}):</strong></p>
                <ul>${participantsHtml}</ul>
            `;

            if (canDelete) {
                modalContent += `
                    <div class="mt-3 text-center">
                        <button class="btn btn-danger" onclick="deleteMeeting(${meeting.id}); closeModal();">
                            Удалить встречу
                        </button>
                    </div>
                `;
            }

            showSimpleModal('Детали встречи', modalContent);
        } else {
            const error = await response.json();
            alert(`Ошибка: ${error.detail}`);
        }
    } catch (error) {
        console.error('Error viewing meeting:', error);
        alert('Ошибка при загрузке деталей встречи');
    }
}

function showSimpleModal(title, content) {
    const modalOverlay = document.createElement('div');
    modalOverlay.className = 'modal-overlay';
    modalOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
    `;

    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';
    modalContent.style.cssText = `
        background: white;
        padding: 20px;
        border-radius: 8px;
        max-width: 600px;
        width: 90%;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    `;

    modalContent.innerHTML = `
        <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px;">
            <h3 style="margin: 0;">${title}</h3>
            <button onclick="closeModal()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
        </div>
        <div class="modal-body">
            ${content}
        </div>
        <div class="modal-footer" style="margin-top: 20px; text-align: right; border-top: 1px solid #eee; padding-top: 10px;">
            <button onclick="closeModal()" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">Закрыть</button>
        </div>
    `;

    modalOverlay.appendChild(modalContent);
    document.body.appendChild(modalOverlay);

    modalOverlay.addEventListener('click', function (e) {
        if (e.target === modalOverlay) {
            closeModal();
        }
    });

    window.currentModal = modalOverlay;
}

function closeModal() {
    if (window.currentModal) {
        document.body.removeChild(window.currentModal);
        window.currentModal = null;
    }
}

async function loadUserTeams() {
    try {
        const response = await authFetch('/teams/list');

        if (response.ok) {
            const teams = await response.json();
            userTeamsWithRoles = teams.map(team => {
                const userMember = team.members.find(member => member.user.id === currentUser.id);
                return {
                    id: team.id,
                    name: team.name,
                    role: userMember ? userMember.role : null
                };
            });
        }
    } catch (error) {
        console.error('Error loading teams:', error);
    }
}

async function getCurrentUser() {
    try {
        const response = await authFetch('/auth/me');
        if (response.ok) {
            currentUser = await response.json();
        } else {
            console.error('Failed to get current user');
            window.location.href = '/auth/login';
        }
    } catch (error) {
        console.error('Error getting current user:', error);
        window.location.href = '/auth/login';
    }
}

function formatDateTimeForInput(date) {
    return date.toISOString().slice(0, 16);
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', async () => {
    await getCurrentUser();
    await loadUserTeams();
    await loadMeetings();

    document.getElementById('create-meeting').addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(e.target);
        const participantCheckboxes = document.querySelectorAll('#participants-list input:checked');
        const participantIds = Array.from(participantCheckboxes).map(cb => parseInt(cb.value));

        const startTime = new Date(formData.get('start_time'));
        const endTime = new Date(formData.get('end_time'));

        if (endTime <= startTime) {
            alert('Время окончания должно быть позже времени начала');
            return;
        }

        const meetingData = {
            title: formData.get('title'),
            description: formData.get('description'),
            team_id: parseInt(formData.get('team_id')),
            start_time: startTime.toISOString(),
            end_time: endTime.toISOString(),
            participant_ids: participantIds
        };

        try {
            const response = await authFetch('/meetings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(meetingData)
            });

            if (response.ok) {
                const newMeeting = await response.json();
                alert(`Встреча "${newMeeting.title}" создана успешно!`);
                hideCreateMeetingForm();
                loadMeetings();
            } else {
                const error = await response.json();
                alert(`Ошибка: ${error.detail}`);
            }
        } catch (error) {
            console.error('Error creating meeting:', error);
            alert('Ошибка при создании встречи');
        }
    });
});