(function () {
'use strict';

// ============================================================
// UTILITIES
// ============================================================
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ============================================================
// CONSTANTS
// ============================================================
const FACE_STATE = {
    NO_FACE: 'NO_FACE',
    MULTIPLE_FACES: 'MULTIPLE_FACES',
    OUT_OF_FRAME: 'OUT_OF_FRAME',
    TOO_SMALL: 'TOO_SMALL',
    TOO_LARGE: 'TOO_LARGE',
    VALID: 'VALID',
    STABLE: 'STABLE',
};

const CHALLENGE_STATE = {
    IDLE: 'IDLE',
    ACTIVE: 'ACTIVE',
    PAUSED: 'PAUSED',
    COMPLETED: 'COMPLETED',
};

const VERIFICATION_STATE = {
    NOT_STARTED: 'NOT_STARTED',
    IN_PROGRESS: 'IN_PROGRESS',
    CAPTURING: 'CAPTURING',
    SUBMITTING: 'SUBMITTING',
    VERIFIED: 'VERIFIED',
    FAILED: 'FAILED',
    EXPIRED: 'EXPIRED',
    CAMERA_ERROR: 'CAMERA_ERROR',
};

const ERROR_MESSAGES = {
    CAMERA_PERMISSION_DENIED: 'دسترسی به دوربین داده نشده است. لطفاً اجازه دسترسی دوربین را فعال کنید.',
    CAMERA_NOT_FOUND: 'دوربین پیدا نشد. لطفاً از اتصال دوربین مطمئن شوید.',
    CAMERA_NOT_READABLE: 'دوربین توسط برنامه دیگری در حال استفاده است.',
    FACE_DEADLINE_EXPIRED: 'مهلت احراز هویت به پایان رسیده است.',
    TOO_MANY_ATTEMPTS: 'تعداد تلاش‌های مجاز شما به پایان رسیده است.',
    ENROLLMENT_REQUIRED: 'ابتدا باید چهره خود را ثبت کنید.',
    NO_REFERENCE_EMBEDDING: 'اطلاعات مرجع چهره شما موجود نیست.',
    LIVENESS_FAILED: 'زنده بودن چهره تأیید نشد.',
    MATCH_FAILED: 'چهره شما با اطلاعات ثبت‌شده مطابقت نداشت.',
    SUSPICIOUS: 'تطبیق چهره با اطمینان کافی انجام نشد.',
    MULTIPLE_FACES: 'فقط یک نفر باید مقابل دوربین باشد.',
    NO_FACE: 'چهره‌ای شناسایی نشد.',
    INVALID_IMAGE: 'فریم‌های ارسالی معتبر نیستند.',
    ATTENDANCE_NOT_ACTIVE: 'درخواست حضور و غیاب فعال نیست.',
    ATTENDANCE_NOT_FOUND: 'درخواست حضور و غیاب یافت نشد.',
    UNAUTHORIZED: 'شما مجاز به انجام این عملیات نیستید.',
    VERIFICATION_SESSION_INVALID: 'نشست احراز هویت معتبر نیست.',
    VERIFICATION_SESSION_EXPIRED: 'مهلت نشست احراز هویت به پایان رسیده است.',
    VERIFICATION_ALREADY_COMPLETED: 'این نشست احراز هویت قبلاً تکمیل شده است.',
    MODEL_UNAVAILABLE: 'مدل تشخیص چهره در دسترس نیست.',
    PROCESSING_ERROR: 'خطا در پردازش احراز هویت.',
};

function mapErrorMessage(code) {
    return ERROR_MESSAGES[code] || 'خطا در احراز هویت چهره.';
}

function formatTime(ms) {
    if (!ms || ms <= 0) return '00:00';
    const totalSeconds = Math.ceil(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

// ============================================================
// API
// ============================================================
class VerificationApi {
    constructor(csrfToken, startUrl, completeUrlBase) {
        this.csrfToken = csrfToken;
        this.startUrl = startUrl;
        this.completeUrlBase = completeUrlBase;
    }

    async start() {
        const response = await fetch(this.startUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': this.csrfToken,
                'Content-Type': 'application/json'
            },
        });
        const data = await response.json().catch(() => null);
        if (!data) throw { code: 'PROCESSING_ERROR' };
        if (!response.ok || data.success === false) throw data;
        return data;
    }

    async complete(sessionId, frames, challengeResult) {
        let url = this.completeUrlBase;
        if (url.includes('00000000-0000-0000-0000-000000000000')) {
            url = url.replace('00000000-0000-0000-0000-000000000000', sessionId);
        } else {
            if (!url.endsWith(sessionId) && !url.endsWith(sessionId + '/')) {
                url = url.replace(/\/$/, '') + '/' + sessionId + '/';
            }
        }
        const formData = new FormData();
        frames.forEach((blob, index) => formData.append('frames', blob, `frame_${index}.jpg`));
        formData.append('challenge_result', JSON.stringify(challengeResult || {}));

        const response = await fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': this.csrfToken },
            body: formData,
        });
        const data = await response.json().catch(() => null);
        if (!data) throw { code: 'PROCESSING_ERROR' };
        if (!response.ok && data.success === false) throw data;
        return data;
    }
}

// ============================================================
// CAMERA
// ============================================================
class CameraController {
    constructor(videoEl) {
        this.videoEl = videoEl;
        this.stream = null;
    }

    async start() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: false,
                video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
            });
            this.videoEl.srcObject = this.stream;
            await this.videoEl.play();
        } catch (error) {
            const name = error && error.name ? error.name : '';
            if (name === 'NotAllowedError' || name === 'PermissionDeniedError') throw { code: 'CAMERA_PERMISSION_DENIED' };
            if (name === 'NotFoundError' || name === 'DevicesNotFoundError') throw { code: 'CAMERA_NOT_FOUND' };
            if (name === 'NotReadableError' || name === 'TrackStartError') throw { code: 'CAMERA_NOT_READABLE' };
            throw { code: 'CAMERA_NOT_READABLE' };
        }
    }

    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.videoEl) this.videoEl.srcObject = null;
    }
}

// ============================================================
// MEDIAPIPE LANDMARKER
// ============================================================
class FaceLandmarkerController {
    constructor(config) {
        this.config = config;
        this.landmarker = null;
        this.ready = false;
    }

    async init() {
        const visionModule = await import(this.config.mediaPipe.moduleUrl);
        const { FaceLandmarker, FilesetResolver } = visionModule;
        const vision = await FilesetResolver.forVisionTasks(this.config.mediaPipe.wasmBase);
        this.landmarker = await FaceLandmarker.createFromOptions(vision, {
            baseOptions: { modelAssetPath: this.config.mediaPipe.modelUrl, delegate: 'GPU' },
            runningMode: 'VIDEO',
            numFaces: 2,
            outputFaceBlendshapes: true,
        });
        this.ready = true;
    }

    detect(video, timestamp) {
        if (!this.ready || !this.landmarker || !video || video.readyState < 2) {
            return { faceCount: 0, landmarks: [], blendshapes: [] };
        }
        try {
            const result = this.landmarker.detectForVideo(video, timestamp);
            return {
                faceCount: (result.faceLandmarks || []).length,
                landmarks: result.faceLandmarks || [],
                blendshapes: result.faceBlendshapes || []
            };
        } catch (e) {
            return { faceCount: 0, landmarks: [], blendshapes: [] };
        }
    }

    close() {
        try {
            if (this.landmarker && this.landmarker.close) this.landmarker.close();
        } catch (e) {}
        this.ready = false;
    }
}

// ============================================================
// FACE POSITION VALIDATOR
// ============================================================
class FacePositionValidator {
    constructor(guide) {
        this.guide = guide;
    }

    computeBBox(landmarks) {
        if (!landmarks || !landmarks.length) return null;
        let minX = 1, minY = 1, maxX = 0, maxY = 0;
        for (const lm of landmarks) {
            if (lm.x < minX) minX = lm.x;
            if (lm.y < minY) minY = lm.y;
            if (lm.x > maxX) maxX = lm.x;
            if (lm.y > maxY) maxY = lm.y;
        }
        return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
    }

    validate(faceResult) {
        if (!faceResult || faceResult.faceCount === 0) {
            return { state: FACE_STATE.NO_FACE, message: 'صورت خود را مقابل دوربین قرار دهید' };
        }
        if (faceResult.faceCount > 1) {
            return { state: FACE_STATE.MULTIPLE_FACES, message: 'فقط یک نفر باید مقابل دوربین باشد' };
        }
        const bbox = this.computeBBox(faceResult.landmarks[0]);
        if (!bbox) {
            return { state: FACE_STATE.NO_FACE, message: 'صورت خود را مقابل دوربین قرار دهید' };
        }
        const g = this.guide;
        if (bbox.width < g.minWidth || bbox.height < g.minHeight) {
            return { state: FACE_STATE.TOO_SMALL, message: 'کمی به دوربین نزدیک‌تر شوید' };
        }
        if (bbox.width > g.maxWidth || bbox.height > g.maxHeight) {
            return { state: FACE_STATE.TOO_LARGE, message: 'کمی از دوربین فاصله بگیرید' };
        }
        const insideX = bbox.x >= g.minX && (bbox.x + bbox.width) <= g.maxX;
        const insideY = bbox.y >= g.minY && (bbox.y + bbox.height) <= g.maxY;
        if (!insideX || !insideY) {
            return { state: FACE_STATE.OUT_OF_FRAME, message: 'صورت خود را در کادر قرار دهید' };
        }
        return { state: FACE_STATE.VALID, message: 'چهره در موقعیت مناسب است' };
    }
}

// ============================================================
// 🔧 HEAD POSE DETECTOR - نسخه اصلاح‌شده
// ============================================================
class HeadPoseDetector {

    avgLandmarks(landmarks, indices) {
        let x = 0, y = 0, count = 0;
        for (const idx of indices) {
            const lm = landmarks[idx];
            if (!lm) continue;
            x += lm.x;
            y += lm.y;
            count += 1;
        }
        if (!count) return null;
        return { x: x / count, y: y / count };
    }

    estimateHeadPose(landmarks) {
        if (!landmarks || landmarks.length < 400) return null;

        // ──────────────────────────────────────────────────────────
        // 🔧 اصلاح اصلی: آینه‌ای کردن لندمارک‌ها
        // چون ویدیو با scaleX(-1) نمایش داده می‌شود،
        // لندمارک‌ها هم باید آینه‌ای شوند تا جهت‌ها درست باشند
        // ──────────────────────────────────────────────────────────
        const mirrorX = (x) => 1 - x;

        // چشم راست کاربر (در تصویر آینه‌ای سمت راست است)
        const rightEye = this.avgLandmarks(landmarks, [33, 133, 159, 145]);
        // چشم چپ کاربر (در تصویر آینه‌ای سمت چپ است)
        const leftEye = this.avgLandmarks(landmarks, [263, 362, 386, 374]);
        const nose = landmarks[1];
        const forehead = landmarks[10];
        const chin = landmarks[152];

        if (!rightEye || !leftEye || !nose || !forehead || !chin) return null;

        // آینه‌ای کردن مختصات
        const rEyeX = mirrorX(rightEye.x);
        const lEyeX = mirrorX(leftEye.x);
        const noseX = mirrorX(nose.x);
        const rEyeY = rightEye.y;
        const lEyeY = leftEye.y;
        const noseY = nose.y;
        const chinY = chin.y;
        const foreheadY = forehead.y;
        const centerX_orig = (rightEye.x + leftEye.x) / 2;
        const centerY = (rEyeY + lEyeY) / 2;
        const centerX = mirrorX(centerX_orig);

        // بردار بین دو چشم (در تصویر آینه‌ای)
        const eyeVecX = lEyeX - rEyeX;
        const eyeVecY = lEyeY - rEyeY;
        const eyeDist = Math.hypot(eyeVecX, eyeVecY);

        if (eyeDist < 0.01) return null;

        // بردار واحد جهت چپ
        const unitLeftX = eyeVecX / eyeDist;
        const unitLeftY = eyeVecY / eyeDist;

        // بردار بینی از مرکز چشم‌ها
        const noseVecX = noseX - centerX;
        const noseVecY = noseY - centerY;

        // تصویر بردار بینی روی محور چپ-راست
        const projection = noseVecX * unitLeftX + noseVecY * unitLeftY;

        // محاسبه زاویه چرخش سر
        const yawRad = Math.atan2(projection, eyeDist * 0.6);
        const yaw = yawRad * (180 / Math.PI);

        const faceHeight = Math.abs(chinY - foreheadY) || eyeDist * 2.2;
        const pitch = ((noseY - centerY) / faceHeight) * 90;
        const roll = Math.atan2(eyeVecY, eyeVecX) * (180 / Math.PI);

        return { yaw, pitch, roll, eyeDist };
    }
}

// ============================================================
// BLINK DETECTOR
// ============================================================
class BlinkDetector {
    constructor(config) {
        this.config = config;
        this.state = 'open';
        this.closedAt = null;
    }

    reset() {
        this.state = 'open';
        this.closedAt = null;
    }

    getScore(categories) {
        if (!categories || !categories.length) return 0;
        const left = categories.find(c => c.categoryName === 'eyeBlinkLeft');
        const right = categories.find(c => c.categoryName === 'eyeBlinkRight');
        return ((left ? left.score : 0) + (right ? right.score : 0)) / 2;
    }

    update(score, timestamp) {
        if (typeof score !== 'number' || isNaN(score)) return false;
        if (this.state === 'open' && score >= this.config.closureThreshold) {
            this.state = 'closed';
            this.closedAt = timestamp;
            return false;
        }
        if (this.state === 'closed') {
            const duration = timestamp - this.closedAt;
            if (score <= this.config.openThreshold) {
                this.state = 'open';
                if (duration >= this.config.minDurationMs && duration <= this.config.maxDurationMs) return true;
            }
            if (duration > this.config.maxDurationMs) this.state = 'open';
        }
        return false;
    }
}

// ============================================================
// EVIDENCE COLLECTOR
// ============================================================
class EvidenceCollector {
    constructor(videoEl, config) {
        this.videoEl = videoEl;
        this.config = config;
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
        this.frames = [];
        this.lastCaptureAt = 0;
    }

    maybeCapture(timestamp, stage) {
        if (timestamp - this.lastCaptureAt < this.config.captureIntervalMs) return;
        if (!this.videoEl || this.videoEl.readyState < 2 || !this.videoEl.videoWidth) return;
        this.lastCaptureAt = timestamp;
        const maxWidth = 640;
        const scale = Math.min(1, maxWidth / this.videoEl.videoWidth);
        this.canvas.width = Math.floor(this.videoEl.videoWidth * scale);
        this.canvas.height = Math.floor(this.videoEl.videoHeight * scale);
        try {
            this.ctx.drawImage(this.videoEl, 0, 0, this.canvas.width, this.canvas.height);
            this.canvas.toBlob((blob) => {
                if (!blob) return;
                this.frames.push({ blob, timestamp: Date.now(), localStage: stage || '' });
                this.frames.sort((a, b) => a.timestamp - b.timestamp);
                const maxBuffer = Math.max(this.config.maxFrames + 5, 20);
                if (this.frames.length > maxBuffer) this.frames = this.frames.slice(-maxBuffer);
            }, 'image/jpeg', 0.85);
        } catch (e) {}
    }

    hasEnough() { return this.frames.length >= this.config.minFrames; }
    getFrames() { return this.frames.slice(-this.config.maxFrames).map(item => item.blob); }
}

// ============================================================
// UI
// ============================================================
class VerificationUI {
    constructor() {
        this.video = document.getElementById('fv-video');
        this.guide = document.getElementById('fv-guide');
        this.status = document.getElementById('fv-status');
        this.instruction = document.getElementById('fv-instruction');
        this.timer = document.getElementById('fv-timer');
        this.overlay = document.getElementById('fv-overlay');
        this.overlayText = document.getElementById('fv-overlay-text');
        this.resultCard = document.getElementById('fv-result');
        this.resultIcon = document.getElementById('fv-result-icon');
        this.resultTitle = document.getElementById('fv-result-title');
        this.resultMessage = document.getElementById('fv-result-message');
        this.retryBtn = document.getElementById('fv-retry');
        this.dots = Array.from(document.querySelectorAll('#fv-progress .fv-dot'));
    }

    setGuide(color) {
        this.guide.classList.remove('green', 'red', 'warning');
        if (color) this.guide.classList.add(color);
    }

    setStatus(message, type = 'info') {
        this.status.textContent = message;
        this.status.className = `fv-message ${type}`;
    }

    setInstruction(message) {
        if (!message) { this.instruction.classList.add('fv-hidden'); return; }
        this.instruction.classList.remove('fv-hidden');
        this.instruction.textContent = message;
    }

    setTimer(ms) {
        this.timer.textContent = formatTime(ms);
        if (ms <= 10000) this.timer.style.color = '#dc2626';
        else if (ms <= 30000) this.timer.style.color = '#d97706';
        else this.timer.style.color = '#111827';
    }

    setProgress(doneCount, activeIndex) {
        this.dots.forEach((dot, index) => {
            dot.classList.remove('done', 'active');
            if (index < doneCount) {
                dot.classList.add('done');
                dot.innerHTML = '<i class="bi bi-check-lg"></i>';
            } else if (index === activeIndex) {
                dot.classList.add('active');
                dot.textContent = String(index + 1);
            } else {
                dot.textContent = String(index + 1);
            }
        });
    }

    showOverlay(show, text) {
        if (show) {
            this.overlay.classList.remove('fv-hidden');
            this.overlayText.textContent = text || 'در حال پردازش...';
        } else {
            this.overlay.classList.add('fv-hidden');
        }
    }

    showResult(type, title, message, canRetry = false) {
        this.resultCard.style.display = 'block';
        this.resultCard.className = `fv-result-card ${type === 'success' ? 'success' : 'error'}`;
        this.resultIcon.innerHTML = type === 'success'
            ? '<i class="bi bi-check-circle-fill"></i>'
            : '<i class="bi bi-x-octagon-fill"></i>';
        this.resultTitle.textContent = title;
        this.resultMessage.textContent = message;
        this.retryBtn.classList.toggle('fv-hidden', !canRetry);
    }

    hideCameraControls() {
        this.setInstruction(null);
        this.showOverlay(false);
    }
}

// ============================================================
// MAIN CONTROLLER
// ============================================================
class VerificationController {
    constructor(config) {
        this.config = config;
        this.ui = new VerificationUI();
        this.camera = new CameraController(this.ui.video);
        this.landmarker = new FaceLandmarkerController(config);
        this.api = new VerificationApi(config.csrfToken, config.startUrl, config.completeUrlBase);
        this.session = null;
        this.dynamicConfig = null;
        this.validator = null;
        this.headPose = new HeadPoseDetector();
        this.blinkDetector = null;
        this.evidence = null;
        this.headPoseConfig = {};
        this.faceState = FACE_STATE.NO_FACE;
        this.challengeState = CHALLENGE_STATE.IDLE;
        this.verificationState = VERIFICATION_STATE.NOT_STARTED;
        this.stableSince = null;
        this.currentStepIndex = 0;
        this.stepConditionSince = null;
        this.challengeSequence = [];
        this.clockOffset = 0;
        this.loopTimer = null;
        this.timerInterval = null;
        this.isBusy = false;
        this.isTerminated = false;

        this.ui.retryBtn.addEventListener('click', () => {
            window.location.reload();
        });
        window.addEventListener('beforeunload', () => this.cleanup());
    }

    async init() {
        try {
            this.ui.showOverlay(true, 'در حال آماده‌سازی دوربین...');
            await this.camera.start();
            this.ui.showOverlay(true, 'در حال بارگذاری مدل تشخیص چهره...');
            await this.landmarker.init();
            this.ui.showOverlay(true, 'در حال ایجاد نشست احراز هویت...');
            await this.startSession();
            this.ui.showOverlay(false);
            this.startTimer();
            this.startLoop();
        } catch (error) {
            console.error('❌ Verification Init Error:', error);
            this.failWithCode(error && error.code ? error.code : 'PROCESSING_ERROR');
        }
    }

    async startSession() {
        const data = await this.api.start();
        if (data.already_verified) {
            this.terminate(VERIFICATION_STATE.VERIFIED);
            this.ui.showResult('success', 'حضور شما قبلاً تایید شده است', 'برای این درخواست، حضور شما قبلاً ثبت شده است.');
            return;
        }
        this.session = data;
        this.dynamicConfig = data.config || {};

        const guideConfig = this.dynamicConfig.guide || {
            minX: 0.20, maxX: 0.80, minY: 0.12, maxY: 0.88,
            minWidth: 0.22, maxWidth: 0.70, minHeight: 0.22, maxHeight: 0.85
        };
        const blinkConfig = this.dynamicConfig.blink || {
            closureThreshold: 0.55, openThreshold: 0.25, minDurationMs: 60, maxDurationMs: 900
        };
        const evidenceConfig = this.dynamicConfig.evidence || {
            minFrames: 5, maxFrames: 12, captureIntervalMs: 130
        };
        this.headPoseConfig = this.dynamicConfig.head || { yawMinDeg: 18, holdMs: 250 };

        this.validator = new FacePositionValidator(guideConfig);
        this.blinkDetector = new BlinkDetector(blinkConfig);
        this.evidence = new EvidenceCollector(this.ui.video, evidenceConfig);
        this.challengeSequence = data.challenge || ['TURN_LEFT', 'TURN_RIGHT', 'BLINK'];

        const serverTime = new Date(data.server_time).getTime();
        this.clockOffset = serverTime - Date.now();
        this.verificationState = VERIFICATION_STATE.IN_PROGRESS;
        this.ui.setProgress(0, 0);
        this.ui.setStatus('دوربین آماده است. صورت خود را داخل کادر قرار دهید.', 'info');
    }

    remainingMs() {
        if (!this.session || !this.session.deadline_at) return 0;
        const deadline = new Date(this.session.deadline_at).getTime();
        const estimatedServerNow = Date.now() + this.clockOffset;
        return Math.max(0, deadline - estimatedServerNow);
    }

    startTimer() {
        this.timerInterval = setInterval(() => {
            if (this.isTerminated) return;
            const remaining = this.remainingMs();
            this.ui.setTimer(remaining);
            if (remaining <= 0) {
                this.terminate(VERIFICATION_STATE.EXPIRED);
                this.ui.showResult('error', 'مهلت احراز هویت به پایان رسید', 'در مدت تعیین‌شده احراز هویت تکمیل نشد.');
            }
        }, 250);
    }

    startLoop() {
        const interval = this.dynamicConfig.inferenceIntervalMs || 80;
        this.loopTimer = setInterval(() => {
            if (this.isTerminated || this.isBusy) return;
            this.isBusy = true;
            try {
                const timestamp = performance.now();
                const result = this.landmarker.detect(this.ui.video, timestamp);
                this.processFrame(result, timestamp);
            } catch (e) {} finally {
                this.isBusy = false;
            }
        }, interval);
    }

    processFrame(result, timestamp) {
        if (!this.session || !this.validator || this.isTerminated) return;

        const position = this.validator.validate(result);

        if (position.state !== FACE_STATE.VALID) {
            this.faceState = position.state;
            this.stableSince = null;
            this.stepConditionSince = null;
            if (this.blinkDetector) this.blinkDetector.reset();
            this.ui.setGuide('red');
            this.ui.setStatus(position.message, 'danger');
            if (this.challengeState === CHALLENGE_STATE.ACTIVE) {
                this.challengeState = CHALLENGE_STATE.PAUSED;
                this.ui.setInstruction('صورت خود را دوباره در کادر قرار دهید');
            }
            return;
        }

        this.faceState = FACE_STATE.VALID;
        this.ui.setGuide('green');

        if (!this.stableSince) {
            this.stableSince = timestamp;
            this.ui.setStatus('چهره در موقعیت مناسب است', 'success');
            return;
        }

        const stableMs = this.dynamicConfig.stableDurationMs || 700;
        if (timestamp - this.stableSince < stableMs) {
            this.ui.setStatus('چهره در موقعیت مناسب است', 'success');
            return;
        }

        this.faceState = FACE_STATE.STABLE;
        this.ui.setStatus('چهره آماده است', 'success');

        if (this.challengeState === CHALLENGE_STATE.IDLE) this.startChallenge();
        if (this.challengeState === CHALLENGE_STATE.PAUSED) {
            this.challengeState = CHALLENGE_STATE.ACTIVE;
            this.stepConditionSince = null;
            this.ui.setInstruction(this.getCurrentInstruction());
        }

        if (this.challengeState === CHALLENGE_STATE.ACTIVE) {
            if (this.evidence) this.evidence.maybeCapture(timestamp, this.getCurrentStep());
            this.processChallenge(result, timestamp);
        } else if (this.challengeState === CHALLENGE_STATE.COMPLETED) {
            this.processEvidenceFinalization(timestamp);
        }
    }

    startChallenge() {
        this.challengeState = CHALLENGE_STATE.ACTIVE;
        this.currentStepIndex = 0;
        this.stepConditionSince = null;
        this.ui.setProgress(0, 0);
        this.ui.setInstruction(this.getCurrentInstruction());
    }

    getCurrentStep() { return this.challengeSequence[this.currentStepIndex] || null; }

    getCurrentInstruction() {
        const step = this.getCurrentStep();
        if (step === 'TURN_LEFT') return '⬅️ سرتان را به سمت چپِ خودتان بچرخانید';
        if (step === 'TURN_RIGHT') return '➡️ سرتان را به سمت راستِ خودتان بچرخانید';
        if (step === 'BLINK') return '😐 یک بار پلک بزنید';
        return 'لطفاً صبر کنید';
    }

    // ──────────────────────────────────────────────────────────────
    // 🔧 اصلاح اصلی: تشخیص جهت چرخش سر
    // ──────────────────────────────────────────────────────────────
    processChallenge(result, timestamp) {
        const step = this.getCurrentStep();
        if (!step) { this.completeChallenge(); return; }

        if (step === 'TURN_LEFT' || step === 'TURN_RIGHT') {
            const pose = this.headPose.estimateHeadPose(result.landmarks[0]);
            if (!pose) return;

            const minYaw = this.headPoseConfig.yawMinDeg || 18;
            const holdMs = this.headPoseConfig.holdMs || 250;

            // ──────────────────────────────────────────────
            // 🔧 شرط‌های اصلاح‌شده:
            // در تصویر آینه‌ای:
            //   چرخش به چپ کاربر → بینی به چپ → در مختصات آینه‌ای:
            //   بینی نسبت به مرکز چشم‌ها به سمت چپ حرکت می‌کند
            //   → در محاسبه ما: وقتی بینی به سمت چپ (در تصویر آینه‌ای)
            //     حرکت کند، چون محور واحد از چشم راست به چشم چپ
            //     (در تصویر آینه‌ای: از راست به چپ) جهت‌گیری شده،
            //     تصویر مثبت می‌شود.
            //   پس: چرخش چپ → مثبت، چرخش راست → منفی
            // ──────────────────────────────────────────────
            const correctCondition = step === 'TURN_LEFT'
                ? pose.yaw >= minYaw      // چرخش چپ → مثبت
                : pose.yaw <= -minYaw;    // چرخش راست → منفی

            const wrongCondition = step === 'TURN_LEFT'
                ? pose.yaw <= -minYaw     // چرخش راست (اشتباه)
                : pose.yaw >= minYaw;     // چرخش چپ (اشتباه)

            if (wrongCondition) {
                this.stepConditionSince = null;
                this.ui.setInstruction(
                    step === 'TURN_LEFT'
                        ? '⚠️ جهت اشتباه است! لطفاً به سمت چپِ خودتان بچرخانید'
                        : '⚠️ جهت اشتباه است! لطفاً به سمت راستِ خودتان بچرخانید'
                );
                return;
            }

            if (correctCondition) {
                if (!this.stepConditionSince) this.stepConditionSince = timestamp;
                const heldMs = timestamp - this.stepConditionSince;
                if (heldMs >= holdMs) this.completeStep();
                else this.ui.setInstruction('✅ عالی است! حالت را نگه دارید...');
            } else {
                this.stepConditionSince = null;
                this.ui.setInstruction(this.getCurrentInstruction());
            }
            return;
        }

        if (step === 'BLINK') {
            const blendCategories = result.blendshapes && result.blendshapes[0]
                ? result.blendshapes[0].categories : null;
            const score = this.blinkDetector.getScore(blendCategories);
            const blinked = this.blinkDetector.update(score, timestamp);
            if (blinked) this.completeStep();
        }
    }

    completeStep() {
        this.currentStepIndex += 1;
        this.stepConditionSince = null;
        if (this.blinkDetector) this.blinkDetector.reset();
        if (this.currentStepIndex >= this.challengeSequence.length) this.completeChallenge();
        else {
            this.ui.setProgress(this.currentStepIndex, this.currentStepIndex);
            this.ui.setInstruction(this.getCurrentInstruction());
        }
    }

    completeChallenge() {
        this.challengeState = CHALLENGE_STATE.COMPLETED;
        this.verificationState = VERIFICATION_STATE.CAPTURING;
        this.ui.setProgress(this.challengeSequence.length, this.challengeSequence.length);
        this.ui.setInstruction('در حال جمع‌آوری شواهد...');
        this.ui.setStatus('چالش‌ها کامل شد. لطفاً چند لحظه صبر کنید.', 'info');
    }

    processEvidenceFinalization(timestamp) {
        if (!this.evidence || this.isTerminated) return;
        this.evidence.maybeCapture(timestamp, 'FINAL');
        if (this.evidence.hasEnough()) this.submitEvidence();
    }

    buildChallengeResult() {
        const result = {};
        for (const step of this.challengeSequence) result[step] = true;
        return result;
    }

    async submitEvidence() {
        if (this.isTerminated || this.verificationState === VERIFICATION_STATE.SUBMITTING) return;
        this.verificationState = VERIFICATION_STATE.SUBMITTING;
        this.ui.setInstruction(null);
        this.ui.setStatus('در حال ارسال شواهد به سرور...', 'info');
        this.ui.showOverlay(true, 'در حال پردازش نهایی...');

        const frames = this.evidence.getFrames();
        const challengeResult = this.buildChallengeResult();

        try {
            const data = await this.api.complete(this.session.session_id, frames, challengeResult);
            this.ui.showOverlay(false);

            if (data.status === 'VERIFIED') {
                this.terminate(VERIFICATION_STATE.VERIFIED);
                this.ui.showResult('success', 'احراز هویت چهره با موفقیت انجام شد', 'حضور شما ثبت شد.');
            } else if (data.status === 'SUSPICIOUS') {
                this.terminate(VERIFICATION_STATE.FAILED);
                this.ui.showResult('error', 'تطبیق چهره با اطمینان کافی انجام نشد', 'نتیجه برای بررسی بیشتر ثبت شد.', true);
            } else {
                this.terminate(VERIFICATION_STATE.FAILED);
                this.ui.showResult('error', 'احراز هویت موفق نبود', mapErrorMessage(data.status || data.code), true);
            }
        } catch (error) {
            this.ui.showOverlay(false);
            this.failWithCode(error && error.code ? error.code : 'PROCESSING_ERROR');
        }
    }

    failWithCode(code) {
        this.terminate(VERIFICATION_STATE.FAILED);
        this.ui.showOverlay(false);
        this.ui.showResult('error', 'احراز هویت موفق نبود', mapErrorMessage(code), true);
    }

    terminate(state) {
        if (this.isTerminated) return;
        this.isTerminated = true;
        this.verificationState = state;
        if (state === VERIFICATION_STATE.VERIFIED) window.faceVerificationSuccess = true;
        if (this.loopTimer) { clearInterval(this.loopTimer); this.loopTimer = null; }
        if (this.timerInterval) { clearInterval(this.timerInterval); this.timerInterval = null; }
        this.camera.stop();
        this.landmarker.close();
    }

    cleanup() { this.terminate(this.verificationState); }
}

// ============================================================
// INIT - دو حالت: مودال داشبورد و صفحه مستقل
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    // حالت ۱: مودال داخل داشبورد دانش‌آموز
    const root = document.getElementById('fv-root');
    if (root && root.dataset.startUrl) {
        const config = {
            attendanceRequestId: root.dataset.attendanceRequestId,
            startUrl: root.dataset.startUrl,
            completeUrlBase: root.dataset.completeUrlBase,
            csrfToken: root.dataset.csrfToken,
            mediaPipe: {
                moduleUrl: root.dataset.mediaPipeModuleUrl,
                wasmBase: root.dataset.mediaPipeWasmBase,
                modelUrl: root.dataset.mediaPipeModelUrl,
            }
        };
        window.currentVerificationController = new VerificationController(config);
        window.currentVerificationController.init();
        return;
    }

    // حالت ۲: صفحه مستقل احراز هویت (verify.html)
    if (window.FV_CONFIG && window.FV_CONFIG.startUrl) {
        const config = {
            attendanceRequestId: window.FV_CONFIG.requestId,
            startUrl: window.FV_CONFIG.startUrl,
            completeUrlBase: window.FV_CONFIG.completeUrlBase,
            csrfToken: window.FV_CONFIG.csrfToken,
            mediaPipe: {
                moduleUrl: window.FV_CONFIG.mpModule,
                wasmBase: window.FV_CONFIG.mpWasm,
                modelUrl: window.FV_CONFIG.mpModel,
            }
        };
        window.currentVerificationController = new VerificationController(config);
        window.currentVerificationController.init();
        return;
    }

    // حالت ۳: دکمه‌های شروع اسکن در داشبورد
    const triggers = document.querySelectorAll('.face-verify-trigger');
    if (triggers.length > 0) {
        triggers.forEach(btn => {
            btn.addEventListener('click', function () {
                const requestId = this.dataset.requestId;
                const startUrl = this.dataset.startUrl;
                const completeUrlBase = this.dataset.completeUrlBase;

                // نمایش مودال
                const modal = new bootstrap.Modal(document.getElementById('faceVerificationModal'));
                modal.show();

                // تنظیم تنظیمات
                const fvRoot = document.getElementById('fv-root');
                if (fvRoot) {
                    fvRoot.dataset.attendanceRequestId = requestId;
                    fvRoot.dataset.startUrl = startUrl;
                    fvRoot.dataset.completeUrlBase = completeUrlBase;
                    fvRoot.dataset.csrfToken = getCookie('csrftoken');
                }

                // تنظیم مدیاپایپ
                const mpConfig = window.MEDIAPIPE_CONFIG || {};
                if (fvRoot) {
                    fvRoot.dataset.mediaPipeModuleUrl = mpConfig.moduleUrl || '';
                    fvRoot.dataset.mediaPipeWasmBase = mpConfig.wasmBase || '';
                    fvRoot.dataset.mediaPipeModelUrl = mpConfig.modelUrl || '';
                }

                // شروع فرآیند
                const config = {
                    attendanceRequestId: requestId,
                    startUrl: startUrl,
                    completeUrlBase: completeUrlBase,
                    csrfToken: getCookie('csrftoken'),
                    mediaPipe: {
                        moduleUrl: mpConfig.moduleUrl || '',
                        wasmBase: mpConfig.wasmBase || '',
                        modelUrl: mpConfig.modelUrl || '',
                    }
                };
                window.currentVerificationController = new VerificationController(config);
                window.currentVerificationController.init();
            });
        });
    }
});

})();