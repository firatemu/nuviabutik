/**
 * NuviaButik Kurumsal Stok Sayım Modülü JavaScript
 * Satis Ekrani mimarisiyle tam uyumlu, barkod + manuel arama,
 * son 5 okutulan vitrini, excel ihracı ve anlık stok eşitleme.
 */

(function ($) {
    'use strict';

    // =========================================================================
    // STATE & DEĞİŞKENLER
    // =========================================================================
    let sayimListesi = [];
    let sayimSonLineId = 0;
    let sonOkutulanBes = [];
    let aktifFiltre = 'all'; // 'all', 'eksik', 'fazla', 'esit'
    let urunAraDebounce = null;
    let codeReader = null;
    let scanningActive = false;

    const _cfg = window.NUVIA_SAYIM_CONFIG || {};
    let sayimNo = _cfg.sayimNo || '';
    let sayimId = _cfg.sayimId || null;
    const csrfToken = _cfg.csrfToken || '';

    // =========================================================================
    // SESLİ BİLDİRİM (WEB AUDIO API)
    // =========================================================================
    let audioCtx = null;
    function getAudioContext() {
        if (!audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) audioCtx = new AudioContext();
        }
        if (audioCtx && audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
        return audioCtx;
    }

    function playTone(freq, type, durationMs) {
        try {
            const ctx = getAudioContext();
            if (!ctx) return;
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = type || 'sine';
            osc.frequency.setValueAtTime(freq, ctx.currentTime);
            gain.gain.setValueAtTime(0.12, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + (durationMs / 1000));
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + (durationMs / 1000));
        } catch (e) {
            // Tarayıcı kısıtlaması durumunda sessiz kal
        }
    }

    function playBeepSuccess() {
        playTone(880, 'sine', 90); // Yüksek A5 sesi
    }

    function playBeepIncrement() {
        playTone(1046.5, 'sine', 70); // C6 sesi (artırma)
    }

    function playBeepError() {
        playTone(220, 'sawtooth', 220); // Düşük A3 sesi (hata)
    }

    function playBeepChime() {
        try {
            playTone(523.25, 'sine', 120);
            setTimeout(() => playTone(659.25, 'sine', 120), 100);
            setTimeout(() => playTone(783.99, 'sine', 200), 200);
        } catch (e) {}
    }

    // =========================================================================
    // YARDIMCI BİLDİRİM FONKSİYONLARI
    // =========================================================================
    let searchFeedbackTimer = null;
    function showSearchFeedback(type, msg, autoHideMs = 3500) {
        const el = document.getElementById('searchFeedback');
        const msgEl = document.getElementById('searchFeedbackMsg');
        if (!el || !msgEl) return;

        el.classList.remove('success', 'danger', 'warning');
        if (type) el.classList.add(type);
        msgEl.textContent = msg || '';
        el.classList.add('show');

        if (searchFeedbackTimer) clearTimeout(searchFeedbackTimer);
        if (autoHideMs && autoHideMs > 0) {
            searchFeedbackTimer = setTimeout(() => {
                el.classList.remove('show', 'success', 'danger', 'warning');
            }, autoHideMs);
        }
    }

    function showToast(type, msg) {
        if (typeof window.showToast === 'function') {
            window.showToast(type, msg);
        } else {
            console.log(`[${type}] ${msg}`);
        }
    }

    function escapeHtml(str) {
        if (str == null || str === '') return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatNumber(n) {
        const x = parseFloat(n);
        if (!isFinite(x)) return '0';
        return x.toLocaleString('tr-TR');
    }

    function timeAgo(date) {
        if (!date) return '';
        const now = new Date();
        const diffSec = Math.round((now - new Date(date)) / 1000);
        if (diffSec < 5) return 'Az önce';
        if (diffSec < 60) return `${diffSec} sn önce`;
        const diffMin = Math.round(diffSec / 60);
        if (diffMin < 60) return `${diffMin} dk önce`;
        return `${Math.round(diffMin / 60)} sa önce`;
    }

    // Canlı Saat
    function updateClock() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        $('#sayimLiveClock').text(timeStr);
    }

    // =========================================================================
    // SAYIM LİSTESİ MANTIĞI (+1 VE SON 5 ÜRÜN)
    // =========================================================================

    /**
     * Ürünü sayım listesine ekler.
     * Eğer varyant zaten listede varsa sayılan_miktar 1 artar.
     * Yoksa 1 adet olarak eklenir.
     * Her durumda son okutulan 5 ürün listesi güncellenir.
     */
    function urunSayimaEkle(urun) {
        const varyantId = parseInt(urun.varyant_id || urun.id, 10);
        const existingIdx = sayimListesi.findIndex(item => item.varyant_id === varyantId);
        let targetItem = null;
        let isIncrement = false;

        const now = new Date();

        if (existingIdx >= 0) {
            // Zaten var -> Miktarı 1 artır
            targetItem = sayimListesi[existingIdx];
            targetItem.sayilan_miktar += 1;
            targetItem.son_okunma_zamani = now;
            isIncrement = true;

            // Sıralamada üstte kalsın isteniyorsa unshift edilebilir
            sayimListesi.splice(existingIdx, 1);
            sayimListesi.unshift(targetItem);

            playBeepIncrement();
            showSearchFeedback('success', `${targetItem.ad} (${targetItem.varyasyon}) adedi artırıldı: ${targetItem.sayilan_miktar}`);
        } else {
            // Yeni ürün -> Listeye 1 adet olarak ekle
            targetItem = {
                lineId: ++sayimSonLineId,
                id: urun.id,
                varyant_id: varyantId,
                ad: urun.ad,
                varyasyon: urun.varyasyon || `${urun.renk || ''} / ${urun.beden || ''}`.trim(),
                beden: urun.beden || 'Tek Beden',
                renk: urun.renk || 'Standart',
                barkod: urun.barkod || '',
                kod: urun.kod || urun.urun_kodu || '',
                kategori: urun.kategori || '',
                stok_miktari: parseInt(urun.stok_miktari, 10) || 0, // sistem stoku
                sayilan_miktar: parseInt(urun.sayilan_miktar, 10) || 1, // bulunan
                pesin_fiyat: parseFloat(urun.pesin_fiyat) || 0.0,
                resim: urun.resim || null,
                son_okunma_zamani: now
            };

            sayimListesi.unshift(targetItem);
            playBeepSuccess();
            showSearchFeedback('success', `${targetItem.ad} sayım listesine eklendi (1 Adet)`);
        }

        // Son Okutulan 5 Ürün listesini güncelle
        guncelleSonOkutulanBes(targetItem);

        // Arayüzü güncelle
        renderSayimTable(targetItem.lineId);
        guncelleOzetMetrikleri();

        // Barkod alanına tekrar odaklan
        $('#barkodInput').focus();
    }

    /**
     * En son okutulan 5 ürün listesini yönetir.
     */
    function guncelleSonOkutulanBes(item) {
        // Varsa listeden çıkar
        sonOkutulanBes = sonOkutulanBes.filter(x => x.varyant_id !== item.varyant_id);
        // Başa ekle
        sonOkutulanBes.unshift(item);
        // 5 ürün ile sınırla
        if (sonOkutulanBes.length > 5) {
            sonOkutulanBes = sonOkutulanBes.slice(0, 5);
        }
        renderSonOkutulanBes();
    }

    function renderSonOkutulanBes() {
        const container = $('#recentScannedContainer');
        if (sonOkutulanBes.length === 0) {
            container.html(`
                <div class="recent-empty">
                    <i class="fas fa-barcode"></i>
                    <span>Barkod okutulduğunda son 5 ürün burada anlık olarak listelenecektir.</span>
                </div>
            `);
            $('#recentSubtext').text('Henüz ürün okutulmadı');
            return;
        }

        $('#recentSubtext').text(`Son ${sonOkutulanBes.length} okuma gösteriliyor`);

        let html = '';
        sonOkutulanBes.forEach((it, index) => {
            const isNewest = index === 0;
            const imgHtml = it.resim
                ? `<img src="${escapeHtml(it.resim)}" class="recent-card-img" alt="Ürün">`
                : `<div class="recent-card-img"><i class="fas fa-box-open"></i></div>`;

            html += `
                <div class="recent-card ${isNewest ? 'recent-card--newest' : ''}" data-line-id="${it.lineId}">
                    <div class="recent-card-top">
                        ${imgHtml}
                        <div class="recent-card-info">
                            <h4 class="recent-card-name" title="${escapeHtml(it.ad)}">${escapeHtml(it.ad)}</h4>
                            <div class="recent-card-variant">${escapeHtml(it.renk)} / ${escapeHtml(it.beden)}</div>
                        </div>
                    </div>
                    <div class="recent-card-bottom">
                        <span class="recent-card-qty" title="Toplam Sayılan">${it.sayilan_miktar} Adet</span>
                        <span class="recent-card-time">${timeAgo(it.son_okunma_zamani)}</span>
                    </div>
                </div>
            `;
        });

        container.html(html);
    }

    // =========================================================================
    // TABLO VE KPI METRİKLERİ
    // =========================================================================

    function renderSayimTable(flashLineId = null) {
        const tbody = $('#sayimTableBody');

        // Filtreye göre elemanları seç
        let goruntulenecekler = sayimListesi.filter(item => {
            const fark = item.sayilan_miktar - item.stok_miktari;
            if (aktifFiltre === 'eksik') return fark < 0;
            if (aktifFiltre === 'fazla') return fark > 0;
            if (aktifFiltre === 'esit') return fark === 0;
            return true;
        });

        if (goruntulenecekler.length === 0) {
            if (sayimListesi.length === 0) {
                tbody.html(`
                    <tr class="empty-row" id="tableEmptyRow">
                        <td colspan="8" class="text-center py-5">
                            <div class="empty-state">
                                <i class="fas fa-dolly-flatbed fa-3x mb-3 text-muted"></i>
                                <h5>Sayım Listesi Boş</h5>
                                <p class="text-muted">Ürün eklemek için yukarıdaki alandan barkod okutun veya ürün adı arayın.</p>
                            </div>
                        </td>
                    </tr>
                `);
            } else {
                tbody.html(`
                    <tr class="empty-row">
                        <td colspan="8" class="text-center py-4 text-muted">
                            <i class="fas fa-filter me-2"></i>Bu filtreye uygun kayıt bulunamadı.
                        </td>
                    </tr>
                `);
            }
            return;
        }

        let html = '';
        goruntulenecekler.forEach((item, index) => {
            const fark = item.sayilan_miktar - item.stok_miktari;
            let farkBadge = '';
            if (fark < 0) {
                farkBadge = `<span class="badge-diff badge-diff-eksik"><i class="fas fa-arrow-down me-1"></i>${fark} (Eksik)</span>`;
            } else if (fark > 0) {
                farkBadge = `<span class="badge-diff badge-diff-fazla"><i class="fas fa-arrow-up me-1"></i>+${fark} (Fazla)</span>`;
            } else {
                farkBadge = `<span class="badge-diff badge-diff-esit"><i class="fas fa-check me-1"></i>0 (Eşit)</span>`;
            }

            const imgHtml = item.resim
                ? `<img src="${escapeHtml(item.resim)}" class="tbl-product-img" alt="">`
                : `<div class="tbl-product-img"><i class="fas fa-tag"></i></div>`;

            const isFlash = flashLineId && item.lineId === flashLineId;

            html += `
                <tr data-line-id="${item.lineId}" class="${isFlash ? 'row-flash' : ''}">
                    <td class="text-center text-muted fw-bold">${index + 1}</td>
                    <td>
                        <div class="tbl-product-cell">
                            ${imgHtml}
                            <div>
                                <div class="tbl-product-name">${escapeHtml(item.ad)}</div>
                                <div class="tbl-product-code">Kod: ${escapeHtml(item.kod || '—')} | ${escapeHtml(item.kategori || '')}</div>
                            </div>
                        </div>
                    </td>
                    <td class="text-center font-monospace">${escapeHtml(item.barkod || '—')}</td>
                    <td class="text-center">
                        <span class="badge bg-light text-dark border">${escapeHtml(item.renk)} / ${escapeHtml(item.beden)}</span>
                    </td>
                    <td class="text-end fw-bold text-secondary">${item.stok_miktari}</td>
                    <td class="text-center">
                        <div class="qty-stepper">
                            <button type="button" class="qty-btn btn-qty-minus" data-line-id="${item.lineId}">-</button>
                            <input type="number" min="0" class="qty-input input-row-qty" data-line-id="${item.lineId}" value="${item.sayilan_miktar}">
                            <button type="button" class="qty-btn btn-qty-plus" data-line-id="${item.lineId}">+</button>
                        </div>
                    </td>
                    <td class="text-center">${farkBadge}</td>
                    <td class="text-center">
                        <button type="button" class="btn-del-row" data-line-id="${item.lineId}" title="Listeden Kaldır">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </td>
                </tr>
            `;
        });

        tbody.html(html);
    }

    function guncelleOzetMetrikleri() {
        const toplamCesit = sayimListesi.length;
        let toplamSayilan = 0;
        let toplamSistem = 0;
        let eksikKalem = 0;
        let fazlaKalem = 0;
        let esitKalem = 0;
        let eksikAdetToplam = 0;
        let fazlaAdetToplam = 0;

        sayimListesi.forEach(item => {
            const sayilan = parseInt(item.sayilan_miktar, 10) || 0;
            const sistem = parseInt(item.stok_miktari, 10) || 0;
            const fark = sayilan - sistem;

            toplamSayilan += sayilan;
            toplamSistem += sistem;

            if (fark < 0) {
                eksikKalem += 1;
                eksikAdetToplam += Math.abs(fark);
            } else if (fark > 0) {
                fazlaKalem += 1;
                fazlaAdetToplam += fark;
            } else {
                esitKalem += 1;
            }
        });

        const netFark = toplamSayilan - toplamSistem;

        // KPI Metriklerini Doldur
        $('#kpiToplamCesit').text(toplamCesit);
        $('#kpiToplamSayilan').text(formatNumber(toplamSayilan));
        $('#kpiToplamSistem').text(formatNumber(toplamSistem));
        $('#kpiNetFark').text((netFark > 0 ? '+' : '') + formatNumber(netFark));
        if (netFark < 0) {
            $('#kpiNetFark').css('color', 'var(--sayim-danger)');
        } else if (netFark > 0) {
            $('#kpiNetFark').css('color', 'var(--sayim-success)');
        } else {
            $('#kpiNetFark').css('color', '#0f172a');
        }

        $('#kpiEksikKalem').text(`${eksikKalem} Çeşit`);
        $('#kpiEksikAdet').text(`-${formatNumber(eksikAdetToplam)} Adet`);

        $('#kpiFazlaKalem').text(`${fazlaKalem} Çeşit`);
        $('#kpiFazlaAdet').text(`+${formatNumber(fazlaAdetToplam)} Adet`);

        $('#kpiEsitKalem').text(`${esitKalem} Çeşit`);

        // Tablo başlık rozetleri
        $('#listRowCount').text(`${toplamCesit} Çeşit`);
        $('#listTotalQtyBadge').text(`${formatNumber(toplamSayilan)} Adet Sayıldı`);

        // Filtre Butonları Sayaçları
        $('#filterAllCount').text(toplamCesit);
        $('#filterEksikCount').text(eksikKalem);
        $('#filterFazlaCount').text(fazlaKalem);
        $('#filterEsitCount').text(esitKalem);
    }

    // =========================================================================
    // AJAX ARAMA İŞLEMLERİ (BARKOD SORGULA & ÜRÜN ARA)
    // =========================================================================

    function barkodSorgula(barkod) {
        if (!barkod) return;
        $('#barkodInput').prop('disabled', true);

        $.get('/urun/sayim/barkod-sorgula/', { barkod: barkod })
            .done(function (data) {
                if (data.success && data.urun) {
                    urunSayimaEkle(data.urun);
                    $('#barkodInput').val('');
                } else {
                    playBeepError();
                    showSearchFeedback('danger', data.message || 'Barkod bulunamadı!');
                    showToast('danger', data.message || 'Barkod bulunamadı!');
                    $('#barkodInput').select();
                }
            })
            .fail(function () {
                playBeepError();
                showSearchFeedback('danger', 'Sunucu ile iletişim kurulamadı!');
                showToast('danger', 'Barkod sorgulanırken sunucu hatası!');
            })
            .always(function () {
                $('#barkodInput').prop('disabled', false).focus();
            });
    }

    function urunAra(query) {
        const kriter = $('#urunAramaKriter').val() || 'hepsi';
        $.get('/urun/sayim/urun-ara/', { q: query, kriter: kriter })
            .done(function (data) {
                const container = $('#urunAramaSonuclari');
                if (data.success && data.urunler && data.urunler.length > 0) {
                    showSearchFeedback(null, '', 1);
                    let html = `
                        <div class="search-results-head">
                            <span class="search-results-head-title"><i class="fas fa-boxes"></i> Eşleşen Ürünler</span>
                            <span class="search-results-count">${data.urunler.length} kayıt</span>
                        </div>
                        <div class="search-results-scroll">
                    `;

                    data.urunler.forEach(function (u) {
                        const ad = escapeHtml(u.ad || '');
                        const kod = escapeHtml(u.kod || u.urun_kodu || '—');
                        const barkod = escapeHtml(u.barkod || '—');
                        const renk = escapeHtml(u.renk || 'Standart');
                        const beden = escapeHtml(u.beden || 'Tek Beden');
                        const stok = parseInt(u.stok_miktari, 10);
                        const stokStr = isFinite(stok) ? stok.toLocaleString('tr-TR') : '0';

                        html += `
                            <button type="button" class="result-item sayim-search-item" data-product='${JSON.stringify(u).replace(/'/g, '&#39;')}'>
                                <div class="result-item-gfx"><i class="fas fa-box"></i></div>
                                <div class="result-item-main">
                                    <div class="result-item-head">
                                        <h3 class="result-name">${ad}</h3>
                                        <span class="badge bg-secondary">Stok: ${stokStr}</span>
                                    </div>
                                    <div class="result-tags">
                                        <span class="result-tag result-tag-renk"><i class="fas fa-palette"></i> ${renk}</span>
                                        <span class="result-tag result-tag-beden"><i class="fas fa-ruler"></i> ${beden}</span>
                                    </div>
                                    <div class="result-foot">
                                        <span class="result-foot-item"><i class="fas fa-barcode"></i> ${barkod}</span>
                                        <span class="result-foot-item"><i class="fas fa-tag"></i> Kod: ${kod}</span>
                                    </div>
                                </div>
                                <div class="result-item-action"><i class="fas fa-plus-circle"></i></div>
                            </button>
                        `;
                    });

                    html += '</div>';
                    container.html(html).addClass('active');
                } else {
                    container.html(`
                        <div class="search-results-empty">
                            <i class="fas fa-magnifying-glass"></i>
                            <p>Eşleşen ürün bulunamadı</p>
                            <small>Farklı bir arama terimi deneyin.</small>
                        </div>
                    `).addClass('active');
                }
            })
            .fail(function () {
                showToast('danger', 'Arama sorgusunda hata!');
            });
    }

    // =========================================================================
    // EXCEL EXPORT (KAYDETMEDEN ÖNCE VEYA SONRA)
    // =========================================================================

    function excelExportEt() {
        if (sayimListesi.length === 0) {
            showToast('warning', 'Dışa aktarılacak sayım verisi bulunmuyor!');
            alert('Sayım listesi boş olduğu için Excel oluşturulamaz.');
            return;
        }

        const payload = {
            sayim_no: sayimNo || 'YENI_SAYIM',
            baslik: $('#sayimBaslikInput').val() || 'Stok Sayım Listesi',
            aciklama: $('#sayimAciklamaInput').val() || '',
            items: sayimListesi.map(it => ({
                varyant_id: it.varyant_id,
                ad: it.ad,
                barkod: it.barkod,
                kod: it.kod,
                renk: it.renk,
                beden: it.beden,
                kategori: it.kategori,
                stok_miktari: it.stok_miktari,
                sayilan_miktar: it.sayilan_miktar,
                pesin_fiyat: it.pesin_fiyat
            }))
        };

        const btn = $('#btnExcelExport');
        const origHtml = btn.html();
        btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Excel Hazırlanıyor...');

        fetch('/urun/sayim/excel-export/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) throw new Error('Excel üretilirken hata oluştu.');
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `stok_sayim_${sayimNo || 'liste'}_${new Date().toISOString().slice(0, 10)}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            showToast('success', 'Excel listesi başarıyla indirildi!');
        })
        .catch(err => {
            console.error(err);
            showToast('danger', 'Excel dosyası indirilemedi!');
        })
        .finally(() => {
            btn.prop('disabled', false).html(origHtml);
        });
    }

    // =========================================================================
    // TASLAK KAYDETME
    // =========================================================================

    function taslakKaydet() {
        if (sayimListesi.length === 0) {
            showToast('warning', 'Kaydedilecek ürün bulunmuyor!');
            return;
        }

        const btn = $('#btnTaslakKaydet');
        const origHtml = btn.html();
        btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Kaydediliyor...');

        const payload = {
            sayim_id: sayimId,
            sayim_no: sayimNo,
            baslik: $('#sayimBaslikInput').val(),
            aciklama: $('#sayimAciklamaInput').val(),
            items: sayimListesi.map(it => ({
                varyant_id: it.varyant_id,
                sayilan_miktar: it.sayilan_miktar
            }))
        };

        $.ajax({
            url: '/urun/sayim/taslak-kaydet/',
            type: 'POST',
            contentType: 'application/json',
            headers: { 'X-CSRFToken': csrfToken },
            data: JSON.stringify(payload),
            success: function (res) {
                if (res.success) {
                    sayimId = res.sayim_id;
                    $('#sayimId').val(sayimId);
                    showToast('success', res.message || 'Taslak kaydedildi!');
                    showSearchFeedback('success', 'Taslak başarıyla saklandı.');
                } else {
                    showToast('danger', res.message || 'Taslak kaydedilemedi!');
                }
            },
            error: function () {
                showToast('danger', 'Sunucu hatası oluştu!');
            },
            complete: function () {
                btn.prop('disabled', false).html(origHtml);
            }
        });
    }

    // =========================================================================
    // SAYIMI TAMAMLA VE STOKLARI EŞİTLEME (TRANSACTIONAL)
    // =========================================================================

    function sayimTamamlaModalAc() {
        if (sayimListesi.length === 0) {
            alert('Sayım listesinde hiç ürün yok. Lütfen en az bir ürün okutun.');
            return;
        }

        let eksikCesit = 0;
        let eksikAdet = 0;
        let fazlaCesit = 0;
        let fazlaAdet = 0;
        let esitCesit = 0;

        sayimListesi.forEach(it => {
            const fark = it.sayilan_miktar - it.stok_miktari;
            if (fark < 0) {
                eksikCesit++;
                eksikAdet += Math.abs(fark);
            } else if (fark > 0) {
                fazlaCesit++;
                fazlaAdet += fark;
            } else {
                esitCesit++;
            }
        });

        const listContainer = $('#modalOzetList');
        listContainer.html(`
            <li class="d-flex justify-content-between py-1 border-bottom">
                <span><i class="fas fa-boxes me-2"></i> Toplam Sayılan Kalem:</span>
                <strong>${sayimListesi.length} Çeşit</strong>
            </li>
            <li class="d-flex justify-content-between py-1 border-bottom text-danger">
                <span><i class="fas fa-minus-circle me-2"></i> Sayım Eksiği Fişi:</span>
                <strong>${eksikCesit} Çeşit (${eksikAdet} Adet Azaltılacak)</strong>
            </li>
            <li class="d-flex justify-content-between py-1 border-bottom text-success">
                <span><i class="fas fa-plus-circle me-2"></i> Sayım Fazlası Fişi:</span>
                <strong>${fazlaCesit} Çeşit (${fazlaAdet} Adet Artırılacak)</strong>
            </li>
            <li class="d-flex justify-content-between py-1 text-secondary">
                <span><i class="fas fa-check-circle me-2"></i> Stoğu Değişmeyecek:</span>
                <strong>${esitCesit} Çeşit</strong>
            </li>
        `);

        const modal = new bootstrap.Modal(document.getElementById('sayimOnayModal'));
        modal.show();
    }

    function sayimStoklariEsitle() {
        const btn = $('#btnModalOnaylaVeEsitle');
        const origHtml = btn.html();
        btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin me-2"></i> Stoklar Eşitleniyor...');

        const payload = {
            sayim_id: sayimId,
            sayim_no: sayimNo,
            baslik: $('#sayimBaslikInput').val(),
            aciklama: $('#sayimAciklamaInput').val(),
            items: sayimListesi.map(it => ({
                varyant_id: it.varyant_id,
                sayilan_miktar: it.sayilan_miktar
            }))
        };

        $.ajax({
            url: '/urun/sayim/kaydet/',
            type: 'POST',
            contentType: 'application/json',
            headers: { 'X-CSRFToken': csrfToken },
            data: JSON.stringify(payload),
            success: function (res) {
                if (res.success) {
                    playBeepChime();
                    const modalEl = document.getElementById('sayimOnayModal');
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();

                    alert(`Tebrikler!\n\nSayım #${res.sayim_no} başarıyla tamamlandı.\nStok hareketleri oluşturuldu ve tüm ürün stokları eşitlendi.`);
                    window.location.href = `/urun/sayim/${res.sayim_id}/detay/`;
                } else {
                    alert('Hata: ' + (res.message || 'Sayım kaydedilemedi!'));
                    btn.prop('disabled', false).html(origHtml);
                }
            },
            error: function (xhr) {
                const msg = xhr.responseJSON ? xhr.responseJSON.message : 'Sunucu işlemi tamamlayamadı!';
                alert('İşlem başarısız: ' + msg);
                btn.prop('disabled', false).html(origHtml);
            }
        });
    }

    // =========================================================================
    // KAMERA İLE BARKOD OKUMA (ZXING)
    // =========================================================================

    function startScannerCamera() {
        if (!window.ZXing) {
            alert('Barkod tarayıcı kütüphanesi yüklenemedi.');
            return;
        }

        const modal = new bootstrap.Modal(document.getElementById('sayimKameraModal'));
        modal.show();

        codeReader = new ZXing.BrowserMultiFormatReader();
        scanningActive = true;

        codeReader.listVideoInputDevices()
            .then(videoInputDevices => {
                if (videoInputDevices.length === 0) {
                    alert('Kamera bulunamadı!');
                    modal.hide();
                    return;
                }
                const selectedDeviceId = videoInputDevices[videoInputDevices.length - 1].deviceId; // Arka kamera tercih edilir
                codeReader.decodeFromVideoDevice(selectedDeviceId, 'sayimScannerVideo', (result, err) => {
                    if (result && scanningActive) {
                        scanningActive = false;
                        modal.hide();
                        stopScannerCamera();
                        barkodSorgula(result.text);
                    }
                });
            })
            .catch(err => {
                console.error(err);
                alert('Kamera başlatılamadı: ' + err.message);
                modal.hide();
            });
    }

    function stopScannerCamera() {
        scanningActive = false;
        if (codeReader) {
            codeReader.reset();
            codeReader = null;
        }
    }

    // =========================================================================
    // EVENT LISTENERS VE BAŞLANGIÇ
    // =========================================================================

    function setupEventListeners() {
        // Tab Geçişleri
        $('.search-tab').on('click', function () {
            $('.search-tab').removeClass('active');
            $(this).addClass('active');
            const tab = $(this).data('tab');
            if (tab === 'barcode') {
                $('#barcodeField').show();
                $('#productField').hide();
                $('#barkodInput').focus();
            } else {
                $('#barcodeField').hide();
                $('#productField').show();
                $('#urunAramaInput').focus();
            }
        });

        // Barkod Input Enter
        $('#barkodInput').on('keypress', function (e) {
            if (e.which === 13) {
                const b = $(this).val().trim();
                if (b) {
                    barkodSorgula(b);
                }
            }
        });

        // Manuel Ürün Arama Input (Debounced)
        $('#urunAramaInput').on('input', function () {
            const q = $(this).val().trim();
            if (urunAraDebounce) clearTimeout(urunAraDebounce);
            if (q.length >= 1) {
                urunAraDebounce = setTimeout(() => urunAra(q), 180);
            } else {
                $('#urunAramaSonuclari').removeClass('active');
            }
        });

        $('#urunAramaKriter').on('change', function () {
            const q = ($('#urunAramaInput').val() || '').trim();
            if (q.length >= 1) urunAra(q);
        });

        // Arama Sonucu Tıklama
        $(document).on('click', '.sayim-search-item', function () {
            const u = JSON.parse($(this).attr('data-product'));
            urunSayimaEkle(u);
            $('#urunAramaSonuclari').removeClass('active');
            $('#urunAramaInput').val('');
        });

        // Dış tıkla arama sonuçlarını kapat
        $(document).on('click', function (e) {
            if (!$(e.target).closest('#urunAramaInput, #urunAramaSonuclari').length) {
                $('#urunAramaSonuclari').removeClass('active');
            }
        });

        // Klavye Kısayolları (F2: Barkod, F3: Ürün Ara)
        $(document).on('keydown', function (e) {
            if (e.key === 'F2') {
                e.preventDefault();
                $('#tabBarcodeBtn').trigger('click');
            } else if (e.key === 'F3') {
                e.preventDefault();
                $('#tabSearchBtn').trigger('click');
            }
        });

        // Miktar Artırma/Azaltma
        $(document).on('click', '.btn-qty-plus', function () {
            const lineId = parseInt($(this).data('line-id'), 10);
            const item = sayimListesi.find(x => x.lineId === lineId);
            if (item) {
                item.sayilan_miktar += 1;
                item.son_okunma_zamani = new Date();
                guncelleSonOkutulanBes(item);
                renderSayimTable();
                guncelleOzetMetrikleri();
                playBeepIncrement();
            }
        });

        $(document).on('click', '.btn-qty-minus', function () {
            const lineId = parseInt($(this).data('line-id'), 10);
            const item = sayimListesi.find(x => x.lineId === lineId);
            if (item && item.sayilan_miktar > 0) {
                item.sayilan_miktar -= 1;
                renderSayimTable();
                guncelleOzetMetrikleri();
            }
        });

        $(document).on('change', '.input-row-qty', function () {
            const lineId = parseInt($(this).data('line-id'), 10);
            let val = parseInt($(this).val(), 10);
            if (isNaN(val) || val < 0) val = 0;
            const item = sayimListesi.find(x => x.lineId === lineId);
            if (item) {
                item.sayilan_miktar = val;
                renderSayimTable();
                guncelleOzetMetrikleri();
            }
        });

        // Satır Silme
        $(document).on('click', '.btn-del-row', function () {
            const lineId = parseInt($(this).data('line-id'), 10);
            const item = sayimListesi.find(x => x.lineId === lineId);
            if (item) {
                if (confirm(`"${item.ad}" ürününü sayım listesinden silmek istediğinize emin misiniz?`)) {
                    sayimListesi = sayimListesi.filter(x => x.lineId !== lineId);
                    sonOkutulanBes = sonOkutulanBes.filter(x => x.lineId !== lineId);
                    renderSonOkutulanBes();
                    renderSayimTable();
                    guncelleOzetMetrikleri();
                    showToast('info', 'Ürün listeden çıkarıldı.');
                }
            }
        });

        // Filtre Butonları
        $('.filter-btn').on('click', function () {
            $('.filter-btn').removeClass('active');
            $(this).addClass('active');
            aktifFiltre = $(this).data('filter');
            renderSayimTable();
        });

        // Listeyi Temizle Butonu
        $('#listeyiTemizleBtn').on('click', function () {
            if (sayimListesi.length === 0) return;
            if (confirm('Tüm sayım listesini temizlemek istediğinize emin misiniz?')) {
                sayimListesi = [];
                sonOkutulanBes = [];
                renderSonOkutulanBes();
                renderSayimTable();
                guncelleOzetMetrikleri();
                showToast('info', 'Sayım listesi temizlendi.');
            }
        });

        // Aksiyon Butonları
        $('#btnExcelExport').on('click', excelExportEt);
        $('#btnTaslakKaydet').on('click', taslakKaydet);
        $('#btnSayimTamamla').on('click', sayimTamamlaModalAc);
        $('#btnModalOnaylaVeEsitle').on('click', sayimStoklariEsitle);

        // Kamera
        $('#sayimKameraBtn').on('click', startScannerCamera);
        $('#sayimKameraModal').on('hidden.bs.modal', stopScannerCamera);

        // Son Okutulan Kart Tıklanırsa Tabloda Parıldasın
        $(document).on('click', '.recent-card', function () {
            const lineId = parseInt($(this).data('line-id'), 10);
            renderSayimTable(lineId);
            const row = $(`tr[data-line-id="${lineId}"]`);
            if (row.length) {
                $('#sayimTableWrapper').scrollTop(row.position().top);
            }
        });
    }

    // =========================================================================
    // BAŞLATMA
    // =========================================================================
    $(document).ready(function () {
        setupEventListeners();
        updateClock();
        setInterval(updateClock, 1000);

        // Varsa önceden yüklenmiş taslak verileri aktar
        if (_cfg.initialItems && Array.isArray(_cfg.initialItems) && _cfg.initialItems.length > 0) {
            _cfg.initialItems.forEach(it => {
                const item = {
                    lineId: ++sayimSonLineId,
                    id: it.id,
                    varyant_id: it.varyant_id,
                    ad: it.ad,
                    varyasyon: it.varyasyon,
                    beden: it.beden,
                    renk: it.renk,
                    barkod: it.barkod,
                    kod: it.kod,
                    kategori: it.kategori,
                    stok_miktari: it.stok_miktari,
                    sayilan_miktar: it.sayilan_miktar,
                    pesin_fiyat: it.pesin_fiyat,
                    resim: it.resim || null,
                    son_okunma_zamani: new Date()
                };
                sayimListesi.push(item);
            });

            // Son 5 tanesini göster
            sonOkutulanBes = sayimListesi.slice(0, 5);
            renderSonOkutulanBes();
            renderSayimTable();
            guncelleOzetMetrikleri();
        }

        $('#barkodInput').focus();
    });

})(jQuery);
