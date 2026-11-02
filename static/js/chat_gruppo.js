
document.addEventListener("DOMContentLoaded", function () {

    const contenitore = document.getElementById(
        "chat-gruppo-messaggi"
    );

    if (contenitore) {
        contenitore.scrollTop = contenitore.scrollHeight;
    }

});
