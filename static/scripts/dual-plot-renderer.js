/**
 * Dual Plot Renderer - Side-by-Side Formant & Articulatory Display
 * ==================================================================
 * Renders vowel analysis on two canvases simultaneously.
 *
 * Features:
 * - 1.5σ (valid range) and 2σ ellipses for each vowel
 * - Personalized SD from calibration
 * - Smooth diphthong trajectory with Catmull-Rom spline
 * - Achievement visualization (concentric circles)
 * - Side-by-side formant chart and articulatory map
 */

class DualPlotRenderer {
    constructor(formantCanvasId, articulatoryCanvasId) {
        this.formantCanvas = document.getElementById(formantCanvasId);
        this.articulatoryCanvas = document.getElementById(articulatoryCanvasId);

        if (!this.formantCanvas || !this.articulatoryCanvas) {
            console.error('[DualPlotRenderer] Canvas elements not found');
            return;
        }

        this.formantCtx = this.formantCanvas.getContext('2d');
        this.articulatoryCtx = this.articulatoryCanvas.getContext('2d');

        // Canvas dimensions (larger for better visibility)
        this.width = 500;
        this.height = 450;

        // Initialize canvases
        this.initializeCanvases();

        // Formant space ranges (Hz) - inverted for chart display
        // Extended range to accommodate all Korean vowels including ㅏ (F1 ~1000Hz)
        // Formant ranges - expanded to accommodate more vowel variations
        // F1: 200-1500 Hz covers all Korean vowels including outliers
        // F2: 500-3200 Hz covers front vowels like ㅣ
        this.f1Range = [1500, 200];  // High to low (inverted Y axis for phonetic convention)
        this.f2Range = [3200, 500];  // High to low (inverted X axis for phonetic convention)

        // Articulatory space ranges (matches backend VOWEL_ARTICULATORY_MAP)
        this.articulatoryRange = {
            x: [0, 1],    // Backness: 0=front, 1=back (ㅣ=0.15, ㅜ=0.90)
            y: [0, 1]     // Height: 0=low, 1=high
        };

        // Chart margins
        this.margin = { top: 40, right: 25, bottom: 45, left: 55 };

        // Current visualization data
        this.currentPoint = null;
        this.previousPoint = null;
        this.targetPoint = null;
        this.targetSD = null;  // {f1_sd, f2_sd} for ellipse
        this.trajectoryHistory = [];
        this.calibrationPoints = [];
        this.referenceVowels = [];

        // Load previous point from localStorage for Old→New animation
        this.loadPreviousPointFromStorage();

        // Personalized Affine transform
        this.affineA = null;
        this.affineB = null;

        // Animation state
        this.animationProgress = 0;
        this.animationDuration = 2000;  // Animation time (Old→Now movement)
        this.animationDelay = 1500;     // Show Old+Now statically for 1.5s before animating
        this.animationFrame = null;
        this.trajectoryAnimationDuration = 3500;
        this.isShowingStaticOld = false;  // Phase 1: show Old and Now statically

        // Achievement score (0-100)
        this.achievementScore = 0;

        // Diphthong start/end reference
        this.diphthongStartRef = null;
        this.diphthongEndRef = null;

        // Mouth cross-section background image
        this.mouthImage = new Image();
        this.mouthImage.src = '/static/images/mouth-crosssection.png';
        this.mouthImage.onload = () => {
            console.log('[DualPlotRenderer] Mouth image loaded');
            this.draw();
        };

        console.log('[DualPlotRenderer] Initialized');
        this.draw();
    }

    initializeCanvases() {
        this.formantCanvas.width = this.width;
        this.formantCanvas.height = this.height;
        this.articulatoryCanvas.width = this.width;
        this.articulatoryCanvas.height = this.height;
    }

    /**
     * Load previous point from localStorage for Old→New animation
     */
    loadPreviousPointFromStorage() {
        try {
            const soundSymbol = localStorage.getItem('selectedSound') || '';
            if (!soundSymbol) return;

            const storageKey = `kospa_lastPoint_${soundSymbol}`;
            const stored = localStorage.getItem(storageKey);
            if (stored) {
                const parsed = JSON.parse(stored);
                // Only load if data is recent (within 24 hours)
                if (parsed.timestamp && Date.now() - parsed.timestamp < 24 * 60 * 60 * 1000) {
                    this.previousPoint = {
                        f1: parsed.f1,
                        f2: parsed.f2,
                        x: parsed.x,
                        y: parsed.y
                    };
                    console.log('[DualPlotRenderer] Loaded previous point from storage:', this.previousPoint);
                }
            }
        } catch (e) {
            console.warn('[DualPlotRenderer] Failed to load previous point:', e);
        }
    }

    /**
     * Save current point to localStorage for future Old→New animation
     */
    saveCurrentPointToStorage() {
        try {
            const soundSymbol = localStorage.getItem('selectedSound') || '';
            if (!soundSymbol || !this.currentPoint) return;

            const storageKey = `kospa_lastPoint_${soundSymbol}`;
            const data = {
                f1: this.currentPoint.f1,
                f2: this.currentPoint.f2,
                x: this.currentPoint.x,
                y: this.currentPoint.y,
                timestamp: Date.now()
            };
            localStorage.setItem(storageKey, JSON.stringify(data));
            console.log('[DualPlotRenderer] Saved current point to storage:', data);
        } catch (e) {
            console.warn('[DualPlotRenderer] Failed to save current point:', e);
        }
    }

    /**
     * Set calibration points
     */
    setCalibrationPoints(points) {
        this.calibrationPoints = points || [];
        this.draw();
    }

    /**
     * Set reference vowels with SD values
     * @param {Array} vowels - [{f1, f2, f1_sd, f2_sd, label}, ...]
     */
    setReferenceVowels(vowels) {
        this.referenceVowels = vowels || [];
        console.log('[DualPlotRenderer] Reference vowels set:', this.referenceVowels.length);
        this.draw();
    }

    /**
     * Set personalized Affine transform
     */
    setAffineTransform(A, b) {
        this.affineA = A;
        this.affineB = b;
        console.log('[DualPlotRenderer] Affine transform set');
        this.draw();
    }

    /**
     * Set target point with SD for ellipse drawing
     */
    setTarget(data) {
        if (data.f1 && data.f2) {
            const artCoords = this.formantsToArticulatory(data.f1, data.f2);
            this.targetPoint = {
                f1: data.f1,
                f2: data.f2,
                x: artCoords.x,
                y: artCoords.y,
                label: data.label || 'Target'
            };
            this.targetSD = {
                f1_sd: data.f1_sd || 80,
                f2_sd: data.f2_sd || 120
            };
        }
        this.draw();
    }

    /**
     * Set diphthong references (start and end vowels)
     */
    setDiphthongReferences(startRef, endRef) {
        this.diphthongStartRef = startRef;  // {f1, f2, f1_sd, f2_sd, label}
        this.diphthongEndRef = endRef;
        this.draw();
    }

    /**
     * Clear all visualizations
     */
    clear() {
        this.currentPoint = null;
        this.previousPoint = null;
        this.targetPoint = null;
        this.targetSD = null;
        this.trajectoryHistory = [];
        this.diphthongStartRef = null;
        this.diphthongEndRef = null;
        this.achievementScore = 0;
        this.draw();
    }

    /**
     * Clear trajectories only
     */
    clearTrajectories() {
        this.trajectoryHistory = [];
        this.currentPoint = null;
        this.previousPoint = null;
        this.draw();
    }

    /**
     * Set new point and animate
     * Animation flow: Show Old first → Wait for UI to render → Animate to Now
     */
    setPoint(data) {
        // Try to load previous point from storage if not already loaded
        if (!this.previousPoint && !this.currentPoint) {
            this.loadPreviousPointFromStorage();
        }

        if (this.currentPoint) {
            this.previousPoint = { ...this.currentPoint };
        }

        const artCoords = this.formantsToArticulatory(data.f1, data.f2);

        this.currentPoint = {
            f1: data.f1,
            f2: data.f2,
            x: data.artX || artCoords.x,
            y: data.artY || artCoords.y
        };

        // Set target if provided
        if (data.targetF1 && data.targetF2) {
            this.setTarget({
                f1: data.targetF1,
                f2: data.targetF2,
                f1_sd: data.targetF1_sd,
                f2_sd: data.targetF2_sd,
                label: 'Target'
            });
        }

        // Calculate achievement score
        if (this.targetPoint && this.targetSD) {
            this.achievementScore = this.calculateAchievement(
                this.currentPoint, this.targetPoint, this.targetSD
            );
        }

        // Handle trajectory
        if (data.trajectory && Array.isArray(data.trajectory)) {
            console.log('[DualPlotRenderer] Adding trajectory with', data.trajectory.length, 'points');
            console.log('[DualPlotRenderer] First point:', data.trajectory[0]);
            console.log('[DualPlotRenderer] Last point:', data.trajectory[data.trajectory.length - 1]);
            this.trajectoryHistory.push({
                points: data.trajectory,
                timestamp: Date.now()
            });
            console.log('[DualPlotRenderer] trajectoryHistory now has', this.trajectoryHistory.length, 'trajectories');
        } else {
            console.log('[DualPlotRenderer] No trajectory in data. data.trajectory:', data.trajectory);
        }

        // Cancel previous animation
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }

        // Phase 1: Show static view with Old point first (if exists)
        // Wait for results UI to fully render before starting animation
        this.animationProgress = 0;
        this.isShowingStaticOld = !!this.previousPoint;

        // Draw initial state showing Old and Now statically
        this.draw();

        // Phase 2: After delay, start animation from Old to Now
        const startDelay = this.previousPoint ? this.animationDelay : 100;
        console.log('[DualPlotRenderer] Will start animation after', startDelay, 'ms delay');

        setTimeout(() => {
            this.isShowingStaticOld = false;
            this.animate();
        }, startDelay);

        // Save current point for future Old→New animation
        this.saveCurrentPointToStorage();
    }

    /**
     * Calculate achievement score (0-100)
     */
    calculateAchievement(current, target, sd) {
        const f1_z = Math.abs(current.f1 - target.f1) / sd.f1_sd;
        const f2_z = Math.abs(current.f2 - target.f2) / sd.f2_sd;
        const z_avg = (f1_z + f2_z) / 2;

        // 1.5σ = 100%, 3σ = 0%
        if (z_avg <= 1.5) return 100;
        if (z_avg >= 3.0) return 0;
        return Math.round(100 * (3.0 - z_avg) / 1.5);
    }

    // =========================================================================
    // Coordinate Conversion
    // =========================================================================

    f1ToCanvasY(f1) {
        const chartHeight = this.height - this.margin.top - this.margin.bottom;
        // Clamp F1 to range to prevent drawing outside chart
        const clampedF1 = Math.max(this.f1Range[1], Math.min(this.f1Range[0], f1));
        const normalized = (clampedF1 - this.f1Range[1]) / (this.f1Range[0] - this.f1Range[1]);
        return this.margin.top + chartHeight * normalized;
    }

    f2ToCanvasX(f2) {
        const chartWidth = this.width - this.margin.left - this.margin.right;
        // Clamp F2 to range to prevent drawing outside chart
        const clampedF2 = Math.max(this.f2Range[1], Math.min(this.f2Range[0], f2));
        const normalized = (clampedF2 - this.f2Range[1]) / (this.f2Range[0] - this.f2Range[1]);
        return this.width - this.margin.right - chartWidth * normalized;
    }

    canvasYToF1(y) {
        const chartHeight = this.height - this.margin.top - this.margin.bottom;
        const normalized = (y - this.margin.top) / chartHeight;
        return this.f1Range[1] + normalized * (this.f1Range[0] - this.f1Range[1]);
    }

    sdToCanvasScale(f1_sd, f2_sd) {
        const chartHeight = this.height - this.margin.top - this.margin.bottom;
        const chartWidth = this.width - this.margin.left - this.margin.right;

        const f1Range = this.f1Range[0] - this.f1Range[1];
        const f2Range = this.f2Range[0] - this.f2Range[1];

        return {
            h: (f1_sd / f1Range) * chartHeight,
            w: (f2_sd / f2Range) * chartWidth
        };
    }

    formantsToArticulatory(f1, f2) {
        if (this.affineA && this.affineB) {
            const x = this.affineA[0][0] * f1 + this.affineA[0][1] * f2 + this.affineB[0];
            const y = this.affineA[1][0] * f1 + this.affineA[1][1] * f2 + this.affineB[1];
            return {
                x: Math.max(0, Math.min(1, x)),
                y: Math.max(0, Math.min(1, y))
            };
        }
        // Fallback mapping (matches backend VOWEL_ARTICULATORY_MAP)
        // x: 0=front, 1=back (higher F2 = front vowel = smaller x)
        // y: 0=low, 1=high (lower F1 = high vowel = higher y)
        //
        // Examples: ㅣ(i) has high F2 (~2800Hz) → x ≈ 0.15 (front/left)
        //           ㅜ(u) has low F2 (~800Hz) → x ≈ 0.90 (back/right)
        const [f1Min, f1Max] = [this.f1Range[1], this.f1Range[0]]; // 200, 900
        const [f2Min, f2Max] = [this.f2Range[1], this.f2Range[0]]; // 500, 3000

        // FIXED: Invert x so high F2 (front vowel) → small x (left side)
        const xNorm = Math.max(0, Math.min(1, 1 - (f2 - f2Min) / (f2Max - f2Min)));
        const yNorm = Math.max(0, Math.min(1, 1 - (f1 - f1Min) / (f1Max - f1Min)));

        return { x: xNorm, y: yNorm };
    }

    artToCanvasX(x) {
        const chartWidth = this.width - this.margin.left - this.margin.right;
        return this.margin.left + chartWidth * x;
    }

    artToCanvasY(y) {
        const chartHeight = this.height - this.margin.top - this.margin.bottom;
        return this.height - this.margin.bottom - chartHeight * y;
    }

    // =========================================================================
    // Main Draw
    // =========================================================================

    draw() {
        this.drawFormantChart();
        this.drawArticulatoryMap();
    }

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

        // Draw reference vowels (faded)
        this.referenceVowels.forEach(pt => {
            const cx = this.f2ToCanvasX(pt.f2);
            const cy = this.f1ToCanvasY(pt.f1);
            this.drawPoint(ctx, cx, cy, 4, '#94a3b8', 0.3, pt.label, 9);
        });

        // Draw calibration points
        this.calibrationPoints.forEach(pt => {
            const cx = this.f2ToCanvasX(pt.f2);
            const cy = this.f1ToCanvasY(pt.f1);
            this.drawPoint(ctx, cx, cy, 6, '#3b82f6', 0.7, pt.label, 10);
        });

        // Draw target with ellipses
        if (this.targetPoint && this.targetSD) {
            this.drawTargetWithEllipses(ctx, this.targetPoint, this.targetSD, 'formant');
        }

        // Draw diphthong references
        if (this.diphthongStartRef) {
            this.drawDiphthongRefEllipse(ctx, this.diphthongStartRef, '#10b981', 'formant');
        }
        if (this.diphthongEndRef) {
            this.drawDiphthongRefEllipse(ctx, this.diphthongEndRef, '#ef4444', 'formant');
        }

        // Draw trajectories
        console.log('[DualPlotRenderer] Drawing', this.trajectoryHistory.length, 'trajectories on formant chart');
        this.trajectoryHistory.forEach((traj, idx) => {
            const isFaded = idx < this.trajectoryHistory.length - 1;
            console.log('[DualPlotRenderer] Drawing trajectory', idx, 'with', traj.points.length, 'points, isFaded:', isFaded);
            this.drawTrajectoryOnFormant(ctx, traj.points, isFaded);
        });

        // Draw movement trail and animation from previous to current point
        if (this.currentPoint) {
            const currX = this.f2ToCanvasX(this.currentPoint.f2);
            const currY = this.f1ToCanvasY(this.currentPoint.f1);

            // Phase 1: Show Old and Now statically (before animation starts)
            if (this.isShowingStaticOld && this.previousPoint) {
                const prevX = this.f2ToCanvasX(this.previousPoint.f2);
                const prevY = this.f1ToCanvasY(this.previousPoint.f1);

                // Draw dashed line connecting Old → Now
                ctx.beginPath();
                ctx.moveTo(prevX, prevY);
                ctx.lineTo(currX, currY);
                ctx.strokeStyle = 'rgba(148, 163, 184, 0.4)';
                ctx.lineWidth = 2;
                ctx.setLineDash([6, 4]);
                ctx.stroke();
                ctx.setLineDash([]);

                // Draw Old point with emphasis
                ctx.beginPath();
                ctx.arc(prevX, prevY, 16, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(100, 116, 139, 0.3)';
                ctx.lineWidth = 2;
                ctx.stroke();
                this.drawPoint(ctx, prevX, prevY, 8, '#64748b', 0.9, 'Old', 12);

                // Draw Now point
                this.drawPoint(ctx, currX, currY, 10, '#fb923c', 0.9, 'Now', 12);
            }
            // Phase 2: Animate from Old to Now
            else {
                const progress = this.easeOutCubic(this.animationProgress);
                let cx, cy;

                // Animate position from previous to current with visible trail
                if (this.previousPoint && this.animationProgress < 1) {
                    const prevX = this.f2ToCanvasX(this.previousPoint.f2);
                    const prevY = this.f1ToCanvasY(this.previousPoint.f1);

                    // Draw the trail line (fading as animation progresses)
                    const trailOpacity = Math.max(0, 0.5 * (1 - progress));
                    if (trailOpacity > 0.05) {
                        ctx.beginPath();
                        ctx.moveTo(prevX, prevY);
                        ctx.lineTo(currX, currY);
                        ctx.strokeStyle = `rgba(251, 146, 60, ${trailOpacity})`;
                        ctx.lineWidth = 3;
                        ctx.setLineDash([6, 3]);
                        ctx.stroke();
                        ctx.setLineDash([]);
                    }

                    // Draw fading previous point (Old)
                    const fadeOpacity = Math.max(0, 0.8 * (1 - progress * 0.8));
                    if (fadeOpacity > 0.05) {
                        this.drawPoint(ctx, prevX, prevY, 8, '#64748b', fadeOpacity, 'Old', 11);
                    }

                    // Interpolate current position
                    cx = prevX + (currX - prevX) * progress;
                    cy = prevY + (currY - prevY) * progress;

                    // Draw intermediate ghost points for smooth trail effect
                    const numGhosts = 5;
                    for (let i = 1; i < numGhosts; i++) {
                        const t = (progress - i * 0.1);
                        if (t > 0 && t < 1) {
                            const ghostX = prevX + (currX - prevX) * t;
                            const ghostY = prevY + (currY - prevY) * t;
                            const ghostOpacity = 0.3 * (1 - i / numGhosts) * (1 - progress);
                            ctx.beginPath();
                            ctx.arc(ghostX, ghostY, 4, 0, Math.PI * 2);
                            ctx.fillStyle = `rgba(251, 146, 60, ${ghostOpacity})`;
                            ctx.fill();
                        }
                    }
                } else {
                    cx = currX;
                    cy = currY;
                }

                const opacity = 0.4 + 0.5 * progress;
                const radius = 6 + 4 * progress;
                this.drawPoint(ctx, cx, cy, radius, '#fb923c', opacity, 'Now', 11);

                // Draw line to target (distance indicator)
                if (this.targetPoint && progress > 0.3) {
                    this.drawDistanceLine(ctx, cx, cy,
                        this.f2ToCanvasX(this.targetPoint.f2),
                        this.f1ToCanvasY(this.targetPoint.f1),
                        (progress - 0.3) / 0.7
                    );
                }
            }
        }

        // Draw title and subtitle
        ctx.fillStyle = '#1e293b';
        ctx.font = 'bold 13px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Formant Chart (F1 vs F2)', w / 2, 18);

        // Subtitle explaining what this chart shows
        ctx.fillStyle = '#64748b';
        ctx.font = '10px Inter, system-ui, sans-serif';
        ctx.fillText('Acoustic Measurements (Hz)', w / 2, 32);

        // Draw border to distinguish from articulatory map
        ctx.strokeStyle = '#3b82f6';  // Blue border
        ctx.lineWidth = 2;
        ctx.strokeRect(1, 1, w - 2, h - 2);
    }

    drawArticulatoryMap() {
        const ctx = this.articulatoryCtx;
        const w = this.width;
        const h = this.height;

        // Clear
        ctx.clearRect(0, 0, w, h);

        // Background - mouth cross-section image or fallback color
        ctx.fillStyle = '#fefce8';  // Warm yellow tint fallback
        ctx.fillRect(0, 0, w, h);

        // Background image disabled due to watermark issue
        // TODO: Enable when clean image is available
        // if (this.mouthImage && this.mouthImage.complete && this.mouthImage.naturalWidth > 0) {
        //     ctx.globalAlpha = 0.25;
        //     const imgAspect = this.mouthImage.naturalWidth / this.mouthImage.naturalHeight;
        //     const canvasAspect = w / h;
        //     let drawW, drawH, drawX, drawY;
        //     if (imgAspect > canvasAspect) {
        //         drawH = h; drawW = h * imgAspect; drawX = (w - drawW) / 2; drawY = 0;
        //     } else {
        //         drawW = w; drawH = w / imgAspect; drawX = 0; drawY = (h - drawH) / 2;
        //     }
        //     ctx.drawImage(this.mouthImage, drawX, drawY, drawW, drawH);
        //     ctx.globalAlpha = 1;
        // }

        // Draw vowel quadrangle overlay (instead of trapezoid)
        this.drawVowelQuadrangle(ctx);

        // Draw reference vowels (always visible as landmarks)
        this.referenceVowels.forEach(pt => {
            const artCoords = this.formantsToArticulatory(pt.f1, pt.f2);
            const cx = this.artToCanvasX(artCoords.x);
            const cy = this.artToCanvasY(artCoords.y);
            this.drawPoint(ctx, cx, cy, 4, '#94a3b8', 0.3, pt.label, 9);
        });

        // Draw calibration points (user's voice profile)
        this.calibrationPoints.forEach(pt => {
            const artCoords = this.formantsToArticulatory(pt.f1, pt.f2);
            const cx = this.artToCanvasX(artCoords.x);
            const cy = this.artToCanvasY(artCoords.y);
            this.drawPoint(ctx, cx, cy, 6, '#3b82f6', 0.7, pt.label, 10);
        });

        // Draw diphthong direction guide (start → end arrow)
        if (this.diphthongStartRef && this.diphthongEndRef) {
            this.drawDiphthongGuide(ctx);
        }

        // Draw target zone (for monophthongs)
        if (this.targetPoint && !this.diphthongStartRef) {
            const tx = this.artToCanvasX(this.targetPoint.x);
            const ty = this.artToCanvasY(this.targetPoint.y);
            this.drawAchievementCircles(ctx, tx, ty);
        }

        // Draw trajectories (diphthong path)
        this.trajectoryHistory.forEach((traj, idx) => {
            const isFaded = idx < this.trajectoryHistory.length - 1;
            this.drawTrajectoryOnArticulatory(ctx, traj.points, isFaded);
        });

        // Draw movement trail and animation from previous to current point
        if (this.currentPoint) {
            const currX = this.artToCanvasX(this.currentPoint.x);
            const currY = this.artToCanvasY(this.currentPoint.y);

            // Phase 1: Show Old and Now statically (before animation starts)
            if (this.isShowingStaticOld && this.previousPoint) {
                const prevX = this.artToCanvasX(this.previousPoint.x);
                const prevY = this.artToCanvasY(this.previousPoint.y);

                // Draw dashed line connecting Old → Now
                ctx.beginPath();
                ctx.moveTo(prevX, prevY);
                ctx.lineTo(currX, currY);
                ctx.strokeStyle = 'rgba(148, 163, 184, 0.4)';
                ctx.lineWidth = 2;
                ctx.setLineDash([6, 4]);
                ctx.stroke();
                ctx.setLineDash([]);

                // Draw Old point with emphasis
                ctx.beginPath();
                ctx.arc(prevX, prevY, 16, 0, Math.PI * 2);
                ctx.strokeStyle = 'rgba(100, 116, 139, 0.3)';
                ctx.lineWidth = 2;
                ctx.stroke();
                this.drawPoint(ctx, prevX, prevY, 8, '#64748b', 0.9, 'Old', 12);

                // Draw Now point
                this.drawPoint(ctx, currX, currY, 10, '#fb923c', 0.9, 'Now', 12);
            }
            // Phase 2: Animate from Old to Now
            else {
                const progress = this.easeOutCubic(this.animationProgress);
                let cx, cy;

                // Animate position from previous to current with visible trail
                if (this.previousPoint && this.animationProgress < 1) {
                    const prevX = this.artToCanvasX(this.previousPoint.x);
                    const prevY = this.artToCanvasY(this.previousPoint.y);

                    // Draw the trail line (fading as animation progresses)
                    const trailOpacity = Math.max(0, 0.5 * (1 - progress));
                    if (trailOpacity > 0.05) {
                        ctx.beginPath();
                        ctx.moveTo(prevX, prevY);
                        ctx.lineTo(currX, currY);
                        ctx.strokeStyle = `rgba(251, 146, 60, ${trailOpacity})`;
                        ctx.lineWidth = 3;
                        ctx.setLineDash([6, 3]);
                        ctx.stroke();
                        ctx.setLineDash([]);
                    }

                    // Draw fading previous point (Old)
                    const fadeOpacity = Math.max(0, 0.8 * (1 - progress * 0.8));
                    if (fadeOpacity > 0.05) {
                        this.drawPoint(ctx, prevX, prevY, 8, '#64748b', fadeOpacity, 'Old', 11);
                    }

                    // Interpolate current position
                    cx = prevX + (currX - prevX) * progress;
                    cy = prevY + (currY - prevY) * progress;

                    // Draw intermediate ghost points for smooth trail effect
                    const numGhosts = 5;
                    for (let i = 1; i < numGhosts; i++) {
                        const t = (progress - i * 0.1);
                        if (t > 0 && t < 1) {
                            const ghostX = prevX + (currX - prevX) * t;
                            const ghostY = prevY + (currY - prevY) * t;
                            const ghostOpacity = 0.3 * (1 - i / numGhosts) * (1 - progress);
                            ctx.beginPath();
                            ctx.arc(ghostX, ghostY, 4, 0, Math.PI * 2);
                            ctx.fillStyle = `rgba(251, 146, 60, ${ghostOpacity})`;
                            ctx.fill();
                        }
                    }
                } else {
                    cx = currX;
                    cy = currY;
                }

                const opacity = 0.4 + 0.5 * progress;
                const radius = 6 + 4 * progress;
                this.drawPoint(ctx, cx, cy, radius, '#fb923c', opacity, 'Now', 11);
            }
        }

        // Draw title and subtitle
        ctx.fillStyle = '#1e293b';
        ctx.font = 'bold 13px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Tongue Position', w / 2, 18);

        // Subtitle explaining what this chart shows
        ctx.fillStyle = '#64748b';
        ctx.font = '10px Inter, system-ui, sans-serif';
        ctx.fillText('Articulatory Space', w / 2, 32);

        // Draw border to distinguish from formant chart
        ctx.strokeStyle = '#f59e0b';  // Amber/orange border
        ctx.lineWidth = 2;
        ctx.strokeRect(1, 1, w - 2, h - 2);

        // Draw achievement score badge
        if (this.achievementScore > 0 && this.animationProgress > 0.5) {
            this.drawAchievementBadge(ctx, this.achievementScore);
        }
    }

    /**
     * Draw diphthong direction guide (start vowel → end vowel)
     * Shows the expected trajectory path for diphthongs like ㅟ = ㅜ→ㅣ
     */
    drawDiphthongGuide(ctx) {
        const startArt = this.formantsToArticulatory(this.diphthongStartRef.f1, this.diphthongStartRef.f2);
        const endArt = this.formantsToArticulatory(this.diphthongEndRef.f1, this.diphthongEndRef.f2);

        const startX = this.artToCanvasX(startArt.x);
        const startY = this.artToCanvasY(startArt.y);
        const endX = this.artToCanvasX(endArt.x);
        const endY = this.artToCanvasY(endArt.y);

        // Draw start zone (softer green circle - smaller)
        ctx.beginPath();
        ctx.arc(startX, startY, 18, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(52, 211, 153, 0.08)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(52, 211, 153, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Start label (softer)
        ctx.fillStyle = 'rgba(52, 211, 153, 0.8)';
        ctx.font = '10px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(this.diphthongStartRef.label || 'Start', startX, startY - 24);

        // Draw end zone (softer orange circle - smaller)
        ctx.beginPath();
        ctx.arc(endX, endY, 18, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(251, 146, 60, 0.08)';
        ctx.fill();
        ctx.strokeStyle = 'rgba(251, 146, 60, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // End label (softer)
        ctx.fillStyle = 'rgba(251, 146, 60, 0.8)';
        ctx.font = '10px Inter, system-ui, sans-serif';
        ctx.fillText(this.diphthongEndRef.label || 'End', endX, endY - 24);

        // Draw direction arrow (dashed line with arrow head - softer)
        ctx.beginPath();
        ctx.setLineDash([6, 3]);
        ctx.strokeStyle = 'rgba(96, 165, 250, 0.35)';
        ctx.lineWidth = 2;
        ctx.moveTo(startX, startY);
        ctx.lineTo(endX, endY);
        ctx.stroke();
        ctx.setLineDash([]);

        // Arrow head (softer)
        this.drawArrow(ctx, startX, startY, endX, endY, 'rgba(96, 165, 250, 0.5)');

        // Direction label in middle (softer)
        const midX = (startX + endX) / 2;
        const midY = (startY + endY) / 2 - 12;
        ctx.fillStyle = 'rgba(96, 165, 250, 0.7)';
        ctx.font = '9px Inter, system-ui, sans-serif';
        ctx.fillText('Expected Path', midX, midY);
    }

    // =========================================================================
    // Grid and Trapezoid
    // =========================================================================

    drawFormantGrid(ctx) {
        const m = this.margin;

        ctx.strokeStyle = '#e2e8f0';
        ctx.lineWidth = 1;

        // F1 lines (horizontal) - extended to 1500 to match f1Range
        [200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500].forEach(f1 => {
            if (f1 < this.f1Range[1] || f1 > this.f1Range[0]) return;
            const y = this.f1ToCanvasY(f1);
            ctx.beginPath();
            ctx.moveTo(m.left, y);
            ctx.lineTo(this.width - m.right, y);
            ctx.stroke();

            ctx.fillStyle = '#64748b';
            ctx.font = '10px Inter, system-ui, sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(f1.toString(), m.left - 6, y + 3);
        });

        // F2 lines (vertical)
        [500, 1000, 1500, 2000, 2500, 3000].forEach(f2 => {
            if (f2 < this.f2Range[1] || f2 > this.f2Range[0]) return;
            const x = this.f2ToCanvasX(f2);
            ctx.beginPath();
            ctx.moveTo(x, m.top);
            ctx.lineTo(x, this.height - m.bottom);
            ctx.stroke();

            ctx.fillStyle = '#64748b';
            ctx.font = '10px Inter, system-ui, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(f2.toString(), x, this.height - m.bottom + 14);
        });

        // Axis labels
        ctx.fillStyle = '#475569';
        ctx.font = 'bold 11px Inter, system-ui, sans-serif';

        // Y axis label (F1)
        ctx.save();
        ctx.translate(12, this.height / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.textAlign = 'center';
        ctx.fillText('F1 (Hz)', 0, 0);
        ctx.restore();

        // X axis label (F2)
        ctx.textAlign = 'center';
        ctx.fillText('F2 (Hz)', this.width / 2, this.height - 5);
    }

    /**
     * Draw vowel quadrangle - lightweight overlay for use with background image
     * Uses artToCanvas functions for consistent positioning with data points
     */
    drawVowelQuadrangle(ctx) {
        // Use articulatory coordinates (x: 0=front, 1=back; y: 0=low, 1=high)
        // and convert to canvas using our standard functions

        // Vowel quadrangle vertices (extended to accommodate all vowels)
        // Front-high (ㅣ): x=0.10, y=0.95
        const frontHigh = [this.artToCanvasX(0.05), this.artToCanvasY(0.98)];
        // Back-high (ㅜ): x=0.95, y=0.90
        const backHigh = [this.artToCanvasX(0.98), this.artToCanvasY(0.95)];
        // Back-low (near ㅓ area): x=0.85, y=0.05
        const backLow = [this.artToCanvasX(0.90), this.artToCanvasY(0.02)];
        // Front-low (ㅏ): x=0.25, y=0.05
        const frontLow = [this.artToCanvasX(0.20), this.artToCanvasY(0.02)];

        const topLeft = frontHigh;
        const topRight = backHigh;
        const bottomRight = backLow;
        const bottomLeft = frontLow;

        // Draw quadrangle with semi-transparent fill
        ctx.beginPath();
        ctx.moveTo(...topLeft);
        ctx.lineTo(...topRight);
        ctx.lineTo(...bottomRight);
        ctx.lineTo(...bottomLeft);
        ctx.closePath();

        // Light fill
        ctx.fillStyle = 'rgba(59, 130, 246, 0.06)';  // Softer blue tint
        ctx.fill();

        // Stroke
        ctx.strokeStyle = 'rgba(59, 130, 246, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Draw internal guide lines
        ctx.strokeStyle = 'rgba(100, 116, 139, 0.2)';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);

        // Vertical center line (x = 0.5)
        const centerX = this.artToCanvasX(0.5);
        ctx.beginPath();
        ctx.moveTo(centerX, this.artToCanvasY(0.90));
        ctx.lineTo(centerX, this.artToCanvasY(0.20));
        ctx.stroke();

        // Horizontal mid line (y = 0.5)
        const midY = this.artToCanvasY(0.5);
        ctx.beginPath();
        ctx.moveTo(this.artToCanvasX(0.15), midY);
        ctx.lineTo(this.artToCanvasX(0.85), midY);
        ctx.stroke();

        ctx.setLineDash([]);

        // Corner labels (subtle) - use artToCanvas for positioning
        ctx.fillStyle = 'rgba(71, 85, 105, 0.6)';
        ctx.font = '9px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';

        // Front/Back labels at top
        ctx.fillText('Front', this.artToCanvasX(0.15), this.margin.top - 5);
        ctx.fillText('Back', this.artToCanvasX(0.85), this.margin.top - 5);

        // High/Low labels on left side
        ctx.save();
        ctx.translate(this.margin.left - 8, this.artToCanvasY(0.85));
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('High', 0, 0);
        ctx.restore();

        ctx.save();
        ctx.translate(this.margin.left - 8, this.artToCanvasY(0.25));
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('Low', 0, 0);
        ctx.restore();
    }

    // =========================================================================
    // Ellipses and Achievement Circles
    // =========================================================================

    drawTargetWithEllipses(ctx, target, sd, chartType) {
        let cx, cy, wScale, hScale;

        if (chartType === 'formant') {
            cx = this.f2ToCanvasX(target.f2);
            cy = this.f1ToCanvasY(target.f1);
            const scale = this.sdToCanvasScale(sd.f1_sd, sd.f2_sd);
            wScale = scale.w;
            hScale = scale.h;
        } else {
            cx = this.artToCanvasX(target.x);
            cy = this.artToCanvasY(target.y);
            wScale = 30;
            hScale = 30;
        }

        // 2σ ellipse (outer, faded)
        ctx.beginPath();
        ctx.ellipse(cx, cy, wScale * 2, hScale * 2, 0, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(52, 211, 153, 0.05)';  // Lighter green
        ctx.fill();
        ctx.strokeStyle = 'rgba(52, 211, 153, 0.2)';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);

        // 1.5σ ellipse (valid range, softer colors)
        ctx.beginPath();
        ctx.ellipse(cx, cy, wScale * 1.5, hScale * 1.5, 0, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(52, 211, 153, 0.1)';  // Softer green fill
        ctx.fill();
        ctx.strokeStyle = 'rgba(52, 211, 153, 0.4)';  // Softer green stroke
        ctx.lineWidth = 2;
        ctx.stroke();

        // Center point (softer green)
        this.drawPoint(ctx, cx, cy, 6, '#34d399', 0.6, target.label || 'Target', 10);
    }

    drawDiphthongRefEllipse(ctx, ref, color, chartType) {
        let cx, cy, wScale, hScale;

        if (chartType === 'formant') {
            cx = this.f2ToCanvasX(ref.f2);
            cy = this.f1ToCanvasY(ref.f1);
            const scale = this.sdToCanvasScale(ref.f1_sd || 60, ref.f2_sd || 100);
            wScale = scale.w * 0.7;  // Smaller ellipse
            hScale = scale.h * 0.7;
        } else {
            const artCoords = this.formantsToArticulatory(ref.f1, ref.f2);
            cx = this.artToCanvasX(artCoords.x);
            cy = this.artToCanvasY(artCoords.y);
            wScale = 18;  // Smaller
            hScale = 18;
        }

        // Parse color and make softer
        const softerColor = color.replace('#10b981', 'rgba(52, 211, 153,')
                                 .replace('#ef4444', 'rgba(251, 146, 60,')
                                 .replace('rgb(', 'rgba(');

        // 1.5σ ellipse (softer, smaller)
        ctx.beginPath();
        ctx.ellipse(cx, cy, wScale * 1.2, hScale * 1.2, 0, 0, Math.PI * 2);
        ctx.fillStyle = softerColor.includes('rgba') ? softerColor + ' 0.06)' : 'rgba(100, 116, 139, 0.06)';
        ctx.fill();
        ctx.strokeStyle = softerColor.includes('rgba') ? softerColor + ' 0.35)' : color;
        ctx.globalAlpha = 0.6;
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.globalAlpha = 1;

        // Label (softer)
        ctx.fillStyle = softerColor.includes('rgba') ? softerColor + ' 0.7)' : color;
        ctx.font = '9px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(ref.label || '', cx, cy - wScale * 1.2 - 4);
    }

    drawAchievementCircles(ctx, cx, cy) {
        const baseRadius = 30;

        // Outer circle (3σ = 0%) - softer red
        ctx.beginPath();
        ctx.arc(cx, cy, baseRadius * 2, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(248, 113, 113, 0.15)';  // Softer red
        ctx.lineWidth = 1;
        ctx.stroke();

        // Middle circle (2σ) - softer amber
        ctx.beginPath();
        ctx.arc(cx, cy, baseRadius * 1.33, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(251, 191, 36, 0.2)';  // Softer amber
        ctx.lineWidth = 1;
        ctx.stroke();

        // Inner circle (1.5σ = 100%) - softer green
        ctx.beginPath();
        ctx.arc(cx, cy, baseRadius, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(52, 211, 153, 0.1)';  // Softer green
        ctx.fill();
        ctx.strokeStyle = 'rgba(52, 211, 153, 0.4)';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Center point (softer green)
        this.drawPoint(ctx, cx, cy, 5, '#34d399', 0.6, 'Target', 10);
    }

    drawAchievementBadge(ctx, score) {
        const x = this.width - 45;
        const y = 50;

        // Badge background
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, 25);
        if (score >= 90) {
            gradient.addColorStop(0, '#10b981');
            gradient.addColorStop(1, '#059669');
        } else if (score >= 70) {
            gradient.addColorStop(0, '#f59e0b');
            gradient.addColorStop(1, '#d97706');
        } else {
            gradient.addColorStop(0, '#ef4444');
            gradient.addColorStop(1, '#dc2626');
        }

        ctx.beginPath();
        ctx.arc(x, y, 23, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();

        // Score text
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 14px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(score + '%', x, y);
        ctx.textBaseline = 'alphabetic';
    }

    // =========================================================================
    // Points and Lines
    // =========================================================================

    drawPoint(ctx, x, y, radius, color, opacity, label, fontSize = 10) {
        // Glow effect
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius * 2.5);
        gradient.addColorStop(0, color + Math.floor(opacity * 80).toString(16).padStart(2, '0'));
        gradient.addColorStop(1, color + '00');
        ctx.fillStyle = gradient;
        ctx.fillRect(x - radius * 2.5, y - radius * 2.5, radius * 5, radius * 5);

        // Point
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.globalAlpha = opacity;
        ctx.fill();
        ctx.globalAlpha = 1;

        // Label
        if (label) {
            ctx.fillStyle = '#1e293b';
            ctx.font = `bold ${fontSize}px Inter, system-ui, sans-serif`;
            ctx.textAlign = 'center';
            ctx.fillText(label, x, y - radius - 5);
        }
    }

    drawDistanceLine(ctx, x1, y1, x2, y2, opacity) {
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = `rgba(100, 116, 139, ${0.4 * opacity})`;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    // =========================================================================
    // Trajectories with Smoothing
    // =========================================================================

    drawTrajectoryOnFormant(ctx, points, isFaded) {
        if (!points || points.length < 2) return;

        const opacity = isFaded ? 0.2 : 0.7;
        const isAnimating = !isFaded && this.animationProgress < 1;
        const visibleCount = isAnimating
            ? Math.max(2, Math.ceil(points.length * this.animationProgress))
            : points.length;

        const visiblePoints = points.slice(0, visibleCount);

        // Convert to canvas coordinates
        const canvasPoints = visiblePoints.map(pt => ({
            x: this.f2ToCanvasX(pt.f2),
            y: this.f1ToCanvasY(pt.f1)
        }));

        // Draw smooth curve (softer blue)
        this.drawSmoothCurve(ctx, canvasPoints, `rgba(96, 165, 250, ${opacity * 0.7})`, 3);

        // Draw arrow at end
        if (canvasPoints.length >= 2 && (!isAnimating || this.animationProgress > 0.8)) {
            const last = canvasPoints[canvasPoints.length - 1];
            const prev = canvasPoints[canvasPoints.length - 2];
            this.drawArrow(ctx, prev.x, prev.y, last.x, last.y, `rgba(96, 165, 250, ${opacity * 0.7})`);
        }

        // Start point (softer green)
        const start = canvasPoints[0];
        this.drawPoint(ctx, start.x, start.y, 5, '#34d399', opacity * 0.7, 'Start', 9);

        // End point (softer orange) - only when animation near complete
        if (!isAnimating || this.animationProgress > 0.85) {
            const endOpacity = isFaded ? opacity : opacity * ((this.animationProgress - 0.85) / 0.15);
            const end = canvasPoints[canvasPoints.length - 1];
            this.drawPoint(ctx, end.x, end.y, 5, '#fb923c', endOpacity * 0.7, 'End', 9);
        }

        // Moving point during animation (softer blue)
        if (isAnimating && visibleCount > 1) {
            const current = canvasPoints[canvasPoints.length - 1];
            this.drawPoint(ctx, current.x, current.y, 7, '#60a5fa', 0.7);
        }
    }

    drawTrajectoryOnArticulatory(ctx, points, isFaded) {
        if (!points || points.length < 2) return;

        const opacity = isFaded ? 0.15 : 0.6;  // Softer
        const isAnimating = !isFaded && this.animationProgress < 1;
        const visibleCount = isAnimating
            ? Math.max(2, Math.ceil(points.length * this.animationProgress))
            : points.length;

        const visiblePoints = points.slice(0, visibleCount);

        // Convert to articulatory then canvas coordinates
        const canvasPoints = visiblePoints.map(pt => {
            const art = this.formantsToArticulatory(pt.f1, pt.f2);
            return {
                x: this.artToCanvasX(art.x),
                y: this.artToCanvasY(art.y)
            };
        });

        // Draw smooth curve (softer blue)
        this.drawSmoothCurve(ctx, canvasPoints, `rgba(96, 165, 250, ${opacity})`, 3);

        // Start point (softer green)
        this.drawPoint(ctx, canvasPoints[0].x, canvasPoints[0].y, 5, '#34d399', opacity);

        // End point (softer orange)
        if (!isAnimating || this.animationProgress > 0.85) {
            const endOpacity = isFaded ? opacity : opacity * ((this.animationProgress - 0.85) / 0.15);
            const last = canvasPoints[canvasPoints.length - 1];
            this.drawPoint(ctx, last.x, last.y, 5, '#fb923c', endOpacity);
        }

        // Moving point (softer blue)
        if (isAnimating && canvasPoints.length > 1) {
            const current = canvasPoints[canvasPoints.length - 1];
            this.drawPoint(ctx, current.x, current.y, 7, '#60a5fa', 0.7);
        }
    }

    /**
     * Draw smooth curve using Catmull-Rom spline
     */
    drawSmoothCurve(ctx, points, color, lineWidth) {
        if (points.length < 2) return;

        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        if (points.length === 2) {
            ctx.moveTo(points[0].x, points[0].y);
            ctx.lineTo(points[1].x, points[1].y);
        } else {
            // Catmull-Rom spline
            ctx.moveTo(points[0].x, points[0].y);

            for (let i = 0; i < points.length - 1; i++) {
                const p0 = points[Math.max(0, i - 1)];
                const p1 = points[i];
                const p2 = points[Math.min(points.length - 1, i + 1)];
                const p3 = points[Math.min(points.length - 1, i + 2)];

                const segments = 10;

                for (let t = 1; t <= segments; t++) {
                    const s = t / segments;
                    const s2 = s * s;
                    const s3 = s2 * s;

                    const x = 0.5 * (
                        (2 * p1.x) +
                        (-p0.x + p2.x) * s +
                        (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * s2 +
                        (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * s3
                    );
                    const y = 0.5 * (
                        (2 * p1.y) +
                        (-p0.y + p2.y) * s +
                        (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * s2 +
                        (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * s3
                    );

                    ctx.lineTo(x, y);
                }
            }
        }

        ctx.stroke();
    }

    drawArrow(ctx, fromX, fromY, toX, toY, color) {
        const headLen = 10;
        const angle = Math.atan2(toY - fromY, toX - fromX);

        ctx.beginPath();
        ctx.moveTo(toX, toY);
        ctx.lineTo(
            toX - headLen * Math.cos(angle - Math.PI / 6),
            toY - headLen * Math.sin(angle - Math.PI / 6)
        );
        ctx.moveTo(toX, toY);
        ctx.lineTo(
            toX - headLen * Math.cos(angle + Math.PI / 6),
            toY - headLen * Math.sin(angle + Math.PI / 6)
        );
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();
    }

    // =========================================================================
    // Animation
    // =========================================================================

    animate() {
        const startTime = performance.now();
        const duration = this.trajectoryHistory.length > 0
            ? this.trajectoryAnimationDuration
            : this.animationDuration;

        console.log('[DualPlotRenderer] Starting animation, duration:', duration, 'ms');

        const step = (timestamp) => {
            const elapsed = timestamp - startTime;
            this.animationProgress = Math.min(1, elapsed / duration);

            this.draw();

            if (elapsed < duration) {
                this.animationFrame = requestAnimationFrame(step);
            } else {
                this.animationProgress = 1;
                this.draw();
                console.log('[DualPlotRenderer] Animation complete');
            }
        };

        this.animationFrame = requestAnimationFrame(step);
    }

    easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }
}

// Export to global scope
window.DualPlotRenderer = DualPlotRenderer;
