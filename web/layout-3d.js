(function () {
    const canvas = document.getElementById('layout3dCanvas');
    const ctx = canvas.getContext('2d');

    const layers = {
        shell: true,
        exterior: true,
        zones: true,
        power: true,
        control: true,
        safety: true,
        airflow: true
    };

    const state = {
        rotX: -0.62,
        rotY: 0.78,
        zoom: 0.92,
        panX: 0,
        panY: 0,
        dragging: false,
        lastX: 0,
        lastY: 0
    };

    const palette = {
        shell: '#dfeae3',
        technical: '#cfdcd5',
        chamber: '#f0f4f2',
        acZone: '#f4d4b2',
        dcZone: '#b9e1dc',
        logicZone: '#d7e7bc',
        relay: '#d96d4b',
        mosfet: '#16867e',
        pi: '#7db44e',
        power12: '#6aa4d8',
        power5: '#4ca0b6',
        terminal: '#5c6d67',
        fan: '#5e7fcf',
        plenum: '#9bb8da',
        inlet: '#444b55',
        switch: '#c94b4b',
        fuse: '#c6c0b2',
        cableAc: '#d08e46',
        cableDc: '#28a27e',
        vent: '#7f6ed6',
        safety: '#d7a34b',
        drain: '#9a7b3b',
        uv: '#b56be0',
        ozone: '#e38e43',
        bed: '#cdb5a2',
        displayPod: '#8b6a4f',
        displayMount: '#6d7f86',
        displayGlass: '#101418',
        displayView: '#f08a4b'
    };

    const objects = [
        {
            id: 'outer-shell',
            label: 'Kabin Dış Hacim',
            layer: 'shell',
            position: [399.05, 299.025, 287.2],
            size: [798.1, 598.05, 574.4],
            color: palette.shell,
            alpha: 0.12,
            stroke: 'rgba(54, 72, 64, 0.26)'
        },
        {
            id: 'technical-bay',
            label: 'Teknik Bölme',
            layer: 'shell',
            position: [70, 299.025, 287.2],
            size: [140, 598.05, 574.4],
            color: palette.technical,
            alpha: 0.18,
            stroke: 'rgba(54, 72, 64, 0.26)'
        },
        {
            id: 'patient-chamber',
            label: 'Hasta Hacmi',
            layer: 'shell',
            position: [469.05, 299.025, 287.2],
            size: [658.1, 558.05, 534.4],
            color: palette.chamber,
            alpha: 0.08,
            stroke: 'rgba(80, 96, 89, 0.14)'
        },
        {
            id: 'front-door',
            label: 'Ön Kapı / Şeffaf Panel',
            layer: 'exterior',
            position: [470, 23, 287],
            size: [620, 10, 500],
            color: '#d8f4f4',
            alpha: 0.18,
            stroke: 'rgba(71, 131, 136, 0.28)'
        },
        {
            id: 'top-cover',
            label: 'Üst Kapak',
            layer: 'exterior',
            position: [470, 299, 560],
            size: [700, 560, 12],
            color: '#e7eee9',
            alpha: 0.16,
            stroke: 'rgba(54, 72, 64, 0.18)'
        },
        {
            id: 'base-floor',
            label: 'Alt Taban',
            layer: 'exterior',
            position: [399, 299, 18],
            size: [790, 590, 16],
            color: '#cad9d1',
            alpha: 0.34,
            stroke: 'rgba(54, 72, 64, 0.18)'
        },
        {
            id: 'left-side',
            label: 'Sol Yan Panel',
            layer: 'exterior',
            position: [6, 299, 287],
            size: [12, 598, 560],
            color: '#d7e2dc',
            alpha: 0.2,
            stroke: 'rgba(54, 72, 64, 0.18)'
        },
        {
            id: 'right-side',
            label: 'Sağ Yan Panel',
            layer: 'exterior',
            position: [792, 299, 287],
            size: [12, 598, 560],
            color: '#d7e2dc',
            alpha: 0.18,
            stroke: 'rgba(54, 72, 64, 0.18)'
        },
        {
            id: 'back-panel',
            label: 'Arka Panel',
            layer: 'exterior',
            position: [399, 590, 287],
            size: [790, 12, 560],
            color: '#d7e2dc',
            alpha: 0.18,
            stroke: 'rgba(54, 72, 64, 0.18)'
        },
        {
            id: 'patient-bed',
            label: 'Hasta Yatağı Referansı',
            layer: 'exterior',
            position: [455, 295, 82],
            size: [420, 250, 26],
            color: palette.bed,
            alpha: 0.72,
            stroke: 'rgba(99, 73, 58, 0.22)'
        },
        {
            id: 'zone-ac',
            label: 'AC Bölgesi',
            layer: 'zones',
            position: [28, 210, 248],
            size: [56, 250, 220],
            color: palette.acZone,
            alpha: 0.18
        },
        {
            id: 'zone-dc',
            label: 'DC Güç Bölgesi',
            layer: 'zones',
            position: [96, 300, 256],
            size: [62, 320, 260],
            color: palette.dcZone,
            alpha: 0.18
        },
        {
            id: 'zone-logic',
            label: 'Logic Bölgesi',
            layer: 'zones',
            position: [56, 110, 236],
            size: [76, 180, 180],
            color: palette.logicZone,
            alpha: 0.16
        },
        {
            id: 'service-deck',
            label: 'Yükseltilmiş Servis Rafı',
            layer: 'safety',
            position: [73, 300, 180],
            size: [118, 506, 8],
            color: palette.safety,
            alpha: 0.58
        },
        {
            id: 'technical-service-cover',
            label: 'Teknik Servis Kapağı',
            layer: 'safety',
            position: [70, 3.75, 296],
            size: [126, 1.5, 452],
            color: palette.technical,
            alpha: 0.5,
            stroke: 'rgba(54, 72, 64, 0.24)'
        },
        {
            id: 'display-pod-shell',
            label: 'Ön Sağ Ekran Podu',
            layer: 'safety',
            position: [77.98, 11.13, 287.45],
            size: [123.97, 68.71, 188],
            color: palette.displayPod,
            alpha: 0.34,
            stroke: 'rgba(76, 54, 35, 0.32)'
        },
        {
            id: 'display-carrier',
            label: 'Ekran Taşıyıcı Plaka',
            layer: 'safety',
            position: [73.85, 0.93, 287.45],
            size: [115.72, 48.31, 188],
            color: palette.displayMount,
            alpha: 0.52,
            stroke: 'rgba(70, 88, 94, 0.3)'
        },
        {
            id: 'display-module',
            label: '7 inç Dikey Ekran',
            layer: 'safety',
            position: [44.64, 60.71, 287.45],
            size: [47.48, 102.17, 164.9],
            color: palette.displayGlass,
            alpha: 0.88,
            stroke: 'rgba(15, 20, 24, 0.36)'
        },
        {
            id: 'display-view',
            label: 'Aktif Görünür Alan',
            layer: 'safety',
            position: [47.0, 47.0, 287.45],
            size: [34.0, 84.0, 154.21],
            color: palette.displayView,
            alpha: 0.32,
            stroke: 'rgba(176, 90, 40, 0.25)'
        },
        {
            id: 'display-harness',
            label: 'Ekran Kablo Hacmi',
            layer: 'control',
            position: [99.87, 6.6, 287.45],
            size: [77.24, 52.93, 24],
            color: palette.logicZone,
            alpha: 0.26,
            stroke: 'rgba(72, 102, 60, 0.18)'
        },
        {
            id: 'drip-tray',
            label: 'Damla Toplama Tepsisi',
            layer: 'safety',
            position: [418, 299, 54],
            size: [700, 560, 12],
            color: palette.safety,
            alpha: 0.28,
            stroke: 'rgba(120, 86, 26, 0.24)'
        },
        {
            id: 'drain-gap',
            label: 'Drenaj / Servis Boşluğu',
            layer: 'safety',
            position: [760, 299, 46],
            size: [40, 520, 22],
            color: palette.drain,
            alpha: 0.36
        },
        {
            id: 'ac-inlet',
            label: 'J1 IEC Giriş',
            layer: 'power',
            position: [20, 174, 214],
            size: [28, 48, 31],
            color: palette.inlet,
            alpha: 0.95
        },
        {
            id: 'fuse',
            label: 'F1 Ana Sigorta',
            layer: 'power',
            position: [38, 179, 212],
            size: [20, 58, 20],
            color: palette.fuse,
            alpha: 0.96
        },
        {
            id: 'switch',
            label: 'S1 Ana Şalter',
            layer: 'power',
            position: [63, 175, 214],
            size: [22, 30, 26],
            color: palette.switch,
            alpha: 0.96
        },
        {
            id: 'earth',
            label: 'PE1 Toprak',
            layer: 'power',
            position: [23, 219, 28],
            size: [10, 10, 12],
            color: '#a48d2e',
            alpha: 0.95
        },
        {
            id: 'relay-board',
            label: 'Röle Kartı',
            layer: 'control',
            position: [38, 310, 286],
            size: [80, 130, 18],
            color: palette.relay,
            alpha: 0.93
        },
        {
            id: 'tb-ac',
            label: 'TB-AC-LOAD',
            layer: 'power',
            position: [26, 460, 300],
            size: [22, 110, 28],
            color: palette.terminal,
            alpha: 0.94
        },
        {
            id: 'psu12',
            label: 'PSU1 12V',
            layer: 'power',
            position: [107, 249.5, 268.5],
            size: [30, 159, 97],
            color: palette.power12,
            alpha: 0.92
        },
        {
            id: 'psu5',
            label: 'PSU2 5V',
            layer: 'power',
            position: [108.5, 414, 244],
            size: [25, 128, 60],
            color: palette.power5,
            alpha: 0.92
        },
        {
            id: 'tb-12v',
            label: 'TB-12V',
            layer: 'power',
            position: [27, 386, 310],
            size: [14, 72, 20],
            color: palette.terminal,
            alpha: 0.94
        },
        {
            id: 'mosfet-board',
            label: 'MOSFET Kartı',
            layer: 'control',
            position: [92, 360, 332],
            size: [70, 120, 18],
            color: palette.mosfet,
            alpha: 0.95
        },
        {
            id: 'tb-dc',
            label: 'TB-DC-LOAD',
            layer: 'power',
            position: [92, 500, 326],
            size: [18, 110, 28],
            color: palette.terminal,
            alpha: 0.94
        },
        {
            id: 'uv-output',
            label: 'UV Röle Çıkışı',
            layer: 'power',
            position: [30, 505, 312],
            size: [18, 24, 24],
            color: palette.uv,
            alpha: 0.96
        },
        {
            id: 'ozone-output',
            label: 'Ozon Röle Çıkışı',
            layer: 'power',
            position: [30, 540, 312],
            size: [18, 24, 24],
            color: palette.ozone,
            alpha: 0.96
        },
        {
            id: 'tb-5v',
            label: 'TB-5V',
            layer: 'power',
            position: [27, 152, 266],
            size: [14, 64, 20],
            color: palette.terminal,
            alpha: 0.94
        },
        {
            id: 'gpio-breakout',
            label: 'GPIO Breakout',
            layer: 'control',
            position: [98, 130, 296],
            size: [38, 62, 14],
            color: '#5f8f6a',
            alpha: 0.96
        },
        {
            id: 'rpi',
            label: 'Raspberry Pi',
            layer: 'control',
            position: [60.5, 100, 236.8],
            size: [85, 56, 1.6],
            color: palette.pi,
            alpha: 0.98
        },
        {
            id: 'fan',
            label: 'Fan',
            layer: 'airflow',
            position: [121, 554.75, 304.3],
            size: [38, 120, 120],
            color: palette.fan,
            alpha: 0.88
        },
        {
            id: 'plenum',
            label: 'Plenum',
            layer: 'airflow',
            position: [469.05, 554.75, 304.3],
            size: [616.5, 45, 498.6],
            color: palette.plenum,
            alpha: 0.16,
            stroke: 'rgba(61, 94, 144, 0.28)'
        },
        {
            id: 'fresh-air-inlet',
            label: 'Taze Hava Girişi',
            layer: 'airflow',
            position: [2, 295, 246],
            size: [5, 96, 180],
            color: palette.vent,
            alpha: 0.52
        },
        {
            id: 'plenum-outlet-slot-band',
            label: 'Plenum Çıkış Slotları',
            layer: 'airflow',
            position: [454, 532.75, 487.6],
            size: [560, 6, 20],
            color: palette.vent,
            alpha: 0.5
        },
        {
            id: 'exhaust-band',
            label: 'Egzoz Menfezleri',
            layer: 'airflow',
            position: [260.8, 597, 218],
            size: [86, 5, 146],
            color: palette.vent,
            alpha: 0.52
        },
        {
            id: 'ac-route',
            label: 'AC Kablo Hattı',
            layer: 'power',
            position: [19, 210, 196],
            size: [18, 120, 140],
            color: palette.cableAc,
            alpha: 0.42
        },
        {
            id: 'dc-route',
            label: 'DC Kablo Hattı',
            layer: 'power',
            position: [42, 350, 244],
            size: [16, 170, 120],
            color: palette.cableDc,
            alpha: 0.38
        },
        {
            id: 'logic-route',
            label: 'Logic Kablo Hattı',
            layer: 'control',
            position: [72, 170, 228],
            size: [12, 150, 106],
            color: '#80b193',
            alpha: 0.35
        },
        {
            id: 'airflow-path',
            label: 'Hava Akış Koridoru',
            layer: 'airflow',
            position: [315, 515, 320],
            size: [390, 36, 110],
            color: '#7da0da',
            alpha: 0.14,
            stroke: 'rgba(79, 106, 160, 0.18)'
        },
    ];

    function updateCanvasSize() {
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        canvas.width = Math.round(rect.width * dpr);
        canvas.height = Math.round(rect.height * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        render();
    }

    function rotatePoint(point) {
        const [x, y, z] = point;
        const cosY = Math.cos(state.rotY);
        const sinY = Math.sin(state.rotY);
        const cosX = Math.cos(state.rotX);
        const sinX = Math.sin(state.rotX);

        const x1 = x * cosY - y * sinY;
        const y1 = x * sinY + y * cosY;
        const z1 = z;

        const y2 = y1 * cosX - z1 * sinX;
        const z2 = y1 * sinX + z1 * cosX;

        return [x1, y2, z2];
    }

    function project(point) {
        const [x, y, z] = rotatePoint(point);
        const scale = Math.min(canvas.clientWidth, canvas.clientHeight) * 0.0023 * state.zoom;
        return {
            x: canvas.clientWidth / 2 + x * scale + state.panX,
            y: canvas.clientHeight / 2 - y * scale + state.panY,
            depth: z
        };
    }

    function getVertices(object) {
        const [cx, cy, cz] = object.position;
        const [sx, sy, sz] = object.size;
        const hx = sx / 2;
        const hy = sy / 2;
        const hz = sz / 2;

        return [
            [cx - hx, cy - hy, cz - hz],
            [cx + hx, cy - hy, cz - hz],
            [cx + hx, cy + hy, cz - hz],
            [cx - hx, cy + hy, cz - hz],
            [cx - hx, cy - hy, cz + hz],
            [cx + hx, cy - hy, cz + hz],
            [cx + hx, cy + hy, cz + hz],
            [cx - hx, cy + hy, cz + hz]
        ];
    }

    function averageDepth(vertices) {
        return vertices.reduce((sum, vertex) => sum + rotatePoint(vertex)[2], 0) / vertices.length;
    }

    function drawFace(projected, face, fill, stroke, alpha) {
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.beginPath();
        ctx.moveTo(projected[face[0]].x, projected[face[0]].y);
        for (let i = 1; i < face.length; i += 1) {
            ctx.lineTo(projected[face[i]].x, projected[face[i]].y);
        }
        ctx.closePath();
        ctx.fillStyle = fill;
        ctx.fill();
        if (stroke) {
            ctx.strokeStyle = stroke;
            ctx.lineWidth = 1;
            ctx.stroke();
        }
        ctx.restore();
    }

    function drawBox(object) {
        if (!layers[object.layer]) {
            return;
        }

        const vertices = getVertices(object);
        const projected = vertices.map(project);
        const faces = [
            [0, 1, 2, 3],
            [4, 5, 6, 7],
            [0, 1, 5, 4],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [3, 0, 4, 7]
        ];

        const orderedFaces = faces
            .map((face) => ({
                face,
                depth: face.reduce((sum, index) => sum + rotatePoint(vertices[index])[2], 0) / face.length
            }))
            .sort((a, b) => a.depth - b.depth);

        orderedFaces.forEach(({ face }, index) => {
            const tint = index === orderedFaces.length - 1 ? 1.0 : 0.92 - index * 0.04;
            drawFace(
                projected,
                face,
                tintColor(object.color, tint),
                object.stroke || 'rgba(38, 52, 48, 0.18)',
                object.alpha
            );
        });

        const labelPoint = projected[6];
        if (object.alpha > 0.15) {
            ctx.save();
            ctx.font = '12px "Segoe UI", sans-serif';
            ctx.fillStyle = 'rgba(22, 48, 39, 0.78)';
            ctx.fillText(object.label, labelPoint.x + 6, labelPoint.y - 4);
            ctx.restore();
        }
    }

    function tintColor(hex, factor) {
        const normalized = hex.replace('#', '');
        const r = parseInt(normalized.slice(0, 2), 16);
        const g = parseInt(normalized.slice(2, 4), 16);
        const b = parseInt(normalized.slice(4, 6), 16);
        return `rgb(${Math.min(255, Math.round(r * factor))}, ${Math.min(255, Math.round(g * factor))}, ${Math.min(255, Math.round(b * factor))})`;
    }

    function drawGrid() {
        ctx.save();
        ctx.strokeStyle = 'rgba(33, 74, 63, 0.08)';
        ctx.lineWidth = 1;
        for (let x = -50; x <= 850; x += 50) {
            const p1 = project([x, -40, 0]);
            const p2 = project([x, 640, 0]);
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
        }
        for (let y = -40; y <= 640; y += 50) {
            const p1 = project([-50, y, 0]);
            const p2 = project([850, y, 0]);
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
        }
        ctx.restore();
    }

    function render() {
        ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
        drawGrid();

        const orderedObjects = objects
            .map((object) => ({ object, depth: averageDepth(getVertices(object)) }))
            .sort((a, b) => a.depth - b.depth);

        orderedObjects.forEach(({ object }) => drawBox(object));
    }

    function setPresetView(rotX, rotY, zoom) {
        state.rotX = rotX;
        state.rotY = rotY;
        state.zoom = zoom;
        state.panX = 0;
        state.panY = 0;
        render();
    }

    canvas.addEventListener('mousedown', (event) => {
        state.dragging = true;
        state.lastX = event.clientX;
        state.lastY = event.clientY;
        canvas.classList.add('dragging');
    });

    window.addEventListener('mouseup', () => {
        state.dragging = false;
        canvas.classList.remove('dragging');
    });

    window.addEventListener('mousemove', (event) => {
        if (!state.dragging) {
            return;
        }
        const dx = event.clientX - state.lastX;
        const dy = event.clientY - state.lastY;
        state.rotY += dx * 0.01;
        state.rotX += dy * 0.01;
        state.lastX = event.clientX;
        state.lastY = event.clientY;
        render();
    });

    canvas.addEventListener('wheel', (event) => {
        event.preventDefault();
        const delta = Math.sign(event.deltaY) * -0.08;
        state.zoom = Math.max(0.38, Math.min(2.4, state.zoom + delta));
        render();
    }, { passive: false });

    canvas.addEventListener('dblclick', () => setPresetView(-0.62, 0.78, 0.92));

    document.querySelectorAll('[data-layer]').forEach((checkbox) => {
        checkbox.addEventListener('change', (event) => {
            layers[event.target.dataset.layer] = event.target.checked;
            render();
        });
    });

    document.getElementById('resetViewBtn').addEventListener('click', () => setPresetView(-0.62, 0.78, 0.92));
    document.getElementById('topViewBtn').addEventListener('click', () => setPresetView(-1.55, 0.02, 1.02));
    document.getElementById('frontViewBtn').addEventListener('click', () => setPresetView(-0.12, 0.0, 0.96));
    document.getElementById('isoViewBtn').addEventListener('click', () => setPresetView(-0.62, 0.78, 0.92));
    document.getElementById('cabinetViewBtn').addEventListener('click', () => setPresetView(-0.48, 0.96, 0.76));

    window.addEventListener('resize', updateCanvasSize);
    updateCanvasSize();
})();
