// Initialize DOM element references
export const input = document.getElementById('new-task-input');
export const taskList = document.getElementById('task-list');
export const filterButtons = document.querySelectorAll('.filters button');

// Global state
export let tasks = [];
export let currentFilter = 'all';

/**
 * Load tasks from localStorage.
 * Reads the JSON string stored under the key 'vividTodoTasks',
 * parses it, and populates the global `tasks` array.
 * If no data exists or parsing fails, `tasks` remains an empty array.
 */
export function loadTasksFromStorage() {
  try {
    const stored = localStorage.getItem('vividTodoTasks');
    if (stored) {
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed)) {
        tasks = parsed;
      }
    }
  } catch (e) {
    console.error('Failed to load tasks from storage:', e);
    tasks = [];
  }
}

/**
 * Save the current tasks array to localStorage.
 * Serializes `tasks` as JSON and stores it under the key 'vividTodoTasks'.
 */
export function saveTasksToStorage() {
  try {
    const serialized = JSON.stringify(tasks);
    localStorage.setItem('vividTodoTasks', serialized);
  } catch (e) {
    console.error('Failed to save tasks to storage:', e);
  }
}

// Load tasks immediately when the script is evaluated.
loadTasksFromStorage();
