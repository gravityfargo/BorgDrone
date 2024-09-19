document.querySelectorAll('.toast').forEach(function (element) {
    if (!element.classList.contains('hide')) {
        let toast = new bootstrap.Toast(element);
        toast.show();
        setTimeout(function () {
            element.remove();
        }, 15 * 1000);  // 15 seconds timeout
    }
});

// HTMX requests
htmx.onLoad(function (content) {
    [content].forEach(function (el) {
        if (el.classList.contains('toast')) {
            let toast = new bootstrap.Toast(el);
            toast.show();
            setTimeout(function () {
                el.remove();
            }, 15 * 1000);  // 15 seconds timeout
        }
    });
});

document.body.addEventListener('htmx:targetError', function (evt) {
    console.error(evt.detail);
});
