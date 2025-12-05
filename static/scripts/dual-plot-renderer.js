/**
 * Dual Plot Renderer - Side-by-Side Formant & Articulatory Display
 * ==================================================================
 * Renders vowel analysis on two canvases simultaneously without regenerating images.
 * Supports both single vowels and diphthong trajectories.
 *
 * Features:
 * - Static base chart (no server-generated images needed)
 * - Persistent diphthong trajectories until new recording
 * - Smooth animations
 * - Side-by-side formant chart and articulatory map
 */

class DualPlotRenderer {
    constructor(formantCanvasId, articulatoryCanvasId) {
        this.formantCanvas = document.getElementById(formantCanvasId);
        this.articulatoryCanvas = document.getElementById(articulatoryCanvasId);

        if (!this.formantCanvas || !this.articulatoryCanvas) {
            console.error('Canvas elements not found');
            return;
        }

        this.formantCtx = this.formantCanvas.getContext('2d');
        this.articulatoryCtx = this.articulatoryCanvas.getContext('2d');

        // Canvas dimensions
        this.width = 500;
        this.height = 500;

        // Initialize canvases
        this.initializeCanvases();

        // Formant space ranges (Hz) - inverted for chart display
        this.f1Range = [800, 200];  // High to low (inverted Y axis)
        this.f2Range = [3000, 600]; // High to low (inverted X axis)

        // Articulatory space ranges (for trapezoid)
        this.articulatoryRange = {
            x: [0, 1],    // Backness: 0=back, 1=front
            y: [0, 1]     // Height: 0=low, 1=high
        };

        // Current visualization data
        this.currentPoint = null;       // {f1, f2, x, y}
        this.previousPoint = null;
        this.targetPoint = null;         // Reference point
        this.trajectoryHistory = [];     // For diphthongs
        this.calibrationPoints = [];     // User calibration points (a, e, u)
        this.referenceVowels = [];       // Standard reference vowels for all Korean vowels

        // Personalized Affine transform (F1, F2 → x, y)
        this.affineA = null;  // 2×2 matrix [[a11, a12], [a21, a22]]
        this.affineB = null;  // 2×1 vector [b1, b2]

        // Animation state
        this.animationProgress = 0;
        this.animationDuration = 1500;    // ms (increased from 800ms for better visibility)
        this.animationFrame = null;

        // Trajectory animation (slower for visibility)
        this.trajectoryAnimationDuration = 3500;  // ms (increased from 1200ms)

        // Debug logging
        console.log('[DualPlotRenderer] Initialized with canvases:', formantCanvasId, articulatoryCanvasId);
        console.log('[DualPlotRenderer] Canvas dimensions:', this.width, 'x', this.height);

        // Draw empty charts
        this.draw();
    }

    initializeCanvases() {
        this.formantCanvas.width = this.width;
        this.formantCanvas.height = this.height;
        this.articulatoryCanvas.width = this.width;
        this.articulatoryCanvas.height = this.height;
    }

    /**
     * Set calibration points to display on chart
     * @param {Array} points - [{f1, f2, label}, ...]
     */
    setCalibrationPoints(points) {
        this.calibrationPoints = points || [];
        this.draw();
    }

    /**
     * Set reference vowels (standard Korean vowels) to display on chart
     * @param {Array} vowels - [{f1, f2, label}, ...]
     */
    setReferenceVowels(vowels) {
        this.referenceVowels = vowels || [];
        console.log('[DualPlotRenderer] Reference vowels set:', this.referenceVowels.length);
        this.draw();
    }

    /**
     * Set personalized Affine transform for articulatory mapping
     * @param {Array} A - 2×2 transformation matrix [[a11, a12], [a21, a22]]
     * @param {Array} b - 2×1 bias vector [b1, b2]
     */
    setAffineTransform(A, b) {
        this.affineA = A;
        this.affineB = b;
        console.log('[DualPlotRenderer] Affine transform set:', { A, b });
        this.draw();
    }

    /**
     * Clear all visualizations
     */
    clear() {
        this.currentPoint = null;
        this.previousPoint = null;
        this.targetPoint = null;
        this.trajectoryHistory = [];
        this.draw();
    }

    /**
     * Clear trajectory history when recording new sound
     * Keep calibration points visible
     */
    clearTrajectories() {
        this.trajectoryHistory = [];
        this.currentPoint = null;
        this.previousPoint = null;
        this.targetPoint = null;
        // Don't clear calibrationPoints - they should persist
        this.draw();
    }

    /**
     * Set new point data and animate
     * @param {Object} data - {f1, f2, targetF1, targetF2, artX, artY, trajectory}
     */
    setPoint(data) {
        // Store previous point
        if (this.currentPoint) {
            this.previousPoint = {...this.currentPoint};
        }

        // Convert F1/F2 to articulatory coordinates using personalized transform
        const artCoords = this.formantsToArticulatory(data.f1, data.f2);

        // Set new current point
        this.currentPoint = {
            f1: data.f1,
            f2: data.f2,
            x: data.artX || artCoords.x,
            y: data.artY || artCoords.y
        };

        // Set target/reference point if provided
        if (data.targetF1 && data.targetF2) {
            const targetArtCoords = this.formantsToArticulatory(data.targetF1, data.targetF2);
            this.targetPoint = {
                f1: data.targetF1,
                f2: data.targetF2,
                x: data.targetArtX || targetArtCoords.x,
                y: data.targetArtY || targetArtCoords.y
            };
        }

        // Handle diphthong trajectory
        if (data.trajectory && Array.isArray(data.trajectory)) {
            this.trajectoryHistory.push({
                points: data.trajectory,
                timestamp: Date.now()
            });
        }

        // Cancel previous animation before starting new one
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }

        // Start animation
        this.animationProgress = 0;
        console.log('[DualPlotRenderer] Starting animation...');
        this.animate();
    }

    /**
     * Convert F1/F2 to canvas coordinates
     */
    f1ToCanvasY(f1) {
        // F1 range: [800, 200] -> canvas [50, 450]
        const margin = 50;
        const chartHeight = this.height - 2 * margin;
        const normalized = (f1 - this.f1Range[1]) / (this.f1Range[0] - this.f1Range[1]);
        return margin + chartHeight * normalized;
    }

    f2ToCanvasX(f2) {
        // F2 range: [3000, 600] -> canvas [450, 50]
        const margin = 50;
        const chartWidth = this.width - 2 * margin;
        const normalized = (f2 - this.f2Range[1]) / (this.f2Range[0] - this.f2Range[1]);
        return this.width - margin - chartWidth * normalized;
    }

    /**
     * Convert F1/F2 to articulatory X/Y (with personalized Affine transform)
     * Uses calibration-based transformation if available
     */
    formantsToArticulatory(f1, f2) {
        if (this.affineA && this.affineB) {
            // Use personalized Affine transform: [x, y] = A * [f1, f2] + b
            const x = this.affineA[0][0] * f1 + this.affineA[0][1] * f2 + this.affineB[0];
            const y = this.affineA[1][0] * f1 + this.affineA[1][1] * f2 + this.affineB[1];

            // Clamp to [0, 1]
            return {
                x: Math.max(0, Math.min(1, x)),
                y: Math.max(0, Math.min(1, y))
            };
        }

        // Fallback to generic transform
        return {
            x: this.f2ToX(f2),
            y: this.f1ToY(f1)
        };
    }

    /**
     * Convert F2 to articulatory X (backness) - generic fallback
     */
    f2ToX(f2) {
        // Higher F2 = fronter (closer to 1)
        return (f2 - 600) / (3000 - 600);
    }

    /**
     * Convert F1 to articulatory Y (height) - generic fallback
     */
    f1ToY(f1) {
        // Higher F1 = lower (closer to 0)
        return 1 - ((f1 - 200) / (800 - 200));
    }

    /**
     * Convert articulatory coordinates to canvas coordinates
     */
    artToCanvasX(x) {
        const margin = 60;
        const trapWidth = this.width - 2 * margin;
        return margin + trapWidth * x;
    }

    artToCanvasY(y) {
        const margin = 60;
        const trapHeight = this.height - 2 * margin;
        return this.height - margin - trapHeight * y;
    }

    /**
     * Main draw function
     */
    draw() {
        this.drawFormantChart();
        this.drawArticulatoryMap();
    }

    /**
     * Draw formant chart (F1 vs F2)
     */
    drawFormantChart() {
        const ctx = this.formantCtx;
        const w = this.width;
        const h = this.height;

        // Clear
        ctx.clearRect(0, 0, w, h);

        // Background
        ctx.fillStyle = '#f8fafc';
        ctx.fillRect(0, 0, w, h);

        // Draw grid
        this.drawFormantGrid(ctx);

        // Draw reference vowels (faded, behind everything else)
        this.referenceVowels.forEach(pt => {
            const cx = this.f2ToCanvasX(pt.f2);
            const cy = this.f1ToCanvasY(pt.f1);
            this.drawPoint(ctx, cx, cy, 5, '#94a3b8', 0.25, pt.label);  // Gray, very faded
        });

        // Draw calibration points (always visible)
        this.calibrationPoints.forEach(pt => {
            const cx = this.f2ToCanvasX(pt.f2);
            const cy = this.f1ToCanvasY(pt.f1);
            this.drawPoint(ctx, cx, cy, 7, '#3b82f6', 0.6, pt.label);  // Blue for calibration (matches target color scheme)
        });

        // Draw reference/target point
        if (this.targetPoint) {
            const tx = this.f2ToCanvasX(this.targetPoint.f2);
            const ty = this.f1ToCanvasY(this.targetPoint.f1);
            this.drawPoint(ctx, tx, ty, 8, '#10b981', 0.3, 'Target');
        }

        // Draw trajectory history
        this.trajectoryHistory.forEach((traj, idx) => {
            this.drawTrajectoryOnFormant(ctx, traj.points, idx < this.trajectoryHistory.length - 1);
        });

        // Draw previous point (faded)
        if (this.previousPoint && this.animationProgress < 1) {
            const px = this.f2ToCanvasX(this.previousPoint.f2);
            const py = this.f1ToCanvasY(this.previousPoint.f1);
            this.drawPoint(ctx, px, py, 6, '#94a3b8', 0.3);
        }

        // Draw current point (animated)
        if (this.currentPoint) {
            const progress = this.easeOutCubic(this.animationProgress);
            const cx = this.f2ToCanvasX(this.currentPoint.f2);
            const cy = this.f1ToCanvasY(this.currentPoint.f1);
            const opacity = 0.3 + 0.7 * progress;
            const radius = 6 + 4 * progress;
            this.drawPoint(ctx, cx, cy, radius, '#ef4444', opacity, 'You');
        }
    }

    /**
     * Draw articulatory map (tongue position trapezoid)
     */
    drawArticulatoryMap() {
        const ctx = this.articulatoryCtx;
        const w = this.width;
        const h = this.height;

        // Clear
        ctx.clearRect(0, 0, w, h);

        // Background
        ctx.fillStyle = '#f8fafc';
        ctx.fillRect(0, 0, w, h);

        // Draw trapezoid
        this.drawTrapezoid(ctx);

        // Draw reference vowels (faded, behind everything else)
        this.referenceVowels.forEach(pt => {
            const artCoords = this.formantsToArticulatory(pt.f1, pt.f2);
            const cx = this.artToCanvasX(artCoords.x);
            const cy = this.artToCanvasY(artCoords.y);
            this.drawPoint(ctx, cx, cy, 5, '#94a3b8', 0.25, pt.label);  // Gray, very faded
        });

        // Draw calibration points (always visible)
        this.calibrationPoints.forEach(pt => {
            // Use Affine transform for articulatory coordinates
            const artCoords = this.formantsToArticulatory(pt.f1, pt.f2);
            const cx = this.artToCanvasX(pt.x || artCoords.x);
            const cy = this.artToCanvasY(pt.y || artCoords.y);
            this.drawPoint(ctx, cx, cy, 7, '#3b82f6', 0.6, pt.label);  // Blue for calibration
        });

        // Draw reference/target
        if (this.targetPoint) {
            const tx = this.artToCanvasX(this.targetPoint.x);
            const ty = this.artToCanvasY(this.targetPoint.y);
            this.drawPoint(ctx, tx, ty, 8, '#10b981', 0.3, 'Target');
        }

        // Draw trajectory history
        this.trajectoryHistory.forEach((traj, idx) => {
            this.drawTrajectoryOnArticulatory(ctx, traj.points, idx < this.trajectoryHistory.length - 1);
        });

        // Draw previous point (faded)
        if (this.previousPoint && this.animationProgress < 1) {
            const px = this.artToCanvasX(this.previousPoint.x);
            const py = this.artToCanvasY(this.previousPoint.y);
            this.drawPoint(ctx, px, py, 6, '#94a3b8', 0.3);
        }

        // Draw current point (animated)
        if (this.currentPoint) {
            const progress = this.easeOutCubic(this.animationProgress);
            const cx = this.artToCanvasX(this.currentPoint.x);
            const cy = this.artToCanvasY(this.currentPoint.y);
            const opacity = 0.3 + 0.7 * progress;
            const radius = 6 + 4 * progress;
            this.drawPoint(ctx, cx, cy, radius, '#ef4444', opacity, 'You');
        }
    }

    /**
     * Draw formant chart grid
     */
    drawFormantGrid(ctx) {
        const margin = 50;

        // Grid lines
        ctx.strokeStyle = '#e2e8f0';
        ctx.lineWidth = 1;

        // F1 lines (horizontal)
        [200, 300, 400, 500, 600, 700, 800].forEach(f1 => {
            const y = this.f1ToCanvasY(f1);
            ctx.beginPath();
            ctx.moveTo(margin, y);
            ctx.lineTo(this.width - margin, y);
            ctx.stroke();

            // Label
            ctx.fillStyle = '#64748b';
            ctx.font = '12px Inter, sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(f1, margin - 5, y + 4);
        });

        // F2 lines (vertical)
        [600, 1000, 1500, 2000, 2500, 3000].forEach(f2 => {
            const x = this.f2ToCanvasX(f2);
            ctx.beginPath();
            ctx.moveTo(x, margin);
            ctx.lineTo(x, this.height - margin);
            ctx.stroke();

            // Label
            ctx.fillStyle = '#64748b';
            ctx.font = '12px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(f2, x, this.height - margin + 20);
        });

        // Axis labels
        ctx.fillStyle = '#1e293b';
        ctx.font = 'bold 14px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('F1 (Hz)', 20, this.height / 2);
        ctx.fillText('F2 (Hz)', this.width / 2, this.height - 5);
    }

    /**
     * Draw articulatory trapezoid
     */
    drawTrapezoid(ctx) {
        const margin = 60;
        const w = this.width - 2 * margin;
        const h = this.height - 2 * margin;

        // Trapezoid shape (mouth cavity approximation)
        const topLeft = [margin + w * 0.15, margin];
        const topRight = [margin + w * 0.85, margin];
        const bottomRight = [this.width - margin, this.height - margin];
        const bottomLeft = [margin, this.height - margin];

        // Fill trapezoid
        ctx.fillStyle = '#f1f5f9';
        ctx.beginPath();
        ctx.moveTo(...topLeft);
        ctx.lineTo(...topRight);
        ctx.lineTo(...bottomRight);
        ctx.lineTo(...bottomLeft);
        ctx.closePath();
        ctx.fill();

        // Stroke trapezoid
        ctx.strokeStyle = '#cbd5e1';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Labels
        ctx.fillStyle = '#64748b';
        ctx.font = 'bold 12px Inter, sans-serif';
        ctx.textAlign = 'center';

        ctx.fillText('FRONT', this.width / 2 + 100, margin - 10);
        ctx.fillText('BACK', this.width / 2 - 100, margin - 10);
        ctx.fillText('HIGH', margin - 30, margin + 30);
        ctx.fillText('LOW', margin - 30, this.height - margin - 20);
    }

    /**
     * Draw a point with glow effect
     */
    drawPoint(ctx, x, y, radius, color, opacity, label) {
        // Glow
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius * 3);
        gradient.addColorStop(0, color + Math.floor(opacity * 100).toString(16).padStart(2, '0'));
        gradient.addColorStop(1, color + '00');
        ctx.fillStyle = gradient;
        ctx.fillRect(x - radius * 3, y - radius * 3, radius * 6, radius * 6);

        // Point
        ctx.fillStyle = color;
        ctx.globalAlpha = opacity;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;

        // Label
        if (label) {
            ctx.fillStyle = '#1e293b';
            ctx.font = 'bold 11px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(label, x, y - radius - 8);
        }
    }

    /**
     * Draw diphthong trajectory on formant chart (with animation support)
     */
    drawTrajectoryOnFormant(ctx, points, isFaded) {
        if (!points || points.length < 2) return;

        console.log('[DualPlotRenderer] Drawing trajectory with', points.length, 'points, faded:', isFaded);

        const opacity = isFaded ? 0.2 : 0.6;

        // For current (non-faded) trajectory, animate the drawing
        const isAnimating = !isFaded && this.animationProgress < 1;
        const visibleCount = isAnimating
            ? Math.max(2, Math.ceil(points.length * this.animationProgress))
            : points.length;

        const visiblePoints = points.slice(0, visibleCount);

        // Draw curve
        ctx.strokeStyle = `rgba(59, 130, 246, ${opacity})`;
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        ctx.beginPath();
        visiblePoints.forEach((pt, i) => {
            const x = this.f2ToCanvasX(pt.f2);
            const y = this.f1ToCanvasY(pt.f1);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();

        // Draw start point (green)
        const start = points[0];
        const sx = this.f2ToCanvasX(start.f2);
        const sy = this.f1ToCanvasY(start.f1);
        this.drawPoint(ctx, sx, sy, 5, '#10b981', opacity);

        // Draw end point (red) - only when animation is near complete or faded
        if (isFaded || this.animationProgress > 0.8) {
            const endOpacity = isFaded ? opacity : opacity * ((this.animationProgress - 0.8) / 0.2);
            const end = points[points.length - 1];
            const ex = this.f2ToCanvasX(end.f2);
            const ey = this.f1ToCanvasY(end.f1);
            this.drawPoint(ctx, ex, ey, 5, '#ef4444', endOpacity);
        }

        // Draw moving point along trajectory (for current animation only)
        if (isAnimating && visibleCount > 1) {
            const currentPt = visiblePoints[visiblePoints.length - 1];
            const cx = this.f2ToCanvasX(currentPt.f2);
            const cy = this.f1ToCanvasY(currentPt.f1);
            this.drawPoint(ctx, cx, cy, 7, '#3b82f6', 0.8, null);  // Blue moving point
        }
    }

    /**
     * Draw diphthong trajectory on articulatory map (with animation support)
     */
    drawTrajectoryOnArticulatory(ctx, points, isFaded) {
        if (!points || points.length < 2) return;

        const opacity = isFaded ? 0.2 : 0.6;

        // For current (non-faded) trajectory, animate the drawing
        const isAnimating = !isFaded && this.animationProgress < 1;
        const visibleCount = isAnimating
            ? Math.max(2, Math.ceil(points.length * this.animationProgress))
            : points.length;

        const visiblePoints = points.slice(0, visibleCount);

        // Convert to articulatory coordinates
        const artPoints = visiblePoints.map(pt => ({
            x: this.artToCanvasX(this.f2ToX(pt.f2)),
            y: this.artToCanvasY(this.f1ToY(pt.f1))
        }));

        // Draw curve
        ctx.strokeStyle = `rgba(59, 130, 246, ${opacity})`;
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        ctx.beginPath();
        artPoints.forEach((pt, i) => {
            if (i === 0) ctx.moveTo(pt.x, pt.y);
            else ctx.lineTo(pt.x, pt.y);
        });
        ctx.stroke();

        // Draw start point (green)
        this.drawPoint(ctx, artPoints[0].x, artPoints[0].y, 5, '#10b981', opacity);

        // Draw end point (red) - only when animation is near complete or faded
        if (isFaded || this.animationProgress > 0.8) {
            const endOpacity = isFaded ? opacity : opacity * ((this.animationProgress - 0.8) / 0.2);
            const lastIdx = artPoints.length - 1;
            this.drawPoint(ctx, artPoints[lastIdx].x, artPoints[lastIdx].y, 5, '#ef4444', endOpacity);
        }

        // Draw moving point along trajectory (for current animation only)
        if (isAnimating && artPoints.length > 1) {
            const currentIdx = artPoints.length - 1;
            this.drawPoint(ctx, artPoints[currentIdx].x, artPoints[currentIdx].y, 7, '#3b82f6', 0.8, null);
        }
    }

    /**
     * Animation loop (for monophthongs and trajectory)
     */
    animate() {
        const startTime = performance.now();

        const step = (timestamp) => {
            const elapsed = timestamp - startTime;

            // Use different duration for trajectories vs points
            const duration = this.trajectoryHistory.length > 0
                ? this.trajectoryAnimationDuration
                : this.animationDuration;

            this.animationProgress = Math.min(1, elapsed / duration);

            this.draw();

            if (this.animationProgress < 1) {
                this.animationFrame = requestAnimationFrame(step);
            } else {
                console.log('[DualPlotRenderer] Animation complete');
            }
        };

        this.animationFrame = requestAnimationFrame(step);
    }

    /**
     * Easing function
     */
    easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }
}

// Export to global scope
window.DualPlotRenderer = DualPlotRenderer;
