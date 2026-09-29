/**
 * NuviaButik Ürün Listesi Etkileşim Scripti
 * - Kopyalanabilir ürün kodları
 * - Görsel lightbox
 * - Ajax hızlı varyant listesi yükleyici (DOM metodları ile güvenli)
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Ürün Kodu Kopyalama
    document.querySelectorAll('.copy-code-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            var code = this.getAttribute('data-code');
            var targetBtn = this;
            if (code && navigator.clipboard) {
                navigator.clipboard.writeText(code).then(function () {
                    var origText = targetBtn.querySelector('span') ? targetBtn.querySelector('span').textContent : '';
                    if (targetBtn.querySelector('span')) {
                        targetBtn.querySelector('span').textContent = 'Kopyalandı!';
                    }
                    setTimeout(function () {
                        if (targetBtn.querySelector('span')) {
                            targetBtn.querySelector('span').textContent = origText;
                        }
                    }, 1400);
                }).catch(function () {});
            }
        });
    });

    // 2. Görsel Lightbox Önizleme
    var imgModalEl = document.getElementById('imagePreviewModal');
    var lightboxImg = document.getElementById('lightboxImg');
    if (imgModalEl && lightboxImg && window.bootstrap && typeof window.bootstrap.Modal === 'function') {
        var imgModal = new window.bootstrap.Modal(imgModalEl);
        document.querySelectorAll('.ul-img-box').forEach(function (box) {
            box.addEventListener('click', function () {
                var url = this.getAttribute('data-img-url');
                if (url) {
                    lightboxImg.src = url;
                    imgModal.show();
                }
            });
        });
    }

    // 3. Hızlı Varyant Önizleme Modalı
    var varModalEl = document.getElementById('quickVariantModal');
    var modalUrunAd = document.getElementById('modalUrunAd');
    var modalUrunKod = document.getElementById('modalUrunKod');
    var modalVariantBody = document.getElementById('modalVariantBody');
    var modalManageLink = document.getElementById('modalManageVariantsLink');

    if (varModalEl && window.bootstrap && typeof window.bootstrap.Modal === 'function') {
        var varModal = new window.bootstrap.Modal(varModalEl);

        document.querySelectorAll('.btn-quick-variants').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var urunId = this.getAttribute('data-urun-id');
                if (!urunId) return;

                // Tabloyu temizle ve yükleniyor göster
                modalVariantBody.textContent = '';
                var loadingRow = document.createElement('tr');
                var loadingTd = document.createElement('td');
                loadingTd.colSpan = 5;
                loadingTd.className = 'text-center py-4 text-muted';
                loadingTd.textContent = 'Varyantlar yükleniyor...';
                loadingRow.appendChild(loadingTd);
                modalVariantBody.appendChild(loadingRow);

                varModal.show();

                fetch('/urun/ajax/varyantlar/' + urunId + '/')
                    .then(function (r) { return r.json(); })
                    .then(function (res) {
                        modalVariantBody.textContent = '';
                        if (res.success && res.urun) {
                            if (modalUrunAd) modalUrunAd.textContent = res.urun.ad;
                            if (modalUrunKod) {
                                modalUrunKod.textContent = 'Kod: ' + res.urun.urun_kodu + ' | Kategori: ' + res.urun.kategori + ' | Toplam Stok: ' + res.urun.toplam_stok;
                            }
                            if (modalManageLink) {
                                modalManageLink.href = '/urun/' + res.urun.id + '/varyasyon/';
                            }

                            if (res.varyantlar && res.varyantlar.length > 0) {
                                res.varyantlar.forEach(function (v) {
                                    var tr = document.createElement('tr');

                                    // Renk
                                    var tdRenk = document.createElement('td');
                                    var dot = document.createElement('span');
                                    dot.className = 'color-dot';
                                    dot.style.backgroundColor = v.renk_hex || '#6c757d';
                                    tdRenk.appendChild(dot);
                                    var strong = document.createElement('strong');
                                    strong.textContent = v.renk;
                                    tdRenk.appendChild(strong);
                                    tr.appendChild(tdRenk);

                                    // Beden
                                    var tdBeden = document.createElement('td');
                                    var bedenBadge = document.createElement('span');
                                    bedenBadge.className = 'badge bg-light text-dark border';
                                    bedenBadge.textContent = v.beden;
                                    tdBeden.appendChild(bedenBadge);
                                    tr.appendChild(tdBeden);

                                    // Barkod
                                    var tdBarkod = document.createElement('td');
                                    tdBarkod.className = 'text-center font-monospace';
                                    tdBarkod.textContent = v.barkod;
                                    tr.appendChild(tdBarkod);

                                    // Stok
                                    var tdStok = document.createElement('td');
                                    tdStok.className = 'text-end fw-bold';
                                    tdStok.textContent = v.stok_miktari;
                                    tr.appendChild(tdStok);

                                    // Durum
                                    var tdDurum = document.createElement('td');
                                    tdDurum.className = 'text-center';
                                    var stBadge = document.createElement('span');
                                    if (v.stok_miktari === 0) {
                                        stBadge.className = 'badge bg-danger';
                                        stBadge.textContent = 'Tükendi';
                                    } else if (v.stok_miktari <= 10) {
                                        stBadge.className = 'badge bg-warning text-dark';
                                        stBadge.textContent = v.stok_miktari + ' Adet';
                                    } else {
                                        stBadge.className = 'badge bg-success';
                                        stBadge.textContent = v.stok_miktari + ' Adet';
                                    }
                                    tdDurum.appendChild(stBadge);
                                    tr.appendChild(tdDurum);

                                    modalVariantBody.appendChild(tr);
                                });
                            } else {
                                var emptyTr = document.createElement('tr');
                                var emptyTd = document.createElement('td');
                                emptyTd.colSpan = 5;
                                emptyTd.className = 'text-center py-3 text-muted';
                                emptyTd.textContent = 'Kayıtlı varyant bulunamadı.';
                                emptyTr.appendChild(emptyTd);
                                modalVariantBody.appendChild(emptyTr);
                            }
                        } else {
                            var errTr = document.createElement('tr');
                            var errTd = document.createElement('td');
                            errTd.colSpan = 5;
                            errTd.className = 'text-center py-3 text-danger';
                            errTd.textContent = 'Varyant bilgileri alınamadı.';
                            errTr.appendChild(errTd);
                            modalVariantBody.appendChild(errTr);
                        }
                    })
                    .catch(function () {
                        modalVariantBody.textContent = '';
                        var errTr = document.createElement('tr');
                        var errTd = document.createElement('td');
                        errTd.colSpan = 5;
                        errTd.className = 'text-center py-3 text-danger';
                        errTd.textContent = 'Sunucu bağlantı hatası oluştu.';
                        errTr.appendChild(errTd);
                        modalVariantBody.appendChild(errTr);
                    });
            });
        });
    }

    // 4. Arama Input Enter
    var searchInput = document.getElementById('searchQInput');
    var filterForm = document.getElementById('urunFilterForm');
    if (searchInput && filterForm) {
        searchInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                filterForm.submit();
            }
        });
    }
});
