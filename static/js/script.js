document.addEventListener("DOMContentLoaded", function() {
    console.log("Automax Transport JS Loaded!");
});
document.addEventListener("DOMContentLoaded", function () {
    const menuToggle = document.querySelector(".menu-toggle");
    const navLinks = document.querySelector(".nav-links");

    menuToggle.addEventListener("click", function () {
        navLinks.classList.toggle("show");
    });
});


document.addEventListener("DOMContentLoaded", function () {
    const viewAsButton = document.querySelector(".view-as-button");
    const dropdownContent = document.querySelector(".dropdown-content");

    if (viewAsButton) {
        viewAsButton.addEventListener("click", function (event) {
            dropdownContent.classList.toggle("show");
            event.stopPropagation(); // Prevents closing when clicking inside
        });

        // Close dropdown when clicking outside
        document.addEventListener("click", function (event) {
            if (!viewAsButton.contains(event.target) && !dropdownContent.contains(event.target)) {
                dropdownContent.classList.remove("show");
            }
        });
    }
});
