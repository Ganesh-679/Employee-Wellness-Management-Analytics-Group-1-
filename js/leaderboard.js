document.addEventListener("DOMContentLoaded", async () => {

    const container = document.getElementById("leaderboardContainer");

    if (!container) {
        console.error("leaderboardContainer not found");
        return;
    }

    const session = getSession();

    if (!session || !session.token) {
        container.innerHTML = "<p>Please sign in again.</p>";
        return;
    }

    try {

        const response = await fetch(`${API_BASE_URL}/leaderboard`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${session.token}`
            },
            cache: "no-store"
        });

        const data = await response.json();

        if (!response.ok) {
            console.error("Leaderboard API error:", data);
            container.innerHTML = "<p>Unable to load leaderboard.</p>";
            return;
        }

        const leaderboard = data.leaderboard;

        if (!leaderboard || leaderboard.length === 0) {
            container.innerHTML = "<p>No leaderboard data available.</p>";
            return;
        }

        let html = `
            <div class="leaderboard-table-wrapper">

                <table class="leaderboard-table">

                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Employee</th>
                            <th>Points</th>
                            <th>Tasks Completed</th>
                            <th>Streak</th>
                        </tr>
                    </thead>

                    <tbody>
        `;

        leaderboard.forEach(employee => {

            let rankDisplay = `#${employee.rank}`;

            if (employee.rank === 1) {
                rankDisplay = "🥇 #1";
            } else if (employee.rank === 2) {
                rankDisplay = "🥈 #2";
            } else if (employee.rank === 3) {
                rankDisplay = "🥉 #3";
            }

            html += `
                <tr class="${employee.is_current_user ? "current-user-row" : ""}">

                    <td class="leaderboard-rank">
                        ${rankDisplay}
                    </td>

                    <td>
                        <strong>${employee.employee_name}</strong>
                        ${employee.is_current_user
                            ? '<span class="you-badge">You</span>'
                            : ''}
                    </td>

                    <td>
                        ⭐ ${employee.points}
                    </td>

                    <td>
                        ✅ ${employee.tasks_completed}
                    </td>

                    <td>
                        🔥 ${employee.streak}
                    </td>

                </tr>
            `;
        });

        html += `
                    </tbody>

                </table>

            </div>
        `;

        container.innerHTML = html;

    } catch (error) {

        console.error("Leaderboard error:", error);

        container.innerHTML = `
            <p>Unable to connect to leaderboard API.</p>
        `;
    }

});