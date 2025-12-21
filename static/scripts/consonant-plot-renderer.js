/**
 * Consonant Plot Renderer - Stop Consonant Visualization
 * =======================================================
 * Renders stop consonant analysis on two canvases:
 * 1. Place Chart: Articulation position (labial/alveolar/velar)
 * 2. VOT-F0z Chart: Phonation type (fortis/lenis/aspirated)
 */

class ConsonantPlotRenderer {
    constructor(placeCanvasId, votCanvasId) {
        this.placeCanvas = document.getElementById(placeCanvasId);
        this.votCanvas = document.getElementById(votCanvasId);

        if (!this.placeCanvas || !this.votCanvas) {
            console.error('[ConsonantPlotRenderer] Canvas elements not found');
            return;
        }

        this.placeCtx = this.placeCanvas.getContext('2d');
        this.votCtx = this.votCanvas.getContext('2d');

        // Canvas dimensions
        this.width = 500;
        this.height = 300;

        // Initialize canvases
        this.initializeCanvases();

        // Colors
        this.colors = {
            axis: '#1f77b4',
            target: '#d62728',
            user: '#ffbf00',
            other: '#bcdff5',
            text: '#333333',
            grid: '#e2e8f0'
        };

        // Place labels (Korean)
        this.placeLabels = {
            labial: 'ㅂ/ㅃ/ㅍ',
            alveolar: 'ㄷ/ㄸ/ㅌ',
            velar: 'ㄱ/ㄲ/ㅋ'
        };

        // Phonation labels by place
        this.phonationLabels = {
            labial: { lenis: 'ㅂ', fortis: 'ㅃ', aspirated: 'ㅍ' },
            alveolar: { lenis: 'ㄷ', fortis: 'ㄸ', aspirated: 'ㅌ' },
            velar: { lenis: 'ㄱ', fortis: 'ㄲ', aspirated: 'ㅋ' }
        };

        // Place centers on x-axis (0-3 range)
        this.placeCenters = {
            labial: 0.5,
            alveolar: 1.5,
            velar: 2.5
        };

        console.log('[ConsonantPlotRenderer] Initialized');
    }

    initializeCanvases() {
        this.placeCanvas.width = this.width;
        this.placeCanvas.height = 150;
        this.votCanvas.width = this.width;
        this.votCanvas.height = this.height;
    }

    /**
     * Update visualization with stop consonant analysis result
     * @param {Object} data - Analysis result from analyze_stop()
     */
    update(data) {
        if (!data || data.type !== 'stop') {
            console.warn('[ConsonantPlotRenderer] Invalid data type');
            return;
        }

        this.drawPlaceChart(data);
        this.drawVotF0zChart(data);
    }

    /**
     * Draw Place Chart - Articulation Position
     */
    drawPlaceChart(data) {
        const ctx = this.placeCtx;
        const w = this.placeCanvas.width;
        const h = this.placeCanvas.height;

        // Clear
        ctx.clearRect(0, 0, w, h);

        // Background
        ctx.fillStyle = '#f8fafc';
        ctx.fillRect(0, 0, w, h);

        const margin = { left: 40, right: 40, top: 40, bottom: 30 };
        const chartWidth = w - margin.left - margin.right;
        const y0 = h / 2;

        // Get data
        const targetPlace = data.targets?.place;
        const detectedPlace = data.evaluation?.detected_place;
        const softscores = data.evaluation?.place_softscores || {};

        // Draw axis line with arrow
        ctx.strokeStyle = this.colors.axis;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(margin.left, y0);
        ctx.lineTo(w - margin.right, y0);
        ctx.stroke();

        // Arrow head
        ctx.beginPath();
        ctx.moveTo(w - margin.right, y0);
        ctx.lineTo(w - margin.right - 10, y0 - 5);
        ctx.lineTo(w - margin.right - 10, y0 + 5);
        ctx.closePath();
        ctx.fillStyle = this.colors.axis;
        ctx.fill();

        // Draw dividers
        const xLabial = margin.left + chartWidth * (1 / 6);
        const xAlveolar = margin.left + chartWidth * (3 / 6);
        const xVelar = margin.left + chartWidth * (5 / 6);
        const divider1 = margin.left + chartWidth * (2 / 6);
        const divider2 = margin.left + chartWidth * (4 / 6);

        ctx.strokeStyle = this.colors.axis;
        ctx.lineWidth = 2;
        [divider1, divider2].forEach(x => {
            ctx.beginPath();
            ctx.moveTo(x, y0 - 10);
            ctx.lineTo(x, y0 + 10);
            ctx.stroke();
        });

        // Draw labels
        ctx.fillStyle = this.colors.text;
        ctx.font = '14px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(this.placeLabels.labial, xLabial, y0 + 25);
        ctx.fillText(this.placeLabels.alveolar, xAlveolar, y0 + 25);
        ctx.fillText(this.placeLabels.velar, xVelar, y0 + 25);

        // Helper to get x position
        const getX = (place) => {
            if (place === 'labial') return xLabial;
            if (place === 'alveolar') return xAlveolar;
            if (place === 'velar') return xVelar;
            return xAlveolar;
        };

        // Draw target marker (star)
        if (targetPlace) {
            const tx = getX(targetPlace);
            ctx.fillStyle = this.colors.target;
            this.drawStar(ctx, tx, y0 - 20, 12, 5);
            ctx.font = 'bold 11px Inter, system-ui, sans-serif';
            ctx.fillStyle = this.colors.target;
            ctx.fillText('Target', tx, y0 - 35);
        }

        // Draw user marker (triangle)
        if (detectedPlace) {
            const ux = getX(detectedPlace);
            ctx.fillStyle = this.colors.user;
            this.drawTriangle(ctx, ux, y0 + 5, 14);
            ctx.font = 'bold 11px Inter, system-ui, sans-serif';
            ctx.fillStyle = this.colors.user;
            ctx.fillText('You', ux, y0 + 55);
        }

        // Title
        const targetLabel = this.placeLabels[targetPlace] || targetPlace;
        ctx.fillStyle = '#1e293b';
        ctx.font = 'bold 13px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(`Articulation Position (target: ${targetLabel})`, w / 2, 20);

        // Border
        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = 2;
        ctx.strokeRect(1, 1, w - 2, h - 2);
    }

    /**
     * Draw VOT vs F0z Chart - Phonation Type
     */
    drawVotF0zChart(data) {
        const ctx = this.votCtx;
        const w = this.votCanvas.width;
        const h = this.votCanvas.height;

        // Clear
        ctx.clearRect(0, 0, w, h);

        // Background
        ctx.fillStyle = '#f8fafc';
        ctx.fillRect(0, 0, w, h);

        const margin = { left: 55, right: 25, top: 45, bottom: 45 };
        const chartWidth = w - margin.left - margin.right;
        const chartHeight = h - margin.top - margin.bottom;

        // Get data
        const plots = data.evaluation?.plots || {};
        const votPoint = plots.vot_f0_point || {};
        const votRanges = plots.vot_reference_ranges_ms || {};
        const f0zTargets = plots.f0z_reference_targets || {};
        const targetPlace = data.targets?.place || 'velar';
        const targetPhonation = data.targets?.phonation;
        const detectedPhonation = data.evaluation?.detected_phonation;

        // Get phonation labels for this place
        const labels = this.phonationLabels[targetPlace] || this.phonationLabels.velar;

        // Scale functions (VOT: -5 to 105ms, F0z: -1.5 to 4.5)
        const votMin = -5, votMax = 105;
        const f0zMin = -1.5, f0zMax = 4.5;

        const scaleX = (vot) => margin.left + ((vot - votMin) / (votMax - votMin)) * chartWidth;
        const scaleY = (f0z) => margin.top + chartHeight - ((f0z - f0zMin) / (f0zMax - f0zMin)) * chartHeight;

        // Draw grid
        ctx.strokeStyle = this.colors.grid;
        ctx.lineWidth = 1;

        // Vertical grid (VOT)
        [0, 20, 40, 60, 80, 100].forEach(vot => {
            const x = scaleX(vot);
            ctx.beginPath();
            ctx.moveTo(x, margin.top);
            ctx.lineTo(x, h - margin.bottom);
            ctx.stroke();

            ctx.fillStyle = '#64748b';
            ctx.font = '10px Inter, system-ui, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(vot.toString(), x, h - margin.bottom + 14);
        });

        // Horizontal grid (F0z)
        [-1, 0, 1, 2, 3, 4].forEach(f0z => {
            const y = scaleY(f0z);
            ctx.beginPath();
            ctx.moveTo(margin.left, y);
            ctx.lineTo(w - margin.right, y);
            ctx.stroke();

            ctx.fillStyle = '#64748b';
            ctx.font = '10px Inter, system-ui, sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(f0z.toString(), margin.left - 8, y + 3);
        });

        // Draw reference ellipses for each phonation type
        ['fortis', 'lenis', 'aspirated'].forEach(phon => {
            const range = votRanges[phon];
            const f0zRef = f0zTargets[phon];
            if (!range || !f0zRef) return;

            const cx = scaleX(range.center);
            const cy = scaleY(f0zRef.center);
            const rx = ((range.high - range.low) / 2) / (votMax - votMin) * chartWidth;
            const ry = (f0zRef.tol) / (f0zMax - f0zMin) * chartHeight;

            const isTarget = (phon === targetPhonation);

            // Draw ellipse
            ctx.beginPath();
            ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
            ctx.fillStyle = isTarget ? 'rgba(214, 39, 40, 0.4)' : 'rgba(188, 223, 245, 0.5)';
            ctx.fill();

            // Label in center
            ctx.fillStyle = '#333';
            ctx.font = 'bold 14px Inter, system-ui, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(labels[phon] || phon, cx, cy + 5);
        });

        // Draw user point
        const userVot = votPoint.x_vot_ms;
        const userF0z = votPoint.y_f0_z;

        if (userVot !== null && userVot !== undefined) {
            const ux = scaleX(userVot);
            let uy;

            if (userF0z !== null && userF0z !== undefined) {
                uy = scaleY(userF0z);
            } else {
                // No F0z - place on x-axis
                uy = scaleY(0);
            }

            // User point
            ctx.beginPath();
            ctx.arc(ux, uy, 10, 0, Math.PI * 2);
            ctx.fillStyle = this.colors.user;
            ctx.fill();
            ctx.strokeStyle = '#996600';
            ctx.lineWidth = 2;
            ctx.stroke();

            // User label
            const userLabel = labels[detectedPhonation] || detectedPhonation || '?';
            ctx.font = 'bold 11px Inter, system-ui, sans-serif';
            ctx.fillStyle = this.colors.user;
            ctx.textAlign = 'center';
            ctx.fillText(`You: ${userLabel}`, ux, uy - 15);
        }

        // Axis labels
        ctx.fillStyle = '#475569';
        ctx.font = 'bold 11px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('VOT (ms)', w / 2, h - 8);

        ctx.save();
        ctx.translate(15, h / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('F0 z-score', 0, 0);
        ctx.restore();

        // Title
        const targetLabel = labels[targetPhonation] || targetPhonation;
        ctx.fillStyle = '#1e293b';
        ctx.font = 'bold 13px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(`Phonation Type (target: ${targetLabel})`, w / 2, 20);

        // Border
        ctx.strokeStyle = '#f59e0b';
        ctx.lineWidth = 2;
        ctx.strokeRect(1, 1, w - 2, h - 2);
    }

    /**
     * Draw a star shape
     */
    drawStar(ctx, cx, cy, outerR, points) {
        const innerR = outerR * 0.5;
        ctx.beginPath();
        for (let i = 0; i < points * 2; i++) {
            const r = i % 2 === 0 ? outerR : innerR;
            const angle = (i * Math.PI / points) - Math.PI / 2;
            const x = cx + r * Math.cos(angle);
            const y = cy + r * Math.sin(angle);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.fill();
    }

    /**
     * Draw a triangle (pointing up)
     */
    drawTriangle(ctx, cx, cy, size) {
        ctx.beginPath();
        ctx.moveTo(cx, cy - size);
        ctx.lineTo(cx - size * 0.866, cy + size * 0.5);
        ctx.lineTo(cx + size * 0.866, cy + size * 0.5);
        ctx.closePath();
        ctx.fill();
    }

    /**
     * Clear both canvases
     */
    clear() {
        this.placeCtx.clearRect(0, 0, this.placeCanvas.width, this.placeCanvas.height);
        this.votCtx.clearRect(0, 0, this.votCanvas.width, this.votCanvas.height);
    }
}

// Export for use in sound.js
if (typeof window !== 'undefined') {
    window.ConsonantPlotRenderer = ConsonantPlotRenderer;
}
