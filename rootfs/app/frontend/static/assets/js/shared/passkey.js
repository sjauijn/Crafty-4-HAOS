// Base64URL encoding/decoding utilities for WebAuthn

function base64URLToBuffer(base64url) {
    const base64 = base64url.replaceAll('-', '+').replaceAll('_', '/');
    const padding = '='.repeat((4 - base64.length % 4) % 4);
    const base64Padded = base64 + padding;
    const binary = atob(base64Padded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.codePointAt(i);
    }
    return bytes.buffer;
}

function bufferToBase64URL(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCodePoint(bytes[i]);
    }
    const base64 = btoa(binary);
    return base64.replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}
