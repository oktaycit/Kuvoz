/**
 * Virtual Keyboard for Kuvoz
 * Supports Turkish character set and context-aware layouts.
 */

class VirtualKeyboard {
    constructor() {
        this.currentInput = null;
        this.layout = 'lowercase'; // lowercase, uppercase, symbols, numeric
        this.visible = false;
        this.language = 'tr';
        this.manualCursorPos = 0; // Track cursor for inputs that don't support selectionStart
        this.startEvents = window.PointerEvent ? ['pointerdown'] : ['mousedown', 'touchstart'];

        this.layouts = {
            lowercase: [
                ["q", "w", "e", "r", "t", "y", "u", "ı", "o", "p", "ğ", "ü"],
                ["a", "s", "d", "f", "g", "h", "j", "k", "l", "ş", "i"],
                ["shift", "z", "x", "c", "v", "b", "n", "m", "ö", "ç", "backspace"],
                ["?123", "space", ".", "enter"]
            ],
            uppercase: [
                ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "Ğ", "Ü"],
                ["A", "S", "D", "F", "G", "H", "J", "K", "L", "Ş", "İ"],
                ["shift", "Z", "X", "C", "V", "B", "N", "M", "Ö", "Ç", "backspace"],
                ["?123", "space", ".", "enter"]
            ],
            symbols: [
                ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
                ["@", "#", "$", "%", "&", "-", "+", "(", ")", "/"],
                ["*", "\"", "'", ":", ";", "!", "?", "ß", "ä", "backspace"],
                ["abc", "space", ",", "enter"]
            ],
            numeric: [
                ["1", "2", "3"],
                ["4", "5", "6"],
                ["7", "8", "9"],
                [".", "0", "backspace"],
                ["enter"]
            ]
        };

        this.init();
    }

    init() {
        if (!this.shouldInitialize()) return;
        
        this.createContainer();
        this.attachListeners();
    }

    shouldInitialize() {
        // Force keyboard via URL parameter for debugging/testing
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('forceKeyboard')) return true;
        if (urlParams.has('disableKeyboard')) return false;

        // Enable only on the device-local kiosk browser.
        return this.isLocalhost() && this.isTouchCapable();
    }

    isLocalhost() {
        const hostname = (window.location.hostname || '')
            .replace(/^\[/, '')
            .replace(/\]$/, '')
            .toLowerCase();

        return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1';
    }

    isTouchCapable() {
        return ('ontouchstart' in window) ||
            (navigator.maxTouchPoints || 0) > 0 ||
            (navigator.msMaxTouchPoints || 0) > 0;
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.className = 'virtual-keyboard';
        document.body.appendChild(this.container);

        // Prevent keyboard from closing when clicking inside it
        this.startEvents.forEach((eventName) => {
            this.container.addEventListener(eventName, (e) => {
                e.preventDefault();
            });
        });
    }

    attachListeners() {
        // Listen for focus events on inputs
        document.addEventListener('focusin', (e) => {
            const target = e.target;
            if (this.isTextField(target)) {
                this.show(target);
            }
        });

        // Hide when focus leaves editable fields.
        document.addEventListener('focusout', (e) => {
            if (e.target !== this.currentInput) return;

            window.setTimeout(() => {
                const activeElement = document.activeElement;
                if (this.isTextField(activeElement)) {
                    this.show(activeElement);
                    return;
                }

                if (!this.container.contains(activeElement)) {
                    this.hide();
                }
            }, 0);
        });

        // Listen for clicks outside to close
        this.startEvents.forEach((eventName) => {
            document.addEventListener(eventName, (e) => {
                if (this.visible &&
                    !this.container.contains(e.target) &&
                    e.target !== this.currentInput) {
                    this.hide();
                }
            });
        });

        // Listen for clicks on inputs to potentially sync cursor
        document.addEventListener('click', (e) => {
            if (this.currentInput && e.target === this.currentInput) {
                this.syncCursor();
            }
        });

        // Window resize may affect position
        window.addEventListener('resize', () => {
            if (this.visible) this.render();
        });
    }

    isTextField(el) {
        if (!el || el.disabled || el.readOnly) return false;
        const tag = el.tagName.toLowerCase();
        if (tag === 'textarea') return true;
        if (tag === 'input') {
            const type = el.type.toLowerCase();
            const textTypes = ['text', 'number', 'password', 'email', 'tel', 'search', 'url'];
            return textTypes.includes(type);
        }
        return false;
    }

    show(input) {
        if (!this.isTextField(input)) {
            this.hide();
            return;
        }

        if (this.currentInput && this.currentInput !== input) {
            this.restoreInputType(this.currentInput);
        }

        this.currentInput = input;
        this.visible = true;

        // Handle numeric input type switching to allow partial decimals (e.g. "1.")
        if (input.type === 'number') {
            input.setAttribute('data-original-type', 'number');
            input.type = 'text';
            this.layout = 'numeric';
            this.container.classList.add('numeric-only');
        } else {
            this.layout = 'lowercase';
            this.container.classList.remove('numeric-only');
        }

        // Sync tracker with existing value
        this.manualCursorPos = input.value.length;
        this.syncCursor();

        this.render();

        // Small delay to ensure CSS transition works
        setTimeout(() => {
            this.container.classList.add('active');
            this.scrollIntoView();
        }, 10);
    }

    syncCursor() {
        if (!this.currentInput) return;
        try {
            const start = this.currentInput.selectionStart;
            if (start !== null) {
                this.manualCursorPos = start;
            }
        } catch (e) {
            // Keep current manual position
        }
    }

    hide() {
        this.restoreInputType(this.currentInput);

        this.visible = false;
        this.container.classList.remove('active');
        this.container.classList.remove('numeric-only');
        this.currentInput = null;
    }

    restoreInputType(input) {
        if (!input) return;

        const originalType = input.getAttribute('data-original-type');
        if (!originalType) return;

        // Ensure value is valid number before switching back, or it might get cleared.
        const val = input.value;
        if (val.endsWith('.')) {
            input.value = val.slice(0, -1);
        }

        input.type = originalType;
        input.removeAttribute('data-original-type');
    }

    scrollIntoView() {
        if (!this.currentInput) return;
        const inputRect = this.currentInput.getBoundingClientRect();
        const kbRect = this.container.getBoundingClientRect();
        if (inputRect.bottom > kbRect.top) {
            this.currentInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    render() {
        this.container.innerHTML = '';
        const rows = this.layouts[this.layout];
        rows.forEach(row => {
            const rowEl = document.createElement('div');
            rowEl.className = 'keyboard-row';
            row.forEach(key => {
                const keyEl = this.createKey(key);
                rowEl.appendChild(keyEl);
            });
            this.container.appendChild(rowEl);
        });
    }

    createKey(key) {
        const keyEl = document.createElement('div');
        keyEl.className = 'keyboard-key';
        let label = key;
        let action = () => this.insertChar(key);

        switch (key) {
            case 'backspace':
                keyEl.classList.add('special', 'backspace', 'wide');
                label = '<i class="fas fa-backspace"></i>';
                action = () => this.backspace();
                break;
            case 'shift':
                keyEl.classList.add('special', 'wide');
                label = '<i class="fas fa-arrow-up"></i>';
                action = () => this.toggleShift();
                if (this.layout === 'uppercase') keyEl.classList.add('action');
                break;
            case 'space':
                keyEl.classList.add('extra-wide');
                label = '&nbsp;';
                action = () => this.insertChar(' ');
                break;
            case 'enter':
                keyEl.classList.add('action', 'wide');
                label = '<i class="fas fa-check"></i>';
                action = () => this.hide();
                break;
            case '?123':
                keyEl.classList.add('special', 'wide');
                label = '?123';
                action = () => this.setLayout('symbols');
                break;
            case 'abc':
                keyEl.classList.add('special', 'wide');
                label = 'abc';
                action = () => this.setLayout('lowercase');
                break;
        }

        keyEl.innerHTML = label;
        keyEl.addEventListener('click', (e) => {
            e.preventDefault();
            action();
            if (this.currentInput) this.currentInput.focus();
        });
        return keyEl;
    }

    insertChar(char) {
        if (!this.currentInput) return;

        let start, end;
        try {
            start = this.currentInput.selectionStart;
            end = this.currentInput.selectionEnd;
            if (start === null) start = end = this.manualCursorPos;
        } catch (e) {
            start = end = this.manualCursorPos;
        }

        const value = this.currentInput.value;
        const newValue = value.substring(0, start) + char + value.substring(end);
        this.currentInput.value = newValue;

        this.manualCursorPos = start + char.length;
        try {
            this.currentInput.setSelectionRange(this.manualCursorPos, this.manualCursorPos);
        } catch (e) { }

        this.currentInput.dispatchEvent(new Event('input', { bubbles: true }));
        this.currentInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    backspace() {
        if (!this.currentInput) return;

        let start, end;
        try {
            start = this.currentInput.selectionStart;
            end = this.currentInput.selectionEnd;
            if (start === null) start = end = this.manualCursorPos;
        } catch (e) {
            start = end = this.manualCursorPos;
        }

        const value = this.currentInput.value;
        if (start === end && start > 0) {
            this.currentInput.value = value.substring(0, start - 1) + value.substring(end);
            this.manualCursorPos = start - 1;
        } else if (start !== end) {
            this.currentInput.value = value.substring(0, start) + value.substring(end);
            this.manualCursorPos = start;
        }

        try {
            this.currentInput.setSelectionRange(this.manualCursorPos, this.manualCursorPos);
        } catch (e) { }

        this.currentInput.dispatchEvent(new Event('input', { bubbles: true }));
        this.currentInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    toggleShift() {
        this.layout = this.layout === 'lowercase' ? 'uppercase' : 'lowercase';
        this.render();
    }

    setLayout(name) {
        this.layout = name;
        this.render();
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    window.vKeyboard = new VirtualKeyboard();
});
