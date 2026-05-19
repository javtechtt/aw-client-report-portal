(function () {
    const form = document.querySelector('.client-form');
    if (!form) return;

    // --- Client 2 section gating: visually de-emphasize when "Single" -------
    const section2 = form.querySelector('[data-client-2-section]');
    const radios = form.querySelectorAll('input[name="client_type"]');

    function syncSection2() {
        const checked = form.querySelector('input[name="client_type"]:checked');
        const isMarried = checked && checked.value === 'married';
        if (section2) section2.classList.toggle('section-disabled', !isMarried);
    }
    radios.forEach(function (r) { r.addEventListener('change', syncSection2); });
    syncSection2();

    // --- Private reserve target auto-suggest --------------------------------
    // Suggest 6 * outflow + deductibles whenever those change, but back off
    // as soon as the user manually edits the target field.
    const outflow = form.querySelector('input[name="monthly_outflow_budget"]');
    const deductibles = form.querySelector('input[name="insurance_deductibles_total"]');
    const target = form.querySelector('input[data-auto-target]');
    if (!outflow || !deductibles || !target) return;

    let userTouchedTarget = target.value !== '' && target.value !== '0' && target.value !== '0.00';
    target.addEventListener('input', function () { userTouchedTarget = true; });

    function recomputeTarget() {
        if (userTouchedTarget) return;
        const o = parseFloat(outflow.value);
        const d = parseFloat(deductibles.value);
        const oNum = isFinite(o) ? o : 0;
        const dNum = isFinite(d) ? d : 0;
        const next = oNum * 6 + dNum;
        target.value = next > 0 ? next.toFixed(2) : '';
    }
    outflow.addEventListener('input', recomputeTarget);
    deductibles.addEventListener('input', recomputeTarget);
})();
