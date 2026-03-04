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

        // Detect if it's a Raspberry Pi or similar ARM Linux touchscreen
        // navigator.platform is deprecated but still useful for this specific case
        const platform = navigator.platform || '';
        const userAgent = navigator.userAgent || '';
        
        const isLinux = /Linux/.test(platform) || /Linux/.test(userAgent);
        const isArm = /arm|aarch64/.test(platform) || /arm|aarch64/.test(userAgent);
        const hasTouch = (('ontouchstart' in window) || (navigator.maxTouchPoints > 0));
        
        // Exclude common mobile/tablet platforms to be precise
        const isMobileOrTablet = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);

        // We target: Linux + ARM + Touch - (Common Mobile/Tablets)
        return isLinux && isArm && hasTouch && !isMobileOrTablet;
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.className = 'virtual-keyboard';
        document.body.appendChild(this.container);

        // Prevent keyboard from closing when clicking inside it
        this.container.addEventListener('mousedown', (e) => {
            e.preventDefault();
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

        // Listen for clicks outside to close
        document.addEventListener('mousedown', (e) => {
            if (this.visible &&
                !this.container.contains(e.target) &&
                e.target !== this.currentInput) {
                this.hide();
            }
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
        if (!el) return false;
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
        if (this.currentInput) {
            // Restore original type if switched
            const originalType = this.currentInput.getAttribute('data-original-type');
            if (originalType) {
                // Ensure value is valid number before switching back, or it might get cleared
                let val = this.currentInput.value;
                // If it ends with a dot, remove it or append 0? Usually remove is safer for valid number.
                if (val.endsWith('.')) {
                    this.currentInput.value = val.slice(0, -1);
                }
                this.currentInput.type = originalType;
                this.currentInput.removeAttribute('data-original-type');
            }
        }

        this.visible = false;
        this.container.classList.remove('active');
        this.currentInput = null;
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
