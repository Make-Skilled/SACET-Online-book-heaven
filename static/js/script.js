// Function to handle adding items to the cart
function addToCart(bookId, action) {
    // Logic to add item to cart
    const url = `/addToCart?bookId=${bookId}&action=${action}`;
    fetch(url)
        .then(response => response.json())
        .then(data => {
            // Update the cart UI based on the response
            console.log(data);
            location.reload(); // Reload the page to reflect changes
        })
        .catch(error => console.error('Error:', error));
}

// Function to handle removing items from the cart
function removeFromCart(bookId) {
    const url = `/removeFromCart?bookId=${bookId}`;
    fetch(url)
        .then(response => response.json())
        .then(data => {
            // Update the cart UI based on the response
            console.log(data);
            location.reload(); // Reload the page to reflect changes
        })
        .catch(error => console.error('Error:', error));
}

// Attach event listeners to buttons
document.querySelectorAll('.add-to-cart').forEach(button => {
    button.addEventListener('click', function() {
        const bookId = this.dataset.bookId;
        const action = this.dataset.action;
        addToCart(bookId, action);
    });
});

document.querySelectorAll('.remove-from-cart').forEach(button => {
    button.addEventListener('click', function() {
        const bookId = this.dataset.bookId;
        removeFromCart(bookId);
    });
});
