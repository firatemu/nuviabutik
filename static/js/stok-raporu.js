// Detaylı Stok Raporu - Premium JS

(function () {
    'use strict';

    // ApexCharts: Stok Sağlığı Donut
    const saglikEl = document.getElementById('sr-stok-saglik-chart');
    if (saglikEl && window.ApexCharts) {
        const stokOlan = parseInt(saglikEl.dataset.stokOlan, 10) || 0;
        const kritik    = parseInt(saglikEl.dataset.kritik, 10) || 0;
        const tukenmis  = parseInt(saglikEl.dataset.tukenmis, 10) || 0;
        const total     = stokOlan + kritik + tukenmis;
        new ApexCharts(saglikEl, {
            chart: { type: 'donut', height: 280, animations: { enabled: true } },
            series: [stokOlan, kritik, tukenmis],
            labels: ['Stoğu Olan', 'Kritik Stok', 'Tükendi'],
            colors: ['#10b981', '#f59e0b', '#ef4444'],
            legend: { position: 'right', fontSize: '13px' },
            dataLabels: { enabled: false },
            plotOptions: {
                pie: {
                    donut: {
                        labels: {
                            show: true,
                            name: { fontSize: '14px', color: '#6b7280' },
                            value: { fontSize: '28px', fontWeight: 700, color: '#1f2937' },
                            total: {
                                show: true,
                                label: 'Toplam Varyant',
                                color: '#6b7280',
                                formatter: () => total.toLocaleString('tr-TR')
                            }
                        }
                    }
                }
            },
            stroke: { width: 2, colors: ['#fff'] },
            tooltip: { y: { formatter: (v) => v + ' varyant' } }
        }).render();
    }

    // ApexCharts: Kâr Marjı Dağılımı Bar
    const dagilimEl = document.getElementById('sr-kar-dagilimi-chart');
    if (dagilimEl && window.ApexCharts) {
        let data = [];
        try {
            data = JSON.parse(dagilimEl.dataset.dagilim || '[]');
        } catch (e) {
            console.warn('kar dagilimi parse error', e);
        }
        new ApexCharts(dagilimEl, {
            chart: { type: 'bar', height: 280, toolbar: { show: false }, animations: { enabled: true } },
            series: [{ name: 'Varyant Sayısı', data: data.map(d => d.count) }],
            xaxis: { categories: data.map(d => d.range + '%') },
            colors: ['#667eea'],
            plotOptions: { bar: { borderRadius: 6, columnWidth: '55%' } },
            dataLabels: {
                enabled: true,
                style: { fontSize: '12px', fontWeight: 600 },
                offsetY: -20
            },
            grid: { borderColor: 'rgba(0,0,0,0.05)' },
            yaxis: { labels: { formatter: (v) => Math.round(v) } }
        }).render();
    }

    // Bootstrap Offcanvas init (filter sidebar)
    const offEl = document.getElementById('sr-filter-offcanvas');
    if (offEl && window.bootstrap) {
        window.bsOffcanvas = new bootstrap.Offcanvas(offEl, { backdrop: true, scroll: true });
    }

    // Filtre sidebar açma butonu
    const openBtn = document.getElementById('sr-open-filters');
    if (openBtn && window.bsOffcanvas) {
        openBtn.addEventListener('click', () => window.bsOffcanvas.show());
    }

    // Segment butonu: Stok Durumu (radio-based segmented control)
    document.querySelectorAll('.sr-segment input[type="radio"]').forEach(radio => {
        radio.addEventListener('change', function () {
            document.getElementById('sr-durum-hidden').value = this.value;
        });
    });

    // Filtre chip kaldırma
    document.querySelectorAll('.sr-chip button[data-remove-filter]').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const filterKey = this.getAttribute('data-remove-filter');
            applyFilterRemoval(filterKey);
        });
    });

    function applyFilterRemoval(key) {
        const url = new URL(window.location.href);
        if (url.searchParams.has(key)) {
            url.searchParams.delete(key);
            window.location.href = url.toString();
        }
    }

    // Tümünü temizle
    const clearAllBtn = document.getElementById('sr-clear-all');
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', function (e) {
            e.preventDefault();
            clearFilters();
        });
    }

    function clearFilters() {
        const sortField = (document.querySelector('input[name="sort"]') || {}).value || '';
        const sortOrder = (document.querySelector('input[name="order"]') || {}).value || '';
        const inputs = ['arama', 'kategori', 'marka', 'cinsiyet',
                       'kar_orani_min', 'kar_orani_max', 'durum'];
        inputs.forEach(name => {
            const el = document.querySelector(`[name="${name}"]`);
            if (!el) return;
            if (el.tagName === 'SELECT') el.value = el.querySelector('option[value=""]')
                ? '' : (el.querySelector('option[value="hepsi"]') ? 'hepsi' : '');
            else if (el.type === 'radio') {
                const def = document.querySelector(`input[name="${name}"][value=""]`)
                       || document.querySelector(`input[name="${name}"][value="hepsi"]`);
                if (def) def.checked = true;
            } else {
                el.value = '';
            }
        });
        const path = window.location.pathname;
        const qs = new URLSearchParams();
        if (sortField && sortField !== 'urun__ad') {
            qs.set('sort', sortField);
            qs.set('order', sortOrder);
        }
        window.location.href = qs.toString() ? `${path}?${qs}` : path;
    }
    window.clearFilters = clearFilters;

    // Sidebar içindeki form submit'inde hidden durum input'u set et
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', function () {
            const checked = document.querySelector('.sr-segment input[type="radio"]:checked');
            if (checked) {
                document.getElementById('sr-durum-hidden').value = checked.value;
            }
        });
    }
})();
