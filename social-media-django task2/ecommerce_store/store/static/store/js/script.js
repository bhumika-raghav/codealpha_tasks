// Auto-hide success/info messages after a few seconds
document.addEventListener('DOMContentLoaded', function () {
    const messages = document.querySelectorAll('.messages .message');
    messages.forEach(function (msg) {
        setTimeout(function () {
            msg.style.transition = 'opacity 0.5s ease';
            msg.style.opacity = '0';
            setTimeout(function () { msg.remove(); }, 500);
        }, 4000);
    });
});
