(function () {
    const form = document.querySelector('.report-entry-form');
    if (!form) return;

    // "Use previous value" — copy the previous balance (and optionally cash)
    // into the per-account inputs. Server-side validation still owns the
    // truth; this is purely a typing shortcut.
    form.querySelectorAll('[data-fill-target]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const balField = form.querySelector('input[name="' + btn.dataset.fillTarget + '"]');
            if (balField && typeof btn.dataset.fillValue !== 'undefined') {
                balField.value = btn.dataset.fillValue;
            }
            if (btn.dataset.fillCashTarget) {
                const cashField = form.querySelector('input[name="' + btn.dataset.fillCashTarget + '"]');
                if (cashField && typeof btn.dataset.fillCashValue !== 'undefined') {
                    cashField.value = btn.dataset.fillCashValue;
                }
            }
        });
    });
})();
