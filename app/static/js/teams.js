async function loadTeams() {
    try {
        const response = await authFetch('/teams/list');

        if (response.ok) {
            const teams = await response.json();
            const teamsList = document.getElementById('teams-list');
            teamsList.innerHTML = '';

            if (teams.length === 0) {
                teamsList.innerHTML = '<p>У вас пока нет команд. Создайте первую команду или присоединитесь к существующей.</p>';
                return;
            }

            teams.forEach(team => {
                const teamDiv = document.createElement('div');
                teamDiv.className = 'team-item';

                const userMember = team.members.find(member => member.user.id === currentUser.id);
                const userRole = userMember ? userMember.role : 'member';

                teamDiv.innerHTML = `
                    <div class="team-header">
                        <h4>${team.name}</h4>
                        <span class="team-role ${userRole}">${userRole === 'admin' ? 'Администратор' : 'Участник'}</span>
                    </div>
                    <p class="team-description">${team.description || 'Нет описания'}</p>
                    <p class="team-members">Участников: ${team.members.length}</p>
                    <div class="team-actions">
                        ${userRole === 'admin' ? `
                        <button class="btn btn-outline" onclick="showInviteCode(${team.id})">
                            Код приглашения
                        </button>
                        ` : ''}
                    </div>
                `;
                teamsList.appendChild(teamDiv);
            });
        } else {
            console.error('Failed to load teams');
            document.getElementById('teams-list').innerHTML = '<p class="text-danger">Ошибка при загрузке команд</p>';
        }
    } catch (error) {
        console.error('Error loading teams:', error);
        document.getElementById('teams-list').innerHTML = '<p class="text-danger">Ошибка при загрузке команд</p>';
    }
}

async function showInviteCode(teamId) {
    try {
        const response = await authFetch(`/teams/${teamId}/invite-code`);

        if (response.ok) {
            const data = await response.json();
            alert(`Код приглашения для команды: ${data.invite_code}\n\nПоделитесь этим кодом с участниками, чтобы они могли присоединиться к команде.`);
        } else {
            const error = await response.json();
            alert(`Ошибка: ${error.detail}`);
        }
    } catch (error) {
        console.error('Error getting invite code:', error);
        alert('Ошибка при получении кода приглашения');
    }
}

function showCreateTeamForm() {
    document.getElementById('create-team-form').style.display = 'block';
}

function hideCreateTeamForm() {
    document.getElementById('create-team-form').style.display = 'none';
    document.getElementById('create-team').reset();
}

function setupCreateTeamForm() {
    document.getElementById('create-team').addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(e.target);
        const teamData = {
            name: formData.get('name'),
            description: formData.get('description')
        };

        try {
            const response = await authFetch('/teams', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(teamData)
            });

            if (response.ok) {
                const newTeam = await response.json();
                alert(`Команда "${newTeam.name}" создана успешно!`);
                hideCreateTeamForm();
                loadTeams();
            } else {
                const error = await response.json();
                alert(`Ошибка: ${error.detail}`);
            }
        } catch (error) {
            console.error('Error creating team:', error);
            alert('Ошибка при создании команды');
        }
    });
}

function setupJoinTeamForm() {
    document.getElementById('join-team').addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(e.target);
        const joinData = {
            invite_code: formData.get('invite_code')
        };

        try {
            const response = await authFetch('/teams/join', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(joinData)
            });

            if (response.ok) {
                const result = await response.json();
                alert(result.message);
                document.getElementById('join-team').reset();
                loadTeams();
            } else {
                const error = await response.json();
                alert(`Ошибка: ${error.detail}`);
            }
        } catch (error) {
            console.error('Error joining team:', error);
            alert('Ошибка при присоединении к команде');
        }
    });
}

let currentUser = null;

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

document.addEventListener('DOMContentLoaded', async () => {
    await getCurrentUser();
    await loadTeams();
    setupCreateTeamForm();
    setupJoinTeamForm();
});