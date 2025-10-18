// utils.js
// Utility module providing DOM helpers, storage abstraction, and debouncing.

/**
 * Select a single DOM element.
 * @param {string} selector - CSS selector string.
 * @returns {Element|null} The first matching element or null.
 */
export function $(selector) {
  return document.querySelector(selector);
}

/**
 * Select multiple DOM elements.
 * @param {string} selector - CSS selector string.
 * @returns {Element[]} Array of matching elements.
 */
export function $$(selector) {
  return Array.from(document.querySelectorAll(selector));
}

/**
 * Create a new DOM element with optional class, attributes, and children.
 * @param {string} tag - Tag name for the element.
 * @param {Object} [options] - Options for the element.
 * @param {string} [options.className] - Class name(s) to assign.
 * @param {Object} [options.attrs] - Attributes to set (key/value pairs).
 * @param {(string|Node)[]} [options.children] - Child nodes or text strings.
 * @returns {Element} The created element.
 */
export function createEl(tag, { className, attrs, children } = {}) {
  const el = document.createElement(tag);

  if (className) {
    el.className = className;
  }

  if (attrs) {
    for (const [key, value] of Object.entries(attrs)) {
      el.setAttribute(key, value);
    }
  }

  if (children) {
    children.forEach((child) => {
      if (typeof child === 'string') {
        el.appendChild(document.createTextNode(child));
      } else if (child instanceof Node) {
        el.appendChild(child);
      }
    });
  }

  return el;
}

/**
 * Storage abstraction for tasks and theme settings.
 * Uses localStorage under specific keys.
 */
export const storage = {
  /**
   * Save tasks array to localStorage.
   * @param {any[]} tasks - Array of task objects.
   */
  saveTasks(tasks) {
    try {
      const serialized = JSON.stringify(tasks);
      localStorage.setItem('colorfulTodoTasks', serialized);
    } catch (e) {
      console.error('Failed to save tasks to storage:', e);
    }
  },

  /**
   * Load tasks array from localStorage.
   * @returns {any[]} Parsed tasks array or empty array on failure.
   */
  loadTasks() {
    try {
      const stored = localStorage.getItem('colorfulTodoTasks');
      if (stored) {
        const parsed = JSON.parse(stored);
        return Array.isArray(parsed) ? parsed : [];
      }
    } catch (e) {
      console.error('Failed to load tasks from storage:', e);
    }
    return [];
  },

  /**
   * Save theme identifier to localStorage.
   * @param {string} theme - Theme name or identifier.
   */
  saveTheme(theme) {
    try {
      localStorage.setItem('colorfulTodoTheme', theme);
    } catch (e) {
      console.error('Failed to save theme to storage:', e);
    }
  },

  /**
   * Load theme identifier from localStorage.
   * @returns {string|null} Stored theme or null if not set.
   */
  loadTheme() {
    try {
      return localStorage.getItem('colorfulTodoTheme');
    } catch (e) {
      console.error('Failed to load theme from storage:', e);
      return null;
    }
  },
};

/**
 * Create a debounced version of a function.
 * The debounced function delays invoking `fn` until after `delay` ms have elapsed
 * since the last time the debounced function was called.
 * @param {Function} fn - Function to debounce.
 * @param {number} delay - Delay in milliseconds.
 * @returns {Function} Debounced function.
 */
export function debounce(fn, delay) {
  let timerId;
  return function (...args) {
    const context = this;
    clearTimeout(timerId);
    timerId = setTimeout(() => fn.apply(context, args), delay);
  };
}
