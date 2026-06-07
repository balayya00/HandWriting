/* ─── HandwriterPro App ─── */
(function () {
  'use strict';

  // ── State ──────────────────────────────────
  const state = {
    currentFile: null,
    extractedText: '',
    pages: [],
    currentPage: 0,
    isEditing: false,
    settings: {
      style: 'style1',
      fontSize: 32,
      lineSpacing: 60,
      inkColor: 'blue',
      paperStyle: 'ruled',
      margin: 80,
    }
  };

  // ── DOM Refs ───────────────────────────────
  const $ = (id) => document.getElementById(id);
  const $$ = (sel) => document.querySelectorAll(sel);

  const elems = {
    // Tabs
    tabBtns: $$('.tab-btn'),
    tabUpload: $('tab-upload'),
    tabText: $('tab-text'),
    // Dropzone
    dropzone: $('dropzone'),
    fileInput: $('file-input'),
    fileInfo: $('file-info'),
    fileName: $('file-name'),
    fileSize: $('file-size'),
    fileTypeIcon: $('file-type-icon'),
    removeFile: $('remove-file'),
    extractRow: $('extract-row'),
    extractBtn: $('extract-btn'),
    // Text
    textInput: $('text-input'),
    charCount: $('char-count'),
    clearText: $('clear-text'),
    sampleText: $('sample-text'),
    // Extracted
    extractedSection: $('extracted-section'),
    extractedPreview: $('extracted-preview'),
    extractedText: $('extracted-text'),
    editExtracted: $('edit-extracted'),
    // Settings
    fontPicker: $('font-picker'),
    fontOpts: $$('.font-option'),
    colorBtns: $$('.color-btn'),
    paperOpts: $$('.paper-option input'),
    fontSizeSlider: $('font-size'),
    fontSizeVal: $('font-size-val'),
    lineSpacingSlider: $('line-spacing'),
    lineSpacingVal: $('line-spacing-val'),
    marginSlider: $('margin'),
    marginVal: $('margin-val'),
    // Generate
    generateBtn: $('generate-btn'),
    progressSection: $('progress-section'),
    progressBar: $('progress-bar'),
    progressLabel: $('progress-label'),
    errorAlert: $('error-alert'),
    errorMsg: $('error-message'),
    successAlert: $('success-alert'),
    successMsg: $('success-message'),
    // Preview
    previewCard: $('preview-card'),
    previewImage: $('preview-image'),
    previewNav: $('preview-nav'),
    prevPage: $('prev-page'),
    nextPage: $('next-page'),
    pageIndicator: $('page-indicator'),
    pageCountBadge: $('page-count-badge'),
    // Download
    downloadPdf: $('download-pdf'),
    downloadJpg: $('download-jpg'),
    downloadSpinner: $('download-spinner'),
    jpgBadge: $('jpg-badge'),
    // Toast
    toastContainer: $('toast-container'),
  };

  // ── Sample Text ────────────────────────────
  const SAMPLE_TEXT = `The quick brown fox jumps over the lazy dog.

Dear Friend,

I hope this letter finds you in good health and high spirits. I am writing to share some exciting news with you — I have recently started exploring the art of handwriting, and it has brought me immense joy.

There is something truly magical about putting pen to paper. Each letter carries a piece of one's personality, and no two handwriting styles are quite alike. I find it to be a wonderful way to slow down and be mindful in our otherwise fast-paced digital world.

Mathematics Notes:
- The Pythagorean theorem: a² + b² = c²
- Area of a circle: A = πr²
- Quadratic formula: x = (-b ± √(b²-4ac)) / 2a

Please write back when you get a chance. I would love to hear your thoughts.

Warm regards,
Your Friend`;

  // ── Tab Handling ───────────────────────────
  elems.tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      elems.tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
      document.getElementById(`tab-${tab}`).classList.add('active');
    });
  });

  // ── Drag & Drop ────────────────────────────
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(ev => {
    elems.dropzone.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); });
    document.body.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); });
  });

  ['dragenter', 'dragover'].forEach(ev => {
    elems.dropzone.addEventListener(ev, () => elems.dropzone.classList.add('drag-over'));
  });

  ['dragleave', 'drop'].forEach(ev => {
    elems.dropzone.addEventListener(ev, () => elems.dropzone.classList.remove('drag-over'));
  });

  elems.dropzone.addEventListener('drop', e => {
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFile(file);
  });

  elems.dropzone.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      elems.fileInput.click();
    }
  });

  elems.dropzone.addEventListener('click', () => elems.fileInput.click());
  elems.fileInput.addEventListener('change', e => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  });

  function handleFile(file) {
    const allowed = [
      'application/pdf',
      'image/jpeg', 'image/jpg', 'image/png',
      'image/bmp', 'image/tiff', 'image/webp'
    ];
    const ext = file.name.toLowerCase().split('.').pop();
    const allowedExts = ['pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp'];

    if (!allowed.includes(file.type) && !allowedExts.includes(ext)) {
      showToast('Unsupported file type. Please use PDF, JPG, or PNG.', 'error');
      return;
    }

    if (file.size > 16 * 1024 * 1024) {
      showToast('File too large. Maximum size is 16MB.', 'error');
      return;
    }

    state.currentFile = file;
    const icon = file.type === 'application/pdf' ? '📄' :
      file.type.startsWith('image/') ? '🖼️' : '📁';

    elems.fileTypeIcon.textContent = icon;
    elems.fileName.textContent = file.name;
    elems.fileSize.textContent = formatBytes(file.size);
    elems.fileInfo.hidden = false;
    elems.extractRow.hidden = false;

    // Clear previous extraction
    state.extractedText = '';
    elems.extractedSection.hidden = true;

    showToast(`File loaded: ${file.name}`, 'success');
  }

  elems.removeFile.addEventListener('click', () => {
    state.currentFile = null;
    elems.fileInput.value = '';
    elems.fileInfo.hidden = true;
    elems.extractRow.hidden = true;
    elems.extractedSection.hidden = true;
    state.extractedText = '';
  });

  // ── Extract Text ───────────────────────────
  elems.extractBtn.addEventListener('click', async () => {
    if (!state.currentFile) return;

    setButtonLoading(elems.extractBtn, true);
    showProgress('Extracting text from file...', 30);

    try {
      const formData = new FormData();
      formData.append('file', state.currentFile);

      const res = await fetch('/api/extract', {
        method: 'POST',
        body: formData
      });

      const data = await res.json();
      setProgress(90);

      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Extraction failed');
      }

      state.extractedText = data.text;
      showExtractedText(data.text);
      hideProgress();
      showToast('Text extracted successfully!', 'success');

    } catch (err) {
      hideProgress();
      showError(err.message);
    } finally {
      setButtonLoading(elems.extractBtn, false);
    }
  });

  function showExtractedText(text) {
    elems.extractedPreview.textContent = text;
    elems.extractedText.value = text;
    elems.extractedSection.hidden = false;
  }

  // ── Edit Extracted Text ────────────────────
  elems.editExtracted.addEventListener('click', () => {
    state.isEditing = !state.isEditing;
    elems.extractedPreview.hidden = state.isEditing;
    elems.extractedText.hidden = !state.isEditing;
    elems.editExtracted.textContent = state.isEditing ? 'Done' : 'Edit';

    if (!state.isEditing) {
      state.extractedText = elems.extractedText.value;
      elems.extractedPreview.textContent = state.extractedText;
    }
  });

  // ── Text Input ─────────────────────────────
  elems.textInput.addEventListener('input', () => {
    const len = elems.textInput.value.length;
    elems.charCount.textContent = `${len.toLocaleString()} characters`;
  });

  elems.clearText.addEventListener('click', () => {
    elems.textInput.value = '';
    elems.charCount.textContent = '0 characters';
  });

  elems.sampleText.addEventListener('click', () => {
    elems.textInput.value = SAMPLE_TEXT;
    elems.charCount.textContent = `${SAMPLE_TEXT.length.toLocaleString()} characters`;
    showToast('Sample text loaded!', 'info');
  });

  // ── Settings: Font ─────────────────────────
  elems.fontOpts.forEach(opt => {
    opt.addEventListener('click', () => {
      elems.fontOpts.forEach(o => o.classList.remove('active'));
      opt.classList.add('active');
      state.settings.style = opt.dataset.style;
    });
  });

  // ── Settings: Paper ────────────────────────
  elems.paperOpts.forEach(radio => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('.paper-option').forEach(p => p.classList.remove('active'));
      radio.closest('.paper-option').classList.add('active');
      state.settings.paperStyle = radio.value;
    });
  });

  // ── Settings: Color ────────────────────────
  elems.colorBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      elems.colorBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.settings.inkColor = btn.dataset.color;
    });
  });

  // ── Settings: Sliders ─────────────────────
  elems.fontSizeSlider.addEventListener('input', e => {
    const v = e.target.value;
    elems.fontSizeVal.textContent = `${v}px`;
    state.settings.fontSize = Number(v);
  });

  elems.lineSpacingSlider.addEventListener('input', e => {
    const v = e.target.value;
    elems.lineSpacingVal.textContent = `${v}px`;
    state.settings.lineSpacing = Number(v);
  });

  elems.marginSlider.addEventListener('input', e => {
    const v = e.target.value;
    elems.marginVal.textContent = `${v}px`;
    state.settings.margin = Number(v);
  });

  // ── Get Active Text ────────────────────────
  function getActiveText() {
    const activeTab = document.querySelector('.tab-btn.active')?.dataset.tab;

    if (activeTab === 'upload') {
      const edited = state.isEditing ? elems.extractedText.value : state.extractedText;
      return edited || state.extractedText;
    } else {
      return elems.textInput.value;
    }
  }

  // ── Generate Handwriting ───────────────────
  elems.generateBtn.addEventListener('click', async () => {
    const text = getActiveText().trim();

    if (!text) {
      showError('Please enter some text or extract from a file first.');
      showToast('No text to convert!', 'error');
      return;
    }

    hideError();
    hideSuccess();
    setButtonLoading(elems.generateBtn, true);
    showProgress('Downloading fonts...', 15);

    try {
      setProgress(25, 'Generating handwriting...');

      const payload = {
        text,
        ...state.settings
      };

      const res = await fetch('/api/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      setProgress(80, 'Rendering pages...');

      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Conversion failed');
      }

      setProgress(100, 'Done!');
      state.pages = data.pages;
      state.currentPage = 0;

      setTimeout(() => {
        hideProgress();
        renderPreview();
        showSuccess(`Generated ${data.total_pages} page(s) successfully!`);
        showToast(`✅ ${data.total_pages} page(s) ready!`, 'success');
        elems.previewCard.hidden = false;
        elems.previewCard.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // Update JPG badge
        if (data.total_pages > 1) {
          elems.jpgBadge.textContent = `${data.total_pages} Images (ZIP)`;
        } else {
          elems.jpgBadge.textContent = '1 Image';
        }
      }, 500);

    } catch (err) {
      hideProgress();
      showError(err.message);
      showToast(err.message, 'error');
    } finally {
      setButtonLoading(elems.generateBtn, false);
    }
  });

  // ── Preview ────────────────────────────────
  function renderPreview() {
    if (!state.pages.length) return;

    const page = state.pages[state.currentPage];
    elems.previewImage.src = page.data;
    elems.previewImage.alt = `Page ${page.page} preview`;

    elems.pageIndicator.textContent = `${state.currentPage + 1} / ${state.pages.length}`;
    elems.pageCountBadge.textContent = `${state.pages.length} page${state.pages.length > 1 ? 's' : ''}`;

    elems.prevPage.disabled = state.currentPage === 0;
    elems.nextPage.disabled = state.currentPage === state.pages.length - 1;

    elems.previewNav.hidden = state.pages.length <= 1;
  }

  elems.prevPage.addEventListener('click', () => {
    if (state.currentPage > 0) {
      state.currentPage--;
      renderPreview();
    }
  });

  elems.nextPage.addEventListener('click', () => {
    if (state.currentPage < state.pages.length - 1) {
      state.currentPage++;
      renderPreview();
    }
  });

  // ── Downloads ──────────────────────────────
  elems.downloadPdf.addEventListener('click', () => downloadFile('pdf'));
  elems.downloadJpg.addEventListener('click', () => downloadFile('jpg'));

  async function downloadFile(format) {
    const text = getActiveText().trim();
    if (!text) {
      showToast('No text to download!', 'error');
      return;
    }

    elems.downloadSpinner.hidden = false;
    elems.downloadPdf.disabled = true;
    elems.downloadJpg.disabled = true;

    try {
      const payload = {
        text,
        format,
        ...state.settings
      };

      const res = await fetch('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Download failed');
      }

      const blob = await res.blob();
      const contentDisposition = res.headers.get('Content-Disposition') || '';
      const filenameMatch = contentDisposition.match(/filename="(.+?)"/);
      const filename = filenameMatch ? filenameMatch[1] : `handwritten_notes.${format}`;

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      showToast(`Downloaded ${filename}!`, 'success');

    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      elems.downloadSpinner.hidden = true;
      elems.downloadPdf.disabled = false;
      elems.downloadJpg.disabled = false;
    }
  }

  // ── Progress Helpers ───────────────────────
  function showProgress(label, pct) {
    elems.progressSection.hidden = false;
    setProgress(pct, label);
  }

  function setProgress(pct, label) {
    elems.progressBar.style.width = `${pct}%`;
    if (label) elems.progressLabel.textContent = label;
  }

  function hideProgress() {
    elems.progressSection.hidden = true;
    elems.progressBar.style.width = '0%';
  }

  // ── Alert Helpers ──────────────────────────
  function showError(msg) {
    elems.errorMsg.textContent = msg;
    elems.errorAlert.hidden = false;
    elems.successAlert.hidden = true;
  }

  function hideError() {
    elems.errorAlert.hidden = true;
  }

  function showSuccess(msg) {
    elems.successMsg.textContent = msg;
    elems.successAlert.hidden = false;
    elems.errorAlert.hidden = true;
  }

  function hideSuccess() {
    elems.successAlert.hidden = true;
  }

  // ── Button Loading ─────────────────────────
  function setButtonLoading(btn, loading) {
    btn.disabled = loading;
    if (loading) btn.classList.add('loading');
    else btn.classList.remove('loading');
  }

  // ── Toast ──────────────────────────────────
  function showToast(message, type = 'info', duration = 4000) {
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;
    elems.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'slideOut 0.3s ease forwards';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  // ── Utils ──────────────────────────────────
  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  // ── Init ───────────────────────────────────
  function init() {
    // Check paper option visual state
    document.querySelectorAll('.paper-option').forEach(opt => {
      opt.addEventListener('click', () => {
        document.querySelectorAll('.paper-option').forEach(p => p.classList.remove('active'));
        opt.classList.add('active');
      });
    });

    // Set initial state
    document.querySelector('.paper-option[data-paper="ruled"]')?.classList.add('active');

    // Health check
    fetch('/api/health')
      .then(r => r.json())
      .then(data => {
        if (!data.tesseract) {
          console.info('Tesseract OCR not available - image OCR will be limited');
        }
      })
      .catch(() => {});

    showToast('Welcome to HandwriterPro! 🎉', 'info', 3000);
  }

  init();
})();
