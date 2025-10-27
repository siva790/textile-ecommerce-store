/* ========================================
   AMAZON-STYLE PRODUCT PAGE JAVASCRIPT
   Interactive Features & Zoom Functionality
   ======================================== */

// ============ THUMBNAIL IMAGE SWITCHING ============

/**
 * Changes the main image when a thumbnail is clicked
 * @param {HTMLElement} thumbnail - The clicked thumbnail element
 */
function changeMainImage(thumbnail) {
    // Get the main image element
    const mainImage = document.getElementById('mainImage');
    
    // Get the source from the clicked thumbnail
    const newImageSrc = thumbnail.src;
    
    // Add fade out effect
    mainImage.style.opacity = '0';
    
    // Change image after fade out (300ms delay)
    setTimeout(() => {
        mainImage.src = newImageSrc;
        mainImage.style.opacity = '1';
    }, 300);
    
    // Remove 'active' class from all thumbnails
    const allThumbnails = document.querySelectorAll('.thumbnail');
    allThumbnails.forEach(thumb => {
        thumb.classList.remove('active');
    });
    
    // Add 'active' class to clicked thumbnail
    thumbnail.classList.add('active');
    
    // Update zoom background image
    imageZoom('mainImage', 'zoomResult');
}

// ============ IMAGE ZOOM FUNCTIONALITY ============

/**
 * Creates a zoom effect on the main image
 * @param {string} imgID - ID of the main image
 * @param {string} resultID - ID of the zoom result container
 */
function imageZoom(imgID, resultID) {
    const img = document.getElementById(imgID);
    const result = document.getElementById(resultID);
    const lens = document.getElementById('zoomLens');
    
    if (!img || !result || !lens) return;
    
    // Calculate zoom ratio
    const cx = result.offsetWidth / lens.offsetWidth;
    const cy = result.offsetHeight / lens.offsetHeight;
    
    // Set background properties for zoomed result
    result.style.backgroundImage = `url('${img.src}')`;
    result.style.backgroundSize = `${img.width * cx}px ${img.height * cy}px`;
    
    // Execute function when mouse moves over image or lens
    lens.addEventListener('mousemove', moveLens);
    img.addEventListener('mousemove', moveLens);
    
    // Also for touch screens
    lens.addEventListener('touchmove', moveLens);
    img.addEventListener('touchmove', moveLens);
    
    /**
     * Moves the zoom lens and updates the result
     */
    function moveLens(e) {
        e.preventDefault();
        
        // Get cursor position
        const pos = getCursorPos(e);
        
        // Calculate lens position
        let x = pos.x - (lens.offsetWidth / 2);
        let y = pos.y - (lens.offsetHeight / 2);
        
        // Prevent lens from going outside image
        if (x > img.width - lens.offsetWidth) x = img.width - lens.offsetWidth;
        if (x < 0) x = 0;
        if (y > img.height - lens.offsetHeight) y = img.height - lens.offsetHeight;
        if (y < 0) y = 0;
        
        // Set lens position
        lens.style.left = x + 'px';
        lens.style.top = y + 'px';
        
        // Display zoomed result
        result.style.backgroundPosition = `-${x * cx}px -${y * cy}px`;
    }
    
    /**
     * Gets the cursor position relative to the image
     */
    function getCursorPos(e) {
        const bounds = img.getBoundingClientRect();
        const x = (e.pageX || e.touches[0].pageX) - bounds.left - window.pageXOffset;
        const y = (e.pageY || e.touches[0].pageY) - bounds.top - window.pageYOffset;
        return { x, y };
    }
}

// ============ QUANTITY CONTROLS ============

/**
 * Increases the quantity value
 */
function increaseQuantity() {
    const quantityInput = document.getElementById('quantity');
    let currentValue = parseInt(quantityInput.value);
    const maxValue = parseInt(quantityInput.max);
    
    if (currentValue < maxValue) {
        quantityInput.value = currentValue + 1;
        updateQuantityDisplay();
    } else {
        // Show max quantity alert
        showAlert('Maximum quantity reached!', 'warning');
    }
}

/**
 * Decreases the quantity value
 */
function decreaseQuantity() {
    const quantityInput = document.getElementById('quantity');
    let currentValue = parseInt(quantityInput.value);
    const minValue = parseInt(quantityInput.min);
    
    if (currentValue > minValue) {
        quantityInput.value = currentValue - 1;
        updateQuantityDisplay();
    } else {
        // Show min quantity alert
        showAlert('Minimum quantity is 1!', 'info');
    }
}

/**
 * Updates the quantity display (optional animation)
 */
function updateQuantityDisplay() {
    const quantityInput = document.getElementById('quantity');
    
    // Add pulse animation
    quantityInput.style.transform = 'scale(1.1)';
    setTimeout(() => {
        quantityInput.style.transform = 'scale(1)';
    }, 200);
}

// ============ ALERT SYSTEM ============

/**
 * Shows a temporary alert message
 * @param {string} message - Alert message
 * @param {string} type - Alert type (success, warning, info, danger)
 */
function showAlert(message, type = 'info') {
    // Create alert element
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to body
    document.body.appendChild(alert);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        alert.remove();
    }, 3000);
}

// ============ KEYBOARD NAVIGATION ============

/**
 * Allows keyboard navigation through thumbnails
 */
document.addEventListener('keydown', function(e) {
    const thumbnails = Array.from(document.querySelectorAll('.thumbnail'));
    const activeThumbnail = document.querySelector('.thumbnail.active');
    const currentIndex = thumbnails.indexOf(activeThumbnail);
    
    // Right arrow - next image
    if (e.key === 'ArrowRight' && currentIndex < thumbnails.length - 1) {
        changeMainImage(thumbnails[currentIndex + 1]);
    }
    
    // Left arrow - previous image
    if (e.key === 'ArrowLeft' && currentIndex > 0) {
        changeMainImage(thumbnails[currentIndex - 1]);
    }
});

// ============ LAZY LOADING IMAGES ============

/**
 * Lazy loads images for better performance
 */
function lazyLoadImages() {
    const images = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.add('loaded');
                observer.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
}

// ============ SMOOTH SCROLL TO TOP ============

/**
 * Adds a scroll to top button
 */
function addScrollToTop() {
    const scrollBtn = document.createElement('button');
    scrollBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
    scrollBtn.className = 'btn btn-primary rounded-circle position-fixed';
    scrollBtn.style.cssText = 'bottom: 30px; right: 30px; width: 50px; height: 50px; display: none; z-index: 999;';
    scrollBtn.onclick = () => window.scrollTo({ top: 0, behavior: 'smooth' });
    
    document.body.appendChild(scrollBtn);
    
    // Show/hide button based on scroll position
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            scrollBtn.style.display = 'block';
        } else {
            scrollBtn.style.display = 'none';
        }
    });
}

// ============ PRODUCT SHARE FUNCTIONALITY ============

/**
 * Shares the product on social media or copies link
 * @param {string} platform - Social media platform
 */
function shareProduct(platform) {
    const url = window.location.href;
    const title = document.querySelector('.product-title').textContent;
    
    let shareUrl;
    
    switch(platform) {
        case 'facebook':
            shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${url}`;
            break;
        case 'twitter':
            shareUrl = `https://twitter.com/intent/tweet?url=${url}&text=${title}`;
            break;
        case 'pinterest':
            const image = document.getElementById('mainImage').src;
            shareUrl = `https://pinterest.com/pin/create/button/?url=${url}&media=${image}&description=${title}`;
            break;
        case 'whatsapp':
            shareUrl = `https://wa.me/?text=${title} ${url}`;
            break;
        case 'copy':
            navigator.clipboard.writeText(url);
            showAlert('Link copied to clipboard!', 'success');
            return;
        default:
            return;
    }
    
    window.open(shareUrl, '_blank', 'width=600,height=400');
}

// ============ ADD TO WISHLIST ============

/**
 * Adds product to wishlist (localStorage)
 */
function addToWishlist() {
    const productTitle = document.querySelector('.product-title').textContent;
    const productPrice = document.querySelector('.current-price').textContent;
    const productImage = document.getElementById('mainImage').src;
    
    // Get existing wishlist or create new one
    let wishlist = JSON.parse(localStorage.getItem('wishlist')) || [];
    
    // Add product to wishlist
    const product = {
        title: productTitle,
        price: productPrice,
        image: productImage,
        url: window.location.href
    };
    
    // Check if already in wishlist
    const exists = wishlist.some(item => item.url === product.url);
    
    if (!exists) {
        wishlist.push(product);
        localStorage.setItem('wishlist', JSON.stringify(wishlist));
        showAlert('Added to wishlist!', 'success');
    } else {
        showAlert('Already in wishlist!', 'info');
    }
}

// ============ RELATED PRODUCTS AUTO-SCROLL ============

/**
 * Auto-scrolls related products carousel
 */
function autoScrollRelatedProducts() {
    const carousel = document.querySelector('#relatedProductsCarousel');
    if (carousel) {
        setInterval(() => {
            const nextButton = carousel.querySelector('.carousel-control-next');
            if (nextButton) nextButton.click();
        }, 5000); // Every 5 seconds
    }
}

// ============ INITIALIZATION ============

/**
 * Initialize all functions when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize image zoom
    imageZoom('mainImage', 'zoomResult');
    
    // Initialize lazy loading
    lazyLoadImages();
    
    // Add scroll to top button
    addScrollToTop();
    
    // Optional: Auto-scroll related products
    // autoScrollRelatedProducts();
    
    // Add smooth transition to main image
    const mainImage = document.getElementById('mainImage');
    if (mainImage) {
        mainImage.style.transition = 'opacity 0.3s ease-in-out';
    }
    
    // Add smooth transition to quantity input
    const quantityInput = document.getElementById('quantity');
    if (quantityInput) {
        quantityInput.style.transition = 'transform 0.2s ease';
    }
    
    console.log('Amazon-style product page initialized!');
});

// ============ PERFORMANCE OPTIMIZATION ============

/**
 * Debounce function to limit event firing rate
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Use debounce for scroll events
window.addEventListener('scroll', debounce(function() {
    // Scroll-based animations can be added here
}, 100));



