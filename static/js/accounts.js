(function () {
    const form = document.querySelector('.account-form');
    if (!form) return;

    const isSingle = form.dataset.clientType === 'single';

    const ownerOptionsByCategory = {
        retirement:     ['client_1', 'client_2'],
        non_retirement: ['client_1', 'client_2', 'joint'],
        trust:          ['trust'],
        liability:      ['client_1', 'client_2', 'joint', 'trust'],
    };
    const investmentTypes = new Set(['IRA', 'Roth IRA', '401K', 'Pension', 'Brokerage', 'Money Market']);

    const categoryRadios = form.querySelectorAll('input[name="category"]');
    const ownerRadios = form.querySelectorAll('input[name="owner"]');
    const accountType = form.querySelector('select[name="account_type"]');
    const cashField = form.querySelector('[data-field="cash_balance"]');
    const rateField = form.querySelector('[data-field="interest_rate"]');

    function currentCategory() {
        const c = form.querySelector('input[name="category"]:checked');
        return c ? c.value : null;
    }

    function syncOwners() {
        const cat = currentCategory();
        const allowed = ownerOptionsByCategory[cat] || ['client_1', 'client_2', 'joint', 'trust'];

        ownerRadios.forEach(function (radio) {
            const label = radio.closest('label[data-owner-option]');
            if (!label) return;
            let show = allowed.includes(radio.value);
            if (isSingle && radio.value === 'client_2') show = false;
            label.style.display = show ? '' : 'none';
            if (!show && radio.checked) radio.checked = false;
        });

        // Auto-select the only valid option when trust category narrows it.
        if (cat === 'trust') {
            const trustRadio = form.querySelector('input[name="owner"][value="trust"]');
            if (trustRadio && !trustRadio.checked) trustRadio.checked = true;
        }
    }

    function syncConditionalFields() {
        const cat = currentCategory();
        const type = accountType ? accountType.value : '';

        if (rateField) {
            rateField.style.display = (cat === 'liability') ? '' : 'none';
            if (cat !== 'liability') {
                const input = rateField.querySelector('input');
                if (input) input.value = '';
            }
        }

        if (cashField) {
            const showCash = investmentTypes.has(type);
            cashField.style.display = showCash ? '' : 'none';
            if (!showCash) {
                const input = cashField.querySelector('input');
                if (input) input.value = '';
            }
        }
    }

    function syncAll() { syncOwners(); syncConditionalFields(); }

    categoryRadios.forEach(function (r) { r.addEventListener('change', syncAll); });
    if (accountType) accountType.addEventListener('change', syncConditionalFields);
    syncAll();
})();
