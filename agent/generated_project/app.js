document.addEventListener('DOMContentLoaded', function () {
    const taskList = document.getElementById('taskList');
    const newTaskTitleInput = document.getElementById('newTaskTitle');
    const newTaskDescriptionInput = document.getElementById('newTaskDescription');
    const addTaskButton = document.getElementById('addTaskButton');

    // Load tasks from local storage
    let tasks = JSON.parse(localStorage.getItem('tasks')) || [];

    function updateTaskList() {
        taskList.innerHTML = '';
        tasks.forEach((task, index) => {
            const listItem = document.createElement('li');

            listItem.innerHTML = `
                <input type="checkbox" id="task-${index}" ${task.completed ? 'checked' : ''} onchange="toggleComplete(${index})">
                <label for="task-${index}"><h3 class='${task.completed ? 'completed-text' : ''}'>${task.title}</h3></label>
                <p class='${task.completed ? 'completed-text' : ''}'>${task.description || ''}</p>
                <button onclick="removeTask(${index})">Remove</button>
            `;

            listItem.classList.toggle('completed', task.completed);

            taskList.appendChild(listItem);
        });
    }

    function saveTasks() {
        localStorage.setItem('tasks', JSON.stringify(tasks));
    }

    window.removeTask = function (index) {
        tasks.splice(index, 1);
        saveTasks();
        updateTaskList();
    };

    window.toggleComplete = function (index) {
        tasks[index].completed = !tasks[index].completed;
        saveTasks();
        updateTaskList();
    };

    addTaskButton.addEventListener('click', function () {
        const title = newTaskTitleInput.value.trim();
        const description = newTaskDescriptionInput.value.trim();

        if (title !== '') {
            const newTask = {
                title: title,
                description: description,
                completed: false
            };

            tasks.push(newTask);
            saveTasks();
            updateTaskList();

            newTaskTitleInput.value = '';
            newTaskDescriptionInput.value = '';
        }
    });

    updateTaskList();
});