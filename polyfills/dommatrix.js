/**
 * DOMMatrix / DOMPoint / DOMRect polyfills for Node.js
 *
 * pdfjs-dist (used by n8n's Default Data Loader PDF mode) references these
 * browser-only globals. This file is loaded via NODE_OPTIONS=--require so
 * they are available before any n8n code runs.
 *
 * Mounted into the container at /polyfills/dommatrix.js
 */

'use strict';

if (typeof globalThis.DOMMatrix === 'undefined') {
    globalThis.DOMMatrix = class DOMMatrix {
        constructor(init) {
            // Identity matrix (2D + 3D fields)
            this.a = 1;  this.b = 0;
            this.c = 0;  this.d = 1;
            this.e = 0;  this.f = 0;
            this.m11 = 1; this.m12 = 0; this.m13 = 0; this.m14 = 0;
            this.m21 = 0; this.m22 = 1; this.m23 = 0; this.m24 = 0;
            this.m31 = 0; this.m32 = 0; this.m33 = 1; this.m34 = 0;
            this.m41 = 0; this.m42 = 0; this.m43 = 0; this.m44 = 1;
            this.is2D = true;
            this.isIdentity = true;
            if (typeof init === 'string' || Array.isArray(init)) {
                // minimal parsing not needed for pdfjs — identity is sufficient
            }
        }
        static fromMatrix(other) { return new globalThis.DOMMatrix(); }
        static fromFloat32Array(arr) { return new globalThis.DOMMatrix(); }
        static fromFloat64Array(arr) { return new globalThis.DOMMatrix(); }
        translate(tx = 0, ty = 0, tz = 0) { const m = new globalThis.DOMMatrix(); m.e = tx; m.f = ty; return m; }
        scale(sx = 1, sy = sx, sz = 1, ox = 0, oy = 0, oz = 0) { const m = new globalThis.DOMMatrix(); m.a = sx; m.d = sy; return m; }
        rotate(rotX = 0, rotY, rotZ) { return new globalThis.DOMMatrix(); }
        rotateAxisAngle(x, y, z, angle) { return new globalThis.DOMMatrix(); }
        skewX(sx) { return new globalThis.DOMMatrix(); }
        skewY(sy) { return new globalThis.DOMMatrix(); }
        multiply(other) { return new globalThis.DOMMatrix(); }
        inverse() { return new globalThis.DOMMatrix(); }
        flipX() { return new globalThis.DOMMatrix(); }
        flipY() { return new globalThis.DOMMatrix(); }
        toFloat32Array() { return new Float32Array([this.m11,this.m12,this.m13,this.m14,this.m21,this.m22,this.m23,this.m24,this.m31,this.m32,this.m33,this.m34,this.m41,this.m42,this.m43,this.m44]); }
        toFloat64Array() { return new Float64Array([this.m11,this.m12,this.m13,this.m14,this.m21,this.m22,this.m23,this.m24,this.m31,this.m32,this.m33,this.m34,this.m41,this.m42,this.m43,this.m44]); }
        toString() { return `matrix(${this.a},${this.b},${this.c},${this.d},${this.e},${this.f})`; }
        transformPoint(point) { return new globalThis.DOMPoint(point ? point.x : 0, point ? point.y : 0); }
    };
}

if (typeof globalThis.DOMPoint === 'undefined') {
    globalThis.DOMPoint = class DOMPoint {
        constructor(x = 0, y = 0, z = 0, w = 1) {
            this.x = x; this.y = y; this.z = z; this.w = w;
        }
        static fromPoint(other) {
            return new globalThis.DOMPoint(other ? other.x : 0, other ? other.y : 0, other ? other.z : 0, other ? other.w : 1);
        }
        matrixTransform(matrix) { return new globalThis.DOMPoint(this.x, this.y, this.z, this.w); }
        toJSON() { return { x: this.x, y: this.y, z: this.z, w: this.w }; }
    };
}

if (typeof globalThis.DOMRect === 'undefined') {
    globalThis.DOMRect = class DOMRect {
        constructor(x = 0, y = 0, width = 0, height = 0) {
            this.x = x; this.y = y; this.width = width; this.height = height;
        }
        static fromRect(other) {
            return new globalThis.DOMRect(other ? other.x : 0, other ? other.y : 0, other ? other.width : 0, other ? other.height : 0);
        }
        get top() { return this.height >= 0 ? this.y : this.y + this.height; }
        get left() { return this.width >= 0 ? this.x : this.x + this.width; }
        get bottom() { return this.height >= 0 ? this.y + this.height : this.y; }
        get right() { return this.width >= 0 ? this.x + this.width : this.x; }
        toJSON() { return { x: this.x, y: this.y, width: this.width, height: this.height, top: this.top, left: this.left, bottom: this.bottom, right: this.right }; }
    };
}

if (typeof globalThis.DOMRectReadOnly === 'undefined') {
    globalThis.DOMRectReadOnly = globalThis.DOMRect;
}

if (typeof globalThis.Path2D === 'undefined') {
    globalThis.Path2D = class Path2D {
        constructor(path) {}
        addPath(path, transform) {}
        closePath() {} moveTo(x, y) {} lineTo(x, y) {}
        bezierCurveTo(cp1x, cp1y, cp2x, cp2y, x, y) {}
        quadraticCurveTo(cpx, cpy, x, y) {}
        arc(x, y, radius, startAngle, endAngle, anticlockwise) {}
        arcTo(x1, y1, x2, y2, radius) {}
        ellipse(x, y, radiusX, radiusY, rotation, startAngle, endAngle, anticlockwise) {}
        rect(x, y, width, height) {}
    };
}

// Minimal ImageData stub so pdfjs doesn't crash on canvas operations
if (typeof globalThis.ImageData === 'undefined') {
    globalThis.ImageData = class ImageData {
        constructor(widthOrData, height, settings) {
            if (widthOrData instanceof Uint8ClampedArray) {
                this.data = widthOrData;
                this.width = height;
                this.height = settings ? settings.height : widthOrData.length / (4 * height);
            } else {
                this.width = widthOrData;
                this.height = height;
                this.data = new Uint8ClampedArray(widthOrData * height * 4);
            }
            this.colorSpace = (settings && settings.colorSpace) || 'srgb';
        }
    };
}
