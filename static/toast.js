function getToastIcon(type) {
  switch (type) {
    case 'success':
      return 'bi-check-circle';
    case 'danger':
      return 'bi-exclamation-circle';
    case 'warning':
      return 'bi-exclamation-triangle';
    default:
      return 'bi-info-circle';
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toastId = `toast-${Date.now()}`;
  const wrapper = document.createElement('div');
  wrapper.className = 'toast align-items-center border-0 show';
  wrapper.setAttribute('role', 'status');
  wrapper.setAttribute('aria-live', 'polite');
  wrapper.setAttribute('aria-atomic', 'true');
  wrapper.id = toastId;

  wrapper.innerHTML = `
    <div class="d-flex">
      <div class="toast-body d-flex align-items-center gap-2">
        <i class="bi ${getToastIcon(type)}"></i>
        <span>${message}</span>
      </div>
      <button type="button" class="btn-close btn-close-dark me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  container.appendChild(wrapper);

  const toast = new bootstrap.Toast(wrapper, { delay: 3000 });
  const closeButton = wrapper.querySelector('[data-bs-dismiss="toast"]');

  // Dismiss the toast directly instead of depending on Bootstrap's delegated
  // data-bs-dismiss handler. This keeps the X reliable on the dashboard,
  // including when other dashboard scripts are present.
  if (closeButton) {
    closeButton.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();

      // Remove it immediately so the UI never depends on Bootstrap's hide
      // transition/event machinery for the close action.
      wrapper.classList.remove('show');
      wrapper.remove();

      // Clean up Bootstrap's instance after the DOM node is gone.
      try {
        toast.dispose();
      } catch (e) {}
    });
  }

  toast.show();
}

// The dashboard is an app workspace, so unresolved V2 intelligence states
// belong naturally between analytics and the raw transaction feed. Keep this
// isolated from the dashboard CSS/theme system: the server returns markup that
// reuses existing dashboard/Bootstrap classes.
document.addEventListener('DOMContentLoaded', function () {
  if (!document.querySelector('.dashboard-transactions-card')) return;
  if (document.getElementById('dashboard-needs-attention')) return;

  const pathMatch = window.location.pathname.match(/^\/dashboard\/(\d+)$/);
  const month = pathMatch ? pathMatch[1] : new Date().getMonth() + 1;
  const endpoint = `/dashboard/attention?month=${encodeURIComponent(month)}`;

  fetch(endpoint, { credentials: 'same-origin' })
    .then(function (response) {
      if (!response.ok) throw new Error('Unable to load attention queue');
      return response.text();
    })
    .then(function (markup) {
      if (!markup.trim()) return;
      const transactionsCard = document.querySelector('.dashboard-transactions-card');
      if (!transactionsCard) return;

      const wrapper = document.createElement('div');
      wrapper.innerHTML = markup;
      const section = wrapper.firstElementChild;
      if (section) transactionsCard.closest('.dashboard-section-block').before(section);
    })
    .catch(function () {
      // The dashboard remains fully usable if the intelligence review request fails.
    });
});
