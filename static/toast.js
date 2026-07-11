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
  toast.show();

  wrapper.addEventListener('hidden.bs.toast', function () {
    wrapper.remove();
  });
}
