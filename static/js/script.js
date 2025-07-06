document.addEventListener('DOMContentLoaded', () => {

    // --- 1. SETUP SHARED UTILITIES ---

    // Mobile Menu Toggle
    const menuToggle = document.getElementById('menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    if (menuToggle && navLinks) {
        menuToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }

    // EFFICIENT INTERSECTION OBSERVER for ANIMATIONS & LAZY LOADING
    const observer = new IntersectionObserver((entries, observerInstance) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Handle lazy loading images
                if (entry.target.matches('img.lazy-load')) {
                    entry.target.src = entry.target.dataset.src;
                    entry.target.onload = () => {
                        entry.target.classList.add('loaded');
                    };
                } else {
                    // Handle general animations for non-image elements
                    entry.target.classList.add('visible');
                }
                // Stop observing the element once it's visible/loaded
                observerInstance.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    // Observe all elements that need lazy loading or animation
    document.querySelectorAll('.animate-on-scroll, img.lazy-load').forEach(el => observer.observe(el));


    // --- 2. PAGE-SPECIFIC INITIALIZATION ---
    if (document.getElementById('activities-container')) {
        fetchActivities();
    }

    if (document.getElementById('post-management')) {
        loadLeaderDashboard();
    }

    if (document.getElementById('suggestions-list')) {
        loadSuggestions();
    }

    const createPostForm = document.getElementById('create-post-form');
    if (createPostForm) {
        createPostForm.addEventListener('submit', handleCreatePost);
    }
});


// --- Reusable API Fetch Function ---
async function apiRequest(url, method = 'GET', body = null, isFormData = false) {
    const options = {
        method,
        headers: {}
    };
    if (body) {
        if (isFormData) {
            options.body = body;
        } else {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }
    }
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Something went wrong');
        }
        return response.status === 204 ? null : response.json();
    } catch (error) {
        console.error('API Request Error:', error);
        alert(`Error: ${error.message}`);
        throw error;
    }
}

// --- Function for Creating Media Carousel ---
function createMediaCarousel(mediaItems, postId) {
    if (!mediaItems || mediaItems.length === 0) {
        return '';
    }

    if (mediaItems.length === 1) {
        const mediaPath = mediaItems[0];
        const element = mediaPath.endsWith('.mp4') || mediaPath.endsWith('.webm') ?
            `<video src="/static/${mediaPath}" controls></video>` :
            `<img src="/static/${mediaPath}" alt="Activity Media">`;
        return `<div class="media-carousel">${element}</div>`;
    }

    const carouselId = `carousel-${postId}`;
    const itemsHtml = mediaItems.map((path, index) => `
        <div class="carousel-item ${index === 0 ? 'active' : ''}">
            ${path.endsWith('.mp4') || path.endsWith('.webm') ?
                `<video src="/static/${path}" controls></video>` :
                `<img src="/static/${path}" alt="Activity Media ${index + 1}">`
            }
        </div>
    `).join('');

    const indicatorsHtml = mediaItems.map((_, index) => `
        <button class="indicator ${index === 0 ? 'active' : ''}" data-target="${carouselId}" data-slide-to="${index}" aria-label="Go to slide ${index + 1}"></button>
    `).join('');

    return `
        <div class="media-carousel" id="${carouselId}" role="region" aria-label="Media gallery">
            <div class="carousel-inner">${itemsHtml}</div>
            <button class="carousel-control prev" data-target="${carouselId}" data-slide="prev" aria-label="Previous slide"><</button>
            <button class="carousel-control next" data-target="${carouselId}" data-slide="next" aria-label="Next slide">></button>
            <div class="carousel-indicators">${indicatorsHtml}</div>
        </div>
    `;
}

// --- Function for Activities Page ---
async function fetchActivities() {
    const container = document.getElementById('activities-container');
    const totalBudgetEl = document.getElementById('total-budget');
    if (!container) return;

    const animationObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
           if (entry.isIntersecting) {
               entry.target.classList.add('visible');
               observer.unobserve(entry.target);
           }
       });
   }, { threshold: 0.1 });

    try {
        const data = await apiRequest('/api/posts');
        container.innerHTML = ''; // Clear loader

        if (totalBudgetEl) {
            totalBudgetEl.textContent = `₹${data.total_budget.toLocaleString()}`;
        }

        if (data.posts.length === 0) {
            container.innerHTML = '<p>No activities have been posted yet.</p>';
            return;
        }

        data.posts.forEach(post => {
            const postElement = document.createElement('div');
            postElement.className = 'activity-post';
            const mediaHtml = createMediaCarousel(post.media, post.id);

            postElement.innerHTML = `
                <h3>${post.title}</h3>
                <p class="post-location">${post.location}</p>
                <div class="post-meta">
                    <p><strong>Author:</strong> <span>${post.author}</span></p>
                    <p><strong>Date:</strong> <span>${post.timestamp}</span></p>
                    <p><strong>Budget:</strong> <span>₹${post.budget.toLocaleString()}</span></p>
                </div>
                ${mediaHtml}
                <p>${post.description.replace(/\n/g, '<br>')}</p>
                <p><strong>On-ground Team:</strong> ${post.on_ground_members || 'N/A'}</p>
                <div class="comments-section" id="comments-for-${post.id}">
                    <h4>Comments</h4>
                    <div class="comments-list"></div>
                    <form class="comment-form" data-post-id="${post.id}">
                        <div class="form-group">
                           <textarea name="comment_text" placeholder="Add your comment..." required></textarea>
                        </div>
                        <button type="submit" class="btn btn-primary">Post Comment</button>
                    </form>
                </div>
            `;
            container.appendChild(postElement);
            animationObserver.observe(postElement);
            fetchComments(post.id);
        });

        document.querySelectorAll('.comment-form').forEach(form => form.addEventListener('submit', handlePostComment));
        document.querySelectorAll('.media-carousel').forEach(initCarousel);

    } catch (error) {
        container.innerHTML = '<p class="error">Failed to load activities.</p>';
    }
}

// --- Carousel Logic ---
function initCarousel(carousel) {
    const inner = carousel.querySelector('.carousel-inner');
    if (!inner) return; // Not a real carousel (e.g., single image)

    const items = carousel.querySelectorAll('.carousel-item');
    const indicators = carousel.querySelectorAll('.indicator');
    const prevBtn = carousel.querySelector('.carousel-control.prev');
    const nextBtn = carousel.querySelector('.carousel-control.next');
    let currentIndex = 0;
    const totalItems = items.length;

    function goToSlide(index) {
        if (index < 0) index = totalItems - 1;
        if (index >= totalItems) index = 0;

        inner.style.transform = `translateX(-${index * 100}%)`;
        indicators.forEach((ind, i) => ind.classList.toggle('active', i === index));
        currentIndex = index;
    }

    if (prevBtn) prevBtn.addEventListener('click', () => goToSlide(currentIndex - 1));
    if (nextBtn) nextBtn.addEventListener('click', () => goToSlide(currentIndex + 1));
    indicators.forEach(ind => {
        ind.addEventListener('click', () => goToSlide(parseInt(ind.dataset.slideTo)));
    });
}


async function fetchComments(postId) {
    const commentsList = document.querySelector(`#comments-for-${postId} .comments-list`);
    try {
        const comments = await apiRequest(`/api/posts/${postId}/comments`);
        commentsList.innerHTML = '';
        if (comments.length > 0) {
            comments.forEach(comment => {
                const commentEl = document.createElement('div');
                commentEl.className = 'comment';
                commentEl.innerHTML = `
                    <img src="${comment.profile_pic}" alt="${comment.author}">
                    <div class="comment-body">
                        <p><strong class="comment-author">${comment.author}</strong></p>
                        <p>${comment.comment_text}</p>
                        <p class="comment-date">${comment.timestamp}</p>
                    </div>
                `;
                commentsList.appendChild(commentEl);
            });
        } else {
            commentsList.innerHTML = '<p>No comments yet. Be the first to comment!</p>';
        }
    } catch (error) {
        commentsList.innerHTML = '<p class="error">Could not load comments.</p>';
    }
}

async function handlePostComment(event) {
    event.preventDefault();
    const form = event.target;
    const postId = form.dataset.postId;
    const commentText = form.querySelector('textarea[name="comment_text"]').value;
    if (!commentText.trim()) return;
    try {
        await apiRequest(`/api/posts/${postId}/comments`, 'POST', { comment_text: commentText });
        form.reset();
        fetchComments(postId);
    } catch (error) { /* Handled by apiRequest */ }
}

// --- Dashboard Functions ---

async function handleCreatePost(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const mediaFiles = formData.getAll('media');

    if (mediaFiles.length > 0 && mediaFiles[0].name === '') {
        formData.delete('media');
    }

    try {
        await apiRequest('/api/create_post', 'POST', formData, true);
        alert('Post created successfully!');
        form.reset();
        if (document.getElementById('all-posts-list')) {
            loadLeaderDashboardPosts();
        }
    } catch (error) { /* Handled by apiRequest */ }
}

async function loadLeaderDashboard() {
    loadLeaderDashboardPosts();
    loadLeaderDashboardUsers();
}

async function loadLeaderDashboardPosts() {
    const container = document.getElementById('all-posts-list');
    const totalBudgetEl = document.getElementById('total-budget-leader');
    if (!container) return;
    container.innerHTML = '<div class="loader"></div>';
    try {
        const data = await apiRequest('/api/posts');
        container.innerHTML = '';
        totalBudgetEl.textContent = `₹${data.total_budget.toLocaleString()}`;
        data.posts.forEach(post => {
            const item = document.createElement('div');
            item.className = 'dashboard-list-item';
            item.innerHTML = `
                <div class="dashboard-list-item-content">
                    <h4>${post.title}</h4>
                    <p>${post.location} - ₹${post.budget.toLocaleString()}</p>
                </div>
                <div class="dashboard-list-item-actions">
                    <button class="btn btn-danger btn-sm" onclick="deletePost(${post.id})">Delete</button>
                </div>
            `;
            container.appendChild(item);
        });
    } catch (error) {
        container.innerHTML = '<p class="error">Failed to load posts.</p>';
    }
}

async function loadLeaderDashboardUsers() {
    const container = document.getElementById('all-users-list');
    if (!container) return;
    container.innerHTML = '<div class="loader"></div>';
    try {
        const users = await apiRequest('/api/users');
        container.innerHTML = '';
        users.forEach(user => {
            const item = document.createElement('div');
            item.className = 'dashboard-list-item';
            item.innerHTML = `
                <div class="dashboard-list-item-content user-info">
                    <img src="${user.profile_pic_path}" alt="${user.username}">
                    <div>
                        <h4>${user.username}</h4>
                        <p>${user.email} - <strong>${user.role}</strong></p>
                    </div>
                </div>
                <div class="dashboard-list-item-actions">
                    ${user.role === 'Member' ? `<button class="btn btn-primary btn-sm" onclick="promoteUser(${user.id})">Promote</button>` : ''}
                    ${user.role === 'Co-Leader' ? `<button class="btn btn-secondary btn-sm" onclick="demoteUser(${user.id})">Demote</button>` : ''}
                    ${user.role !== 'Leader' ? `<button class="btn btn-danger btn-sm" onclick="deleteUser(${user.id})">Delete</button>` : ''}
                </div>
            `;
            container.appendChild(item);
        });
    } catch (error) {
        container.innerHTML = '<p class="error">Failed to load users.</p>';
    }
}

// --- NEW FUNCTION TO LOAD SUGGESTIONS ---
async function loadSuggestions() {
    const container = document.getElementById('suggestions-list');
    if (!container) return;
    container.innerHTML = '<div class="loader"></div>';

    try {
        const suggestions = await apiRequest('/api/suggestions');
        container.innerHTML = '';
        if (suggestions.length === 0) {
            container.innerHTML = '<p>No suggestions have been submitted yet.</p>';
            return;
        }

        suggestions.forEach(s => {
            const item = document.createElement('div');
            item.className = 'dashboard-list-item';
            item.innerHTML = `
                <div class="dashboard-list-item-content">
                    <p>${s.text}</p>
                    <p style="font-size: 0.8rem; color: var(--text-secondary);">
                        By: <strong>${s.suggester_name}</strong> on ${s.timestamp}
                    </p>
                </div>
            `;
            container.appendChild(item);
        });
    } catch (error) {
        container.innerHTML = '<p class="error">Failed to load suggestions.</p>';
    }
}

// --- Action Functions (called via onclick) ---
async function deletePost(postId) {
    if (confirm('Are you sure you want to delete this post and all its media?')) {
        try {
            await apiRequest(`/api/delete_post/${postId}`, 'DELETE');
            loadLeaderDashboardPosts();
        } catch(e) {/* Handled */}
    }
}
async function promoteUser(userId) {
    if (confirm('Promote this member to Co-Leader?')) {
        try {
            await apiRequest(`/api/promote_user/${userId}`, 'POST');
            loadLeaderDashboardUsers();
        } catch(e) {/* Handled */}
    }
}
async function demoteUser(userId) {
    if (confirm('Demote this Co-Leader to Member?')) {
        try {
            await apiRequest(`/api/demote_user/${userId}`, 'POST');
            loadLeaderDashboardUsers();
        } catch(e) {/* Handled */}
    }
}
async function deleteUser(userId) {
    if (confirm('PERMANENTLY delete this user?')) {
        try {
            await apiRequest(`/api/delete_user/${userId}`, 'DELETE');
            loadLeaderDashboardUsers();
        } catch(e) {/* Handled */}
    }
}