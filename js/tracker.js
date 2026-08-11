function updateTodayProgress(summaryData, totalTasks) {

    const progress = document.getElementById("todayProgressContainer");

    if (!progress) return;

    const completed = summaryData.completed_tasks || 0;
    const remaining = Math.max(totalTasks - completed, 0);

    const percentage = totalTasks > 0
        ? Math.round((completed / totalTasks) * 100)
        : 0;

    const completedNames = summaryData.completed_task_names || [];

    let completedHTML = "";

    if (completedNames.length > 0) {

        completedHTML = `
            <div class="tracker-completed-list">
                <h3>Completed Today</h3>

                ${completedNames.map(name => `
                    <p>✅ ${name}</p>
                `).join("")}
            </div>
        `;

    } else {

        completedHTML = `
            <p>No tasks completed yet. Start your first wellness activity!</p>
        `;
    }

    const goalMessage = percentage === 100
        ? `<p><strong>🎉 Daily Wellness Goal Completed!</strong></p>`
        : `<p>🎯 ${remaining} task${remaining !== 1 ? "s" : ""} remaining</p>`;

    progress.innerHTML = `

        <div class="tracker-progress-wrapper">

            <div class="tracker-progress-header">

                <h3>${percentage}% Complete</h3>

                <span>
                    ${completed} of ${totalTasks} tasks completed
                </span>

            </div>

            <div class="tracker-progress-bar">

                <div
                    class="tracker-progress-fill"
                    style="width:${percentage}%">
                </div>

            </div>

            <div class="tracker-progress-stats">

                <div>
                    <strong>⭐ ${summaryData.points}</strong>
                    <span>Total Points</span>
                </div>

                <div>
                    <strong>🔥 ${summaryData.streak}</strong>
                    <span>Day Streak</span>
                </div>

                <div>
                    <strong>🎯 ${remaining}</strong>
                    <span>Remaining</span>
                </div>

            </div>

            ${goalMessage}

            ${completedHTML}

        </div>
    `;
}
document.addEventListener("DOMContentLoaded", () => {

    const summary = document.getElementById("trackerSummaryCards");

    const tasks = document.getElementById("todayTaskContainer");

    const progress = document.getElementById("todayProgressContainer");

    async function loadTrackerSummary(token, totalTasks = 5) {
    try {
        const response = await fetch(`${API_BASE_URL}/tracker/summary`, {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${token}`
            },
            cache: "no-store"
        });

        const data = await response.json();

        if (!response.ok) {
            console.error("Summary error:", data);
            return [];
        }

        const summary = document.getElementById("trackerSummaryCards");

        if (summary) {
            summary.innerHTML = `
                <div class="tracker-metric-grid">

                    <div class="tracker-metric-card">
                        <h3>⭐ Points</h3>
                        <h1>${data.points}</h1>
                    </div>

                    <div class="tracker-metric-card">
                        <h3>🔥 Streak</h3>
                        <h1>${data.streak}</h1>
                    </div>

                    <div class="tracker-metric-card">
                        <h3>🏆 Rank</h3>
                        <h1>#${data.rank}</h1>
                    </div>

                    <div class="tracker-metric-card">
                        <h3>✅ Tasks</h3>
                        <h1>${data.completed_tasks}/${totalTasks}</h1>
                    </div>

                </div>
            `;
        }
        updateTodayProgress(data, totalTasks);

        return data.completed_task_names || [];

    } catch (error) {
        console.error("Unable to load tracker summary:", error);
        return [];
    }
}

    if(tasks){

        const session = getSession();

if (!session || !session.token) {
    tasks.innerHTML = `<p>Please sign in again.</p>`;
    return;
}

const token = session.token;

fetch(`${API_BASE_URL}/recommendations`, {
    method: "GET",
    headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
    },
    cache: "no-store"
})
    .then(response => response.json())
    .then(async data => { 

        let html = "";

        const recommendations = Object.values(data.recommendations);
        const completedTaskNames = await loadTrackerSummary(
    token,
    recommendations.length
);

recommendations.forEach(task => {
    const isCompleted = completedTaskNames.includes(task.title);

    const priority = task.needs_improvement ? "high" : "low";

    html += `

    <div class="tracker-task-card">

        <div class="tracker-task-header">

            <h3>${task.title}</h3>

            <span class="tracker-priority ${priority}">
                ${task.category}
            </span>

        </div>

        <p>${task.description}</p>

        <div class="tracker-task-footer">

            <button
    class="btn-primary tracker-complete-btn"
    data-task-name="${task.title}"
    data-category="${task.category}"
    ${isCompleted ? "disabled" : ""}
>
    ${isCompleted ? "✅ Completed" : "✅ Complete"}
</button>

            <button class="btn-secondary tracker-view-recommendation-btn"
        data-task-name="${task.title}"
        data-category="${task.category}">
    📖 View Recommendation
</button>

        </div>

    </div>

    `;

});

tasks.innerHTML = html;
document.querySelectorAll(".tracker-complete-btn").forEach(button => {

    button.addEventListener("click", async () => {

    const taskName = button.dataset.taskName;
    const category = button.dataset.category;

    const session = getSession();

    if (!session || !session.token) {
        alert("Session expired. Please sign in again.");
        return;
    }

    const token = session.token;

    try {

        const response = await fetch("/api/tracker/complete", {
            method: "POST",

            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },

            body: JSON.stringify({
                task_name: taskName,
                category: category
            })
        });

        const data = await response.json();

        if (!response.ok) {
            console.error("Tracker API error:", data);
            alert(data.message || "Unable to complete task");
            return;
        }

        button.innerHTML = "✅ Completed";
        button.disabled = true;

        alert(`Task completed! +${data.points_earned} points`);
        await loadTrackerSummary(token, recommendations.length);

        console.log("Tracker result:", data);

    } catch (error) {

    console.error("Tracker error:", error);

    alert(
        "Unable to connect to tracker API.\n\n" +
        "Error: " + error.message
    );

}
});

});
document.querySelectorAll(".tracker-view-recommendation-btn").forEach(button => {

    button.addEventListener("click", () => {

        const taskName = button.dataset.taskName;
        const category = button.dataset.category;

        // Save which recommendation should be highlighted
        sessionStorage.setItem("highlightRecommendationTask", taskName);
        sessionStorage.setItem("highlightRecommendationCategory", category);

        // Open Wellness Recommendations section
        const recommendationsNav = document.querySelector(
            '[data-view="recommendationsView"]'
        );

        if (recommendationsNav) {
            recommendationsNav.click();
        }

    });

});

    })
    .catch(error => {

        console.error(error);

        tasks.innerHTML = `
            <p>Unable to load today's wellness tasks.</p>
        `;

    });
    }


});