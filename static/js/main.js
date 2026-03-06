// Copy text to clipboard
function copyText(text) {
    navigator.clipboard.writeText(text).then(function () {
        showToast('Copied to clipboard!');
    }).catch(function () {
        // Fallback for older browsers
        var tmp = document.createElement('textarea');
        tmp.value = text;
        document.body.appendChild(tmp);
        tmp.select();
        document.execCommand('copy');
        document.body.removeChild(tmp);
        showToast('Copied to clipboard!');
    });
}

// Simple toast notification
function showToast(msg) {
    var toast = document.createElement('div');
    toast.textContent = msg;
    toast.style.cssText = 'position:fixed;bottom:24px;right:24px;background:#00ff88;color:#000;' +
        'padding:10px 20px;border-radius:8px;font-size:14px;font-weight:600;z-index:999;' +
        'animation:flashIn 0.3s ease;';
    document.body.appendChild(toast);
    setTimeout(function () {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(function () { toast.remove(); }, 300);
    }, 2000);
}

// Auto-dismiss flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function () {
    var flashes = document.querySelectorAll('.flash');
    flashes.forEach(function (flash) {
        setTimeout(function () {
            flash.style.opacity = '0';
            flash.style.transition = 'opacity 0.3s';
            setTimeout(function () { flash.remove(); }, 300);
        }, 5000);
    });
});
