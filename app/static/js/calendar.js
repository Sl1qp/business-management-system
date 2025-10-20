let currentView = calendarConfig.currentView;
let currentYear = calendarConfig.currentYear;
let currentMonth = calendarConfig.currentMonth;
let currentDay = calendarConfig.currentDay;

async function loadCalendarEvents() {
    try {
        let startDate, endDate;

        if (currentView === 'month') {
            startDate = new Date(currentYear, currentMonth - 1, 1);
            endDate = new Date(currentYear, currentMonth, 0);
        } else {
            startDate = new Date(currentYear, currentMonth - 1, currentDay);
            endDate = new Date(currentYear, currentMonth - 1, currentDay + 1);
        }

        const startStr = startDate.toISOString();
        const endStr = endDate.toISOString();

        const response = await authFetch(
            `/calendar/events?start=${encodeURIComponent(startStr)}&end=${encodeURIComponent(endStr)}&view=${currentView}`
        );

        if (response.ok) {
            const data = await response.json();
            renderCalendar(data.events);
        } else {
            document.getElementById('calendar-content').innerHTML =
                '<p>Ошибка загрузки календаря</p>';
        }
    } catch (error) {
        console.error('Error loading calendar:', error);
        document.getElementById('calendar-content').innerHTML =
            '<p>Ошибка загрузки календаря</p>';
    }
}

function renderCalendar(events) {
    const container = document.getElementById('calendar-content');

    if (currentView === 'month') {
        container.innerHTML = renderMonthView(events);
    } else {
        container.innerHTML = renderDayView(events);
    }
}

function renderMonthView(events) {
    const monthNames = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                       'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];

    const firstDay = new Date(currentYear, currentMonth - 1, 1);
    const lastDay = new Date(currentYear, currentMonth, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay() + (firstDay.getDay() === 0 ? -6 : 1));

    let calendarHTML = `
        <div class="month-view">
            <table class="calendar-table">
                <thead>
                    <tr>
                        <th>Пн</th>
                        <th>Вт</th>
                        <th>Ср</th>
                        <th>Чт</th>
                        <th>Пт</th>
                        <th>Сб</th>
                        <th>Вс</th>
                    </tr>
                </thead>
                <tbody>
    `;

    let currentDate = new Date(startDate);

    for (let week = 0; week < 6; week++) {
        calendarHTML += '<tr>';

        for (let dayOfWeek = 0; dayOfWeek < 7; dayOfWeek++) {
            const dayEvents = events.filter(event => {
                const eventDate = new Date(event.start_time);
                return eventDate.toDateString() === currentDate.toDateString();
            });

            const isCurrentMonth = currentDate.getMonth() === currentMonth - 1;
            const isToday = currentDate.toDateString() === new Date().toDateString();

            calendarHTML += `
                <td class="calendar-day ${!isCurrentMonth ? 'other-month' : ''} ${isToday ? 'today' : ''}">
                    <div class="day-header">
                        <span class="day-number">${currentDate.getDate()}</span>
                        ${dayEvents.length > 3 ? `<span class="events-badge">+${dayEvents.length - 3}</span>` : ''}
                    </div>
                    <div class="day-events">
            `;

            dayEvents.slice(0, 3).forEach(event => {
                const timeStr = event.all_day ? 'Весь день' : new Date(event.start_time).toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit'});
                calendarHTML += `
                    <div class="calendar-event ${event.event_type.toLowerCase()}"
                         style="border-left: 3px solid ${event.color}">
                        <small>${timeStr}</small>
                        <div class="event-title">
                            <a title="${event.title}">
                                ${event.title.length > 15 ? event.title.substring(0, 15) + '...' : event.title}
                            </a>
                        </div>
                    </div>
                `;
            });

            calendarHTML += `
                    </div>
                </td>
            `;

            currentDate.setDate(currentDate.getDate() + 1);
        }

        calendarHTML += '</tr>';

        if (currentDate > lastDay) {
            break;
        }
    }

    calendarHTML += `
                </tbody>
            </table>
        </div>
    `;

    return calendarHTML;
}

function renderDayView(events) {
    const dayEvents = events.filter(event => {
        const eventDate = new Date(event.start_time);
        return eventDate.toDateString() === new Date(currentYear, currentMonth - 1, currentDay).toDateString();
    });

    let calendarHTML = `
        <div class="day-view">
            <div class="day-header-large">
                <h2>${currentDay} ${getMonthName(currentMonth)} ${currentYear}</h2>
            </div>
            <div class="day-events-list">
    `;

    if (dayEvents.length === 0) {
        calendarHTML += `
            <div class="no-events">
                <p>На этот день событий нет</p>
            </div>
        `;
    } else {
        dayEvents.forEach(event => {
            const timeStr = event.all_day ?
                '<strong>Весь день</strong>' :
                `<strong>${new Date(event.start_time).toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit'})} - ${new Date(event.end_time).toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit'})}</strong>`;

            calendarHTML += `
                <div class="day-event-item ${event.event_type.toLowerCase()}">
                    <div class="event-time">
                        ${timeStr}
                    </div>
                    <div class="event-details">
                        <div class="event-header">
                            <span class="event-type-badge ${event.event_type.toLowerCase()}">
                                ${event.event_type === 'TASK' ? 'Задача' : 'Встреча'}
                            </span>
                            <h4 class="event-title"><a href="${event.url}">${event.title}</a></h4>
                        </div>
                        ${event.description ? `<p class="event-description">${event.description}</p>` : ''}
                        <div class="event-meta">
                            ${event.event_type === 'TASK' ? `<span class="task-status status-${event.status.toLowerCase()}">${getStatusText(event.status)}</span>` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
    }

    calendarHTML += `
            </div>
        </div>
    `;

    return calendarHTML;
}

function getMonthName(month) {
    const months = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                   'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
    return months[month];
}

function getStatusText(status) {
    const statusMap = {
        'OPEN': 'Открыта',
        'IN_PROGRESS': 'В процессе',
        'COMPLETED': 'Завершена'
    };
    return statusMap[status] || status;
}

document.addEventListener('DOMContentLoaded', async () => {
    const isAuthenticated = await checkAuth();
    if (isAuthenticated) {
        await loadCalendarEvents();
    }
});