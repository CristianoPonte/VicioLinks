const API_BASE = '';

// State Management
let products = [];
let turmas = [];
let launchTypes = [];
let sourceConfigs = [];
let currentLinks = [];
let filteredLinks = []; // Store current filtered state for export
let currentMode = 'captacao'; // 'captacao' or 'vendas'

// State for Admin Cascading
let adminSelectedSource = null;
let adminSelectedMedium = null;
let editingMode = {
    active: false,
    type: null,
    oldSlug: null,
    parentSource: null,   // for mediums/contents
    parentMedium: null    // for contents
};

// Auth State
let currentUser = null;
let authToken = localStorage.getItem('authToken');

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
    console.log('App DOMContentLoaded. Initializing...');

    // Check Auth first
    if (!authToken) {
        showLoginScreen();
    } else {
        await verifyTokenAndInit();
    }

    setupEventListeners();
    setupAuthListeners();
});

async function verifyTokenAndInit() {
    try {
        const res = await authFetch(`${API_BASE}/users/me`);
        if (res.ok) {
            currentUser = await res.json();
            document.getElementById('user-name').innerText = currentUser.username;
            updateUIForRole(currentUser.role);
            hideLoginScreen();
            await initApp();
        } else {
            handleLogout();
        }
    } catch (err) {
        console.error("Auth check failed", err);
        handleLogout();
    }
}

function updateUIForRole(role) {
    const navGenerate = document.getElementById('nav-generate');
    const navAdmin = document.getElementById('nav-admin');
    const navUsers = document.getElementById('nav-users');

    // Reset visibility
    if (navGenerate) navGenerate.parentElement.style.display = 'block';
    if (navAdmin) navAdmin.parentElement.style.display = 'block';
    if (navUsers) navUsers.classList.add('hidden');

    if (role === 'admin') {
        if (navUsers) navUsers.classList.remove('hidden');
    } else if (role === 'viewer') {
        if (navGenerate) navGenerate.parentElement.style.display = 'none';
        if (navAdmin) navAdmin.parentElement.style.display = 'none';
        showScreen('list');
    } else if (role === 'user') {
        if (navAdmin) navAdmin.parentElement.style.display = 'none';
        // If on admin screen, move to generate
        if (!document.getElementById('screen-admin').classList.contains('hidden')) {
            showScreen('generate');
        }
    }
}

async function authFetch(url, options = {}) {
    const headers = options.headers || {};
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    const newOptions = { ...options, headers };
    const res = await fetch(url, newOptions);
    if (res.status === 401) {
        handleLogout();
    }
    return res;
}

function showLoginScreen() {
    const overlay = document.getElementById('login-overlay');
    const app = document.getElementById('app-container');
    if (overlay) overlay.classList.remove('hidden');
    if (app) app.classList.add('hidden');
}

function hideLoginScreen() {
    const overlay = document.getElementById('login-overlay');
    const app = document.getElementById('app-container');
    if (overlay) overlay.classList.add('hidden');
    if (app) app.classList.remove('hidden');
}

function handleLogout() {
    localStorage.removeItem('authToken');
    authToken = null;
    currentUser = null;
    showLoginScreen();
}

function setupAuthListeners() {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('login-username').value;
            const password = document.getElementById('login-password').value;
            const btn = loginForm.querySelector('button');

            try {
                btn.disabled = true;
                btn.innerText = 'Autenticando...';

                const formData = new URLSearchParams();
                formData.append('username', username);
                formData.append('password', password);

                const res = await fetch(`${API_BASE}/token`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: formData
                });

                if (res.ok) {
                    const data = await res.json();
                    authToken = data.access_token;
                    localStorage.setItem('authToken', authToken);
                    await verifyTokenAndInit();
                } else {
                    alert('Usuário ou senha incorretos.');
                }
            } catch (err) {
                console.error(err);
                alert('Erro na conexão com o servidor.');
            } finally {
                btn.disabled = false;
                btn.innerText = 'Entrar no Sistema';
            }
        });
    }

    // Logout on clicking avatar or name specifically
    const avatar = document.querySelector('.avatar');
    const userName = document.getElementById('user-name');

    [avatar, userName].forEach(el => {
        if (el) {
            el.style.cursor = 'pointer';
            el.title = 'Clique para Sair';
            el.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent bubbling just in case
                if (confirm('Deseja sair do sistema?')) {
                    handleLogout();
                }
            });
        }
    });
}

async function initApp() {
    try {
        console.log('Starting initApp fetches...');
        await Promise.all([
            fetchProducts(),
            fetchTurmas(),
            fetchLaunchTypes(),
            fetchSourceConfigs(),
            fetchLaunches(),
            fetchLinks()
        ]);
        console.log('initApp completed successfully.');
        updateMediums('instagram');
    } catch (err) {
        console.error('Failed to initialize app:', err);
    }
}

function setupEventListeners() {
    console.log('Setting up event listeners...');

    const addListener = (id, event, fn) => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener(event, fn);
        } else {
            console.warn(`Element with ID "${id}" not found.`);
        }
    };

    // Navigation
    addListener('nav-generate', 'click', (e) => { e.preventDefault(); showScreen('generate'); });
    addListener('nav-list', 'click', (e) => { e.preventDefault(); showScreen('list'); fetchLinks(); });
    addListener('nav-admin', 'click', (e) => { e.preventDefault(); showScreen('admin'); renderAdminLists(); });

    // Mode Toggle
    document.querySelectorAll('.mode-toggle:not(.admin-tabs) .mode-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            setMode(e.target.dataset.mode);
        });
    });

    // Admin Tab Toggle
    document.querySelectorAll('.admin-tabs .mode-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            setAdminTab(e.target.dataset.adminTab);
        });
    });

    // Campaign Generator Listeners
    ['gen-product', 'gen-turma', 'gen-type', 'gen-month', 'gen-year'].forEach(id => {
        addListener(id, 'change', updateCampaignPreview);
    });

    // Button Save Campaign
    addListener('btn-save-campaign', 'click', saveGeneratedCampaign);
    addListener('btn-copy', 'click', () => {
        const finalUrl = document.getElementById('final-url');
        if (finalUrl && finalUrl.innerText) copyToClipboard(finalUrl.innerText);
    });

    // Link Generation Flow
    addListener('channel', 'change', (e) => {
        const sourceSlug = e.target.value;
        updateMediums(sourceSlug);
        updateDynamicFields(sourceSlug);
        // Update contents based on Source now
        updateContents(sourceSlug);
    });

    // Medium change does NOT affect contents anymore
    // addListener('subtype', 'change', (e) => { ... });

    // --- Repository Filters ---
    addListener('search-links', 'input', applyFilters);
    addListener('filter-campaign', 'change', applyFilters);
    addListener('filter-source', 'change', (e) => {
        const sourceSlug = e.target.value;
        const source = sourceConfigs.find(s => s.slug === sourceSlug);
        populateSelect('filter-medium', source ? (source.config?.mediums || []) : []);
        // Populate contents directly from Source
        populateSelect('filter-content', source ? (source.config?.contents || []) : []);

        const mediumSelect = document.getElementById('filter-medium');
        if (mediumSelect) {
            mediumSelect.disabled = !source;
            mediumSelect.value = "";
        }
        applyFilters();
    });
    addListener('filter-medium', 'change', applyFilters); // Just apply filters, don't update contents
    addListener('filter-content', 'change', applyFilters);
    addListener('filter-term', 'input', applyFilters);

    addListener('btn-toggle-advanced', 'click', () => {
        const adv = document.getElementById('advanced-filters');
        if (adv) adv.classList.toggle('hidden');
    });

    addListener('btn-export', 'click', exportToCSV);

    // --- Admin Cascading Listeners ---
    addListener('admin-medium-source-filter', 'change', (e) => {
        adminSelectedSource = e.target.value;
        renderMediumsTab();
    });

    addListener('admin-content-source-filter', 'change', (e) => {
        const sourceSlug = e.target.value;
        const source = sourceConfigs.find(s => s.slug === sourceSlug);
        adminSelectedSource = sourceSlug;
        // adminSelectedMedium = null; // No longer needed
        renderContentsTab();
    });

    // Validating if we need to remove specific medium listener for admin content? 
    // Yes, it was removed from HTML, so listener is moot, but code cleanup is good.
    // Removed: addListener('admin-content-medium-filter', ...);

    // Form Submissions
    addListener('link-form', 'submit', handleGenerateLink);
    addListener('admin-source-form-new', 'submit', handleAdminSourceSubmit);
    addListener('admin-medium-form-new', 'submit', handleAdminMediumSubmit);
    addListener('admin-content-form-new', 'submit', handleAdminContentSubmit);

    // Simple Admin Forms
    addListener('admin-product-form', 'submit', (e) => handleAdminSimpleSubmit(e, 'products', fetchProducts));
    addListener('admin-turma-form', 'submit', (e) => handleAdminSimpleSubmit(e, 'turmas', fetchTurmas));
    addListener('admin-launchtype-form', 'submit', (e) => handleAdminSimpleSubmit(e, 'launch-types', fetchLaunchTypes));

    console.log('Event listeners setup complete.');
}

function showScreen(screen) {
    const screenElements = {
        generate: document.getElementById('screen-generate'),
        list: document.getElementById('screen-list'),
        admin: document.getElementById('screen-admin'),
        users: document.getElementById('screen-users')
    };
    const nLinks = {
        generate: document.getElementById('nav-generate'),
        list: document.getElementById('nav-list'),
        admin: document.getElementById('nav-admin')
    };

    Object.keys(screenElements).forEach(key => {
        if (screenElements[key]) screenElements[key].classList.toggle('hidden', key !== screen);
    });
    Object.keys(nLinks).forEach(key => {
        if (nLinks[key]) nLinks[key].classList.toggle('active', key === screen);
    });
}

function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    const submitBtn = document.querySelector('#btn-generate span');
    if (submitBtn) {
        submitBtn.innerText = mode === 'captacao' ? 'Gerar Link de Captação' : 'Gerar Link de Vendas';
    }
}

function setAdminTab(tab) {
    document.querySelectorAll('.admin-tabs .mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.adminTab === tab);
    });

    document.querySelectorAll('.admin-tab-content').forEach(content => {
        content.classList.toggle('hidden', content.id !== `admin-tab-${tab}`);
    });

    renderAdminLists();
}

// Fetch Functions
async function fetchProducts() {
    const res = await authFetch(`${API_BASE}/products`);
    products = await res.json();
    populateSelect('gen-product', products);
}

async function fetchTurmas() {
    const res = await authFetch(`${API_BASE}/turmas`);
    turmas = await res.json();
    populateSelect('gen-turma', turmas);
}

async function fetchLaunchTypes() {
    const res = await authFetch(`${API_BASE}/launch-types`);
    launchTypes = await res.json();
    populateSelect('gen-type', launchTypes);
}

async function fetchSourceConfigs() {
    const res = await authFetch(`${API_BASE}/source-configs`);
    sourceConfigs = await res.json();

    populateSelect('channel', sourceConfigs.map(s => ({ slug: s.slug, nome: s.name })));
    populateSelect('filter-source', sourceConfigs.map(s => ({ slug: s.slug, nome: s.name })));

    populateSelect('admin-medium-source-filter', sourceConfigs.map(s => ({ slug: s.slug, nome: s.name })));
    populateSelect('admin-content-source-filter', sourceConfigs.map(s => ({ slug: s.slug, nome: s.name })));
}

async function fetchLaunches() {
    const res = await authFetch(`${API_BASE}/launches`);
    const launches = await res.json();
    populateCampaignDropdown(launches);
    populateSelect('filter-campaign', launches.map(l => ({ slug: l.slug, nome: l.nome || l.slug })));
    return launches;
}

async function fetchLinks() {
    const res = await authFetch(`${API_BASE}/links`);
    currentLinks = await res.json();
    renderLinksTable();
}

function populateSelect(id, items) {
    const select = document.getElementById(id);
    if (!select) return;
    const currentValue = select.value;
    const firstOption = select.options[0];
    const firstText = firstOption ? firstOption.text : 'Selecionar';

    select.innerHTML = `<option value="">${firstText}</option>`;
    if (!items || !Array.isArray(items)) return;

    items.forEach(item => {
        const val = item.slug || item;
        const txt = item.nome || item.name || item;
        const opt = new Option(txt, val);
        select.add(opt);
    });
    if (currentValue) select.value = currentValue;
}

function populateCampaignDropdown(launches) {
    const select = document.getElementById('campaign-select');
    if (!select) return;
    select.innerHTML = '<option value="" disabled selected>Selecionar Campaign</option>';
    launches.forEach(l => {
        const opt = new Option(l.nome || l.slug, l.slug);
        select.add(opt);
    });
}

// Filter Logic
function applyFilters() {
    const search = document.getElementById('search-links').value.toLowerCase();
    const campaign = document.getElementById('filter-campaign').value;
    const source = document.getElementById('filter-source').value;
    const medium = document.getElementById('filter-medium').value;
    const content = document.getElementById('filter-content').value;
    const term = document.getElementById('filter-term').value.toLowerCase();

    const filtered = currentLinks.filter(l => {
        const matchesSearch = !search || l.id.toLowerCase().includes(search) || (l.full_url && l.full_url.toLowerCase().includes(search));
        const matchesCampaign = !campaign || l.utm_campaign === campaign;
        const matchesSource = !source || l.utm_source === source;
        const matchesMedium = !medium || l.utm_medium === medium;
        const matchesContent = !content || l.utm_content === content;
        const matchesTerm = !term || (l.utm_term && l.utm_term.toLowerCase().includes(term));

        return matchesSearch && matchesCampaign && matchesSource && matchesMedium && matchesContent && matchesTerm;
    });

    renderLinksTable(filtered);
    filteredLinks = filtered; // Update state for export
}

// Cascading Logic
function updateMediums(sourceSlug) {
    const source = sourceConfigs.find(s => s.slug === sourceSlug);
    // New structure: source.config.mediums
    populateSelect('subtype', source ? (source.config?.mediums || []) : []);
}

function updateContents(sourceSlug) {
    if (!sourceSlug || typeof sourceSlug !== 'string') {
        const el = document.getElementById('channel');
        sourceSlug = el ? el.value : null;
    }
    const source = sourceConfigs.find(s => s.slug === sourceSlug);
    // Populate content based on SOURCE.
    populateSelect('content-select', source ? (source.config?.contents || []) : []);
}

function updateDynamicFields(sourceSlug) {
    const source = sourceConfigs.find(s => s.slug === sourceSlug);
    const container = document.getElementById('dynamic-fields-container');
    if (!container) return;

    container.innerHTML = '';
    if (!source || !source.config) return;

    const config = source.config;

    if (config.required_fields && (config.required_fields.includes('date') || config.term_config === 'standard')) {
        const today = new Date().toISOString().split('T')[0];
        container.innerHTML = `
            <div class="form-group">
                <label for="dynamic-date">Data de Envio (Termo/Interno)</label>
                <input type="date" id="dynamic-date" value="${today}">
            </div>
        `;
    }
}

// Campaign Preview Functions
function updateCampaignPreview() {
    const prod = document.getElementById('gen-product') ? document.getElementById('gen-product').value : "";
    const turma = document.getElementById('gen-turma') ? document.getElementById('gen-turma').value : "";
    const type = document.getElementById('gen-type') ? document.getElementById('gen-type').value : "";
    const month = document.getElementById('gen-month') ? document.getElementById('gen-month').value : "";
    const year = document.getElementById('gen-year') ? document.getElementById('gen-year').value : "";

    const preview = document.getElementById('campaign-preview-text');
    if (!preview) return;

    if (!prod || !turma || !type || !month || !year) {
        preview.innerText = '...';
        return;
    }

    const formattedDate = `${month}-${year.slice(2)}`;
    const campaign = `${prod}_${turma}_${type}_${formattedDate}`;
    preview.innerText = campaign;
}

async function saveGeneratedCampaign() {
    const preview = document.getElementById('campaign-preview-text');
    const nameInput = document.getElementById('gen-campaign-name');
    if (!preview || preview.innerText === '...' || !nameInput || !nameInput.value) {
        alert('Por favor, preencha o Nome da Campaign e todos os campos do gerador.');
        return;
    }

    const slug = preview.innerText;
    const nome = nameInput.value;
    const btn = document.getElementById('btn-save-campaign');
    if (btn) btn.disabled = true;

    try {
        const res = await authFetch(`${API_BASE}/launches`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ slug, nome: nome, owner: 'admin', status: 'active' })
        });
        if (res.ok) {
            alert('Campaign criada com sucesso!');
            nameInput.value = '';
            await fetchLaunches();
            renderAdminLists();
            return;
        }

        let errorMsg = `Erro ao salvar Campaign (status ${res.status}).`;
        try {
            const data = await res.json();
            if (data?.detail) errorMsg = `${errorMsg} ${data.detail}`;
        } catch (_) {
            // Ignore JSON parsing failures.
        }
        console.error('Save campaign failed:', res.status, res.statusText);
        alert(errorMsg);
    } catch (err) {
        console.error('Save campaign error:', err);
        alert('Erro ao salvar Campaign');
    } finally {
        if (btn) btn.disabled = false;
    }
}

// Link Generation
async function handleGenerateLink(e) {
    e.preventDefault();
    const campaign = document.getElementById('campaign-select').value;
    const source = document.getElementById('channel').value;
    const medium = document.getElementById('subtype').value;
    const content = document.getElementById('content-select').value;
    const baseUrl = document.getElementById('base_url').value;
    let utmTerm = document.getElementById('utm_term').value;
    const notes = document.getElementById('notes').value;

    if (!campaign || !source || !medium || !baseUrl) {
        alert('Por favor, preencha todos os campos obrigatórios.');
        return;
    }

    const sourceConfig = sourceConfigs.find(s => s.slug === source);

    // Handle Date for Term
    const dateInput = document.getElementById('dynamic-date');
    let dateStr = "";
    if (dateInput && dateInput.value) {
        const [y, m, d] = dateInput.value.split('-');
        dateStr = `${d}-${m}-${y}`;
    } else {
        const today = new Date();
        dateStr = `${String(today.getDate()).padStart(2, '0')}-${String(today.getMonth() + 1).padStart(2, '0')}-${today.getFullYear()}`;
    }

    if (sourceConfig && sourceConfig.term_config === 'standard') {
        utmTerm = utmTerm ? `${utmTerm}_${dateStr}` : dateStr;
    }

    const payload = {
        link_type: currentMode,
        base_url: baseUrl,
        utm_source: source,
        utm_medium: medium,
        utm_campaign: campaign,
        utm_content: content,
        utm_term: utmTerm,
        dynamic_fields: { date: dateStr },
        notes: notes
    };

    try {
        const res = await authFetch(`${API_BASE}/links/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            let msg = `Erro ao gerar o link (status ${res.status}).`;
            try {
                const errData = await res.json();
                if (errData?.detail) msg = `${msg} ${errData.detail}`;
            } catch (_) {
                // Ignore response parsing errors.
            }
            alert(msg);
            return;
        }

        const link = await res.json();
        showResult(link);
        await fetchLinks();
    } catch (err) {
        console.error('Generate link error:', err);
        alert('Erro ao gerar o link.');
    }
}

function showResult(link) {
    const resultCard = document.getElementById('result-container');
    if (resultCard) {
        resultCard.classList.remove('hidden');
        document.getElementById('final-url').innerText = link.full_url;
        document.getElementById('res-id').innerText = link.id;
        document.getElementById('res-source').innerText = link.utm_source;
        document.getElementById('res-medium').innerText = link.utm_medium;
        document.getElementById('res-campaign').innerText = link.utm_campaign;
        document.getElementById('res-content').innerText = link.utm_content;
        resultCard.scrollIntoView({ behavior: 'smooth' });
    }
}

// Admin Editing Logic
function editItem(type, slug, parentS = null, parentM = null) {
    editingMode = { active: true, type, oldSlug: slug, parentSource: parentS, parentMedium: parentM };
    console.log(`Editing ${type}: ${slug}`);

    let item, formId;
    if (type === 'products') {
        item = products.find(p => p.slug === slug);
        formId = 'admin-product-form';
    } else if (type === 'turmas') {
        item = turmas.find(t => t.slug === slug);
        formId = 'admin-turma-form';
    } else if (type === 'launch-types') {
        item = launchTypes.find(lt => lt.slug === slug);
        formId = 'admin-launchtype-form';
    } else if (type === 'source-configs') {
        item = sourceConfigs.find(s => s.slug === slug);
        formId = 'admin-source-form-new';
    } else if (type === 'mediums') {
        const source = sourceConfigs.find(s => s.slug === parentS);
        item = source.config.mediums.find(m => m.slug === slug);
        formId = 'admin-medium-form-new';
    } else if (type === 'contents') {
        const source = sourceConfigs.find(s => s.slug === parentS);
        if (source && source.config && source.config.contents) {
            item = source.config.contents.find(c => c.slug === slug);
        }
        if (!item) item = { slug: slug, name: slug }; // Fallback
        formId = 'admin-content-form-new';
    } else if (type === 'launches') {
        item = { slug: slug, nome: slug };
        // For launches, we use a prompt or we could build a small overlay. 
        // For now, let's use a prompt to be quick as requested, or just renaming via API.
        const newName = prompt("Digite o novo nome para a Campaign:", slug);
        if (newName) {
            authFetch(`${API_BASE}/launches`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ slug, nome: newName, owner: 'admin', status: 'active' })
            }).then(() => fetchLaunches().then(renderAdminLists));
        }
        editingMode.active = false;
        return;
    }

    if (item && formId) {
        const form = document.getElementById(formId);
        if (form) {
            const slugInput = form.querySelector('input[id*="slug"]');
            const nameInput = form.querySelector('input[id*="name"]');

            if (slugInput) slugInput.value = item.slug || "";
            if (nameInput) nameInput.value = item.nome || item.name || "";

            if (type === 'source-configs') {
                const termInput = document.getElementById('source-new-term');
                if (termInput) termInput.value = item.config?.term_config || "standard";
            }

            const submitBtn = form.querySelector('button[type="submit"] span');
            if (submitBtn) submitBtn.innerText = 'Salvar Alterações';

            // Add Cancel button inside form-actions
            const actions = form.querySelector('.form-actions');
            if (actions && !document.getElementById(`cancel-${formId}`)) {
                const cancelBtn = document.createElement('button');
                cancelBtn.type = 'button';
                cancelBtn.className = 'btn btn-secondary btn-sm';
                cancelBtn.id = `cancel-${formId}`;
                cancelBtn.innerText = 'Cancelar';
                cancelBtn.onclick = () => resetAdminForm(formId, type);
                actions.appendChild(cancelBtn);
            }
            form.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
}

function resetAdminForm(formId, type) {
    editingMode = { active: false, type: null, oldSlug: null, parentSource: null, parentMedium: null };
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
        const submitBtn = form.querySelector('button[type="submit"] span');
        if (submitBtn) {
            const labels = {
                'source-configs': 'Adicionar Source',
                'products': 'Adicionar Produto',
                'turmas': 'Adicionar Turma',
                'launch-types': 'Adicionar Tipo',
                'mediums': 'Adicionar Medium',
                'contents': 'Adicionar Content'
            };
            submitBtn.innerText = labels[type] || 'Adicionar';
        }
        const cancelBtn = document.getElementById(`cancel-${formId}`);
        if (cancelBtn) cancelBtn.remove();
    }
}

// Admin Rendering
function renderAdminLists() {
    renderCampaignSettingsTab();
    renderSourcesTab();
    renderMediumsTab();
    renderContentsTab();
}

function renderCampaignSettingsTab() {
    const pList = document.getElementById('admin-products-list');
    const tList = document.getElementById('admin-turmas-list');
    const ltList = document.getElementById('admin-launchtypes-list');
    const lList = document.getElementById('admin-launches-list');

    const render = (items, type, refreshFnName) => items.map(p => {
        const name = p.nome || p.name;
        const slug = p.slug;
        const displaySlug = (name === slug) ? "" : slug;
        return `
            <div class="admin-item">
                <div class="info">
                    <span>${name}</span>
                    ${displaySlug ? `<span>${displaySlug}</span>` : ''}
                </div>
                <div class="actions">
                    <button class="btn btn-secondary btn-sm" onclick="editItem('${type}', '${slug}')">Editar</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteSimpleItem('${type}', '${slug}', ${refreshFnName})">Remover</button>
                </div>
            </div>
        `;
    }).join('');

    if (pList) pList.innerHTML = render(products, 'products', 'fetchProducts');
    if (tList) tList.innerHTML = render(turmas, 'turmas', 'fetchTurmas');
    if (ltList) ltList.innerHTML = render(launchTypes, 'launch-types', 'fetchLaunchTypes');

    if (lList) {
        authFetch(`${API_BASE}/launches`).then(res => res.json()).then(launches => {
            lList.innerHTML = launches.map(l => {
                const name = l.nome || l.slug;
                const slug = l.slug;
                const displaySlug = (name === slug) ? "" : slug;
                return `
                    <div class="admin-item">
                        <div class="info">
                            <span>${name}</span>
                            ${displaySlug ? `<span>${displaySlug}</span>` : ''}
                        </div>
                        <div class="actions">
                            <button class="btn btn-secondary btn-sm" onclick="editItem('launches', '${slug}')">Editar</button>
                            <button class="btn btn-danger btn-sm" onclick="deleteSimpleItem('launches', '${slug}', fetchLaunches)">Remover</button>
                        </div>
                    </div>
                `;
            }).join('');
        });
    }
}

function renderSourcesTab() {
    const list = document.getElementById('admin-sources-list');
    if (list) {
        list.innerHTML = sourceConfigs.map(s => `
            <div class="admin-item">
                <div class="info">
                    <span>${s.name}</span>
                    <span>slug: ${s.slug} | config: ${s.config?.term_config || 'standard'}</span>
                </div>
                <div class="actions">
                    <button class="btn btn-secondary btn-sm" onclick="editItem('source-configs', '${s.slug}')">Editar</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteSimpleItem('source-configs', '${s.slug}', fetchSourceConfigs)">Remover</button>
                </div>
            </div>
        `).join('');
    }
}

function renderMediumsTab() {
    const area = document.getElementById('medium-management-area');
    const empty = document.getElementById('medium-empty-state');
    const listCard = document.getElementById('medium-list-card');
    const list = document.getElementById('admin-mediums-list');
    const label = document.getElementById('current-source-label');

    console.log('renderMediumsTab called', { adminSelectedSource, sourceConfigsCount: sourceConfigs.length });

    if (!adminSelectedSource) {
        if (area) area.classList.add('hidden');
        if (empty) empty.classList.remove('hidden');
        if (listCard) listCard.classList.add('hidden');
        return;
    }
    const source = sourceConfigs.find(s => s.slug === adminSelectedSource);
    console.log('Found source:', source);

    if (!source) return;
    if (area) area.classList.remove('hidden');
    if (empty) empty.classList.add('hidden');
    if (listCard) listCard.classList.remove('hidden');
    if (label) label.innerText = source.name;

    // New structure: source.config.mediums
    const mediums = source.config?.mediums || [];
    console.log('Mediums to render:', mediums);

    if (list) list.innerHTML = mediums.map(m => `
        <div class="admin-item">
            <div class="info">
                <span>${m.name}</span>
                <span>slug: ${m.slug}</span>
            </div>
            <div class="actions">
                <button class="btn btn-secondary btn-sm" onclick="editItem('mediums', '${m.slug}', '${source.slug}')">Editar</button>
                <button class="btn btn-danger btn-sm" onclick="deleteMedium('${source.slug}', '${m.slug}')">Remover</button>
            </div>
        </div>
    `).join('');
}

function renderContentsTab() {
    const area = document.getElementById('content-management-area');
    const empty = document.getElementById('content-empty-state');
    const listCard = document.getElementById('content-list-card');
    const list = document.getElementById('admin-contents-list');
    const label = document.getElementById('content-current-context-label'); // Ensure ID matches HTML

    // Content is now based on Source only
    if (!adminSelectedSource) {
        if (area) area.classList.add('hidden');
        if (empty) empty.classList.remove('hidden');
        if (listCard) listCard.classList.add('hidden');
        return;
    }

    const source = sourceConfigs.find(s => s.slug === adminSelectedSource);
    if (!source) return;

    if (area) area.classList.remove('hidden');
    if (empty) empty.classList.add('hidden');
    if (listCard) listCard.classList.remove('hidden');

    // New structure: source.config.contents
    const contents = source.config?.contents || [];

    if (list) list.innerHTML = contents.map(c => `
        <div class="admin-item">
            <div class="info">
                <span>${c.name}</span>
                <span>slug: ${c.slug}</span>
            </div>
            <div class="actions">
                <button class="btn btn-secondary btn-sm" onclick="editItem('contents', '${c.slug}', '${source.slug}')">Editar</button>
                <button class="btn btn-danger btn-sm" onclick="deleteContent('${source.slug}', '${c.slug}')">Remover</button>
            </div>
        </div>
    `).join('');

    if (label) {
        label.innerText = source.name;
        label.classList.remove('hidden');
    }
}

// Admin API Handlers
async function handleAdminSourceSubmit(e) {
    if (e) e.preventDefault();
    const slug = document.getElementById('source-new-slug').value;
    const name = document.getElementById('source-new-name').value;
    const term = document.getElementById('source-new-term').value;

    let payload;
    if (editingMode.active && editingMode.type === 'source-configs') {
        const oldSource = sourceConfigs.find(s => s.slug === editingMode.oldSlug);
        // Ensure config exists
        const oldConfig = oldSource.config || { mediums: [], contents: [], required_fields: [] };
        // Update term_config
        oldConfig.term_config = term;

        payload = { ...oldSource, slug, name, config: oldConfig };

        if (slug !== editingMode.oldSlug) {
            await authFetch(`${API_BASE}/source-configs/${editingMode.oldSlug}`, { method: 'DELETE' });
        }
    } else {
        // New Source
        const newConfig = {
            mediums: [],
            contents: [],
            term_config: term,
            required_fields: term === 'standard' ? ['date'] : []
        };
        payload = { slug, name, config: newConfig };
    }

    await authFetch(`${API_BASE}/source-configs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    resetAdminForm('admin-source-form-new', 'source-configs');
    await fetchSourceConfigs();
    renderAdminLists();
}

async function handleAdminSimpleSubmit(e, endpoint, refresh) {
    if (e) e.preventDefault();
    const slug = e.target.querySelector('input[id*="slug"]').value;
    const nome = e.target.querySelector('input[id*="name"]').value;

    if (editingMode.active && editingMode.type === endpoint) {
        if (slug !== editingMode.oldSlug) {
            await authFetch(`${API_BASE}/${endpoint}/${editingMode.oldSlug}`, { method: 'DELETE' });
        }
    }

    await authFetch(`${API_BASE}/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug, nome })
    });

    resetAdminForm(e.target.id, endpoint);
    await refresh();
    renderAdminLists();
}

async function handleAdminMediumSubmit(e) {
    if (e) e.preventDefault();
    const slug = document.getElementById('medium-new-slug').value;
    const name = document.getElementById('medium-new-name').value;

    console.log('handleAdminMediumSubmit called', { slug, name, adminSelectedSource });

    const source = sourceConfigs.find(s => s.slug === adminSelectedSource);
    if (!source) {
        console.error('Source not found:', adminSelectedSource);
        alert('Erro: Source não encontrado');
        return;
    }

    console.log('Source before modification:', JSON.parse(JSON.stringify(source)));

    // Ensure config
    if (!source.config) source.config = { mediums: [], contents: [] };

    if (editingMode.active && editingMode.type === 'mediums') {
        const mIdx = source.config.mediums.findIndex(m => m.slug === editingMode.oldSlug);
        if (mIdx > -1) {
            source.config.mediums[mIdx].slug = slug;
            source.config.mediums[mIdx].name = name;
        }
    } else {
        source.config.mediums.push({ slug, name });
    }

    console.log('Source after modification:', JSON.parse(JSON.stringify(source)));

    try {
        const response = await authFetch(`${API_BASE}/source-configs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(source)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('API Error:', errorText);
            alert(`Erro ao salvar: ${errorText}`);
            return;
        }

        console.log('Medium saved successfully');
        resetAdminForm('admin-medium-form-new', 'mediums');
        await fetchSourceConfigs();
        renderAdminLists();
    } catch (error) {
        console.error('Error saving medium:', error);
        alert(`Erro ao salvar medium: ${error.message}`);
    }
}

async function handleAdminContentSubmit(e) {
    if (e) e.preventDefault();
    const slug = document.getElementById('content-new-slug').value.trim();
    const name = document.getElementById('content-new-name').value.trim();

    console.log('handleAdminContentSubmit called', { slug, name, adminSelectedSource });

    const source = sourceConfigs.find(s => s.slug === adminSelectedSource);
    if (!source) {
        console.error('Source not found:', adminSelectedSource);
        alert('Erro: Source não encontrado');
        return;
    }

    console.log('Source before modification:', JSON.parse(JSON.stringify(source)));

    // Ensure config
    if (!source.config) source.config = { mediums: [], contents: [] };
    if (!source.config.contents) source.config.contents = [];

    const newItem = { slug, name };

    if (editingMode.active && editingMode.type === 'contents') {
        const cIdx = source.config.contents.findIndex(c => c.slug === editingMode.oldSlug);
        if (cIdx > -1) {
            source.config.contents[cIdx] = newItem;
        }
    } else {
        source.config.contents.push(newItem);
    }

    console.log('Source after modification:', JSON.parse(JSON.stringify(source)));

    try {
        const response = await authFetch(`${API_BASE}/source-configs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(source)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('API Error:', errorText);
            alert(`Erro ao salvar: ${errorText}`);
            return;
        }

        console.log('Content saved successfully');
        resetAdminForm('admin-content-form-new', 'contents');
        await fetchSourceConfigs();
        renderAdminLists();
    } catch (error) {
        console.error('Error saving content:', error);
        alert(`Erro ao salvar content: ${error.message}`);
    }
}

async function deleteSimpleItem(ep, id, refresh) {
    if (confirm('Tem certeza que deseja remover este item?')) { await authFetch(`${API_BASE}/${ep}/${id}`, { method: 'DELETE' }); await refresh(); renderAdminLists(); }
}

async function deleteMedium(s, m) {
    if (!confirm('Tem certeza que deseja remover este meio?')) return;
    const source = sourceConfigs.find(sc => sc.slug === s);
    if (!source || !source.config) return;
    source.config.mediums = source.config.mediums.filter(ms => ms.slug !== m);
    await authFetch(`${API_BASE}/source-configs`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(source) });
    await fetchSourceConfigs();
    renderAdminLists();
}


async function deleteContent(s, c) {
    if (!confirm('Tem certeza que deseja remover este conteúdo?')) return;
    const source = sourceConfigs.find(sc => sc.slug === s);
    if (!source || !source.config) return;
    source.config.contents = source.config.contents.filter(ct => ct.slug !== c);
    await authFetch(`${API_BASE}/source-configs`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(source) });
    await fetchSourceConfigs();
    renderAdminLists();
}

// Helpers
function showToast(message) {
    const toast = document.getElementById('toast');
    if (toast) {
        toast.innerText = message;
        toast.classList.remove('hidden');
        setTimeout(() => toast.classList.add('hidden'), 3000);
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text);
    showToast("Copiado para a área de transferência!");
}

function splitTerm(term) {
    if (!term) return { detail: '-', date: '-' };
    const dateRegex = /^\d{2}-\d{2}-\d{4}$/;
    const parts = term.split('_');
    const lastPart = parts[parts.length - 1];

    if (dateRegex.test(lastPart)) {
        const date = lastPart;
        const detail = parts.slice(0, -1).join('_') || '-';
        return { detail, date };
    }
    return { detail: term, date: '-' };
}

function renderLinksTable(links = currentLinks) {
    const tbody = document.getElementById('links-tbody');
    const emptyState = document.getElementById('empty-state');
    if (!tbody) return;

    tbody.innerHTML = links.map(l => {
        const { detail, date } = splitTerm(l.utm_term);
        return `
            <tr>
                <td><code>${l.id}</code></td>
                <td>${l.utm_campaign}</td>
                <td>${l.utm_source}</td>
                <td>${l.utm_medium}</td>
                <td>${l.utm_content}</td>
                <td>${detail}</td>
                <td>${date}</td>
                <td class="actions-col">
                    <button class="btn btn-secondary btn-sm" onclick="copyToClipboard('${l.full_url}')">Copy</button>
                </td>
            </tr>
        `;
    }).join('');

    if (emptyState) emptyState.classList.toggle('hidden', links.length > 0);
    filteredLinks = links; // Initial/Fallback filtered state
}

function exportToCSV() {
    if (!filteredLinks || filteredLinks.length === 0) {
        alert('Nenhum link pesquisado para exportar.');
        return;
    }

    const headers = ['ID', 'Campaign', 'Source', 'Medium', 'Content', 'Term', 'URL Final', 'Notas'];
    const rows = filteredLinks.map(l => [
        l.id,
        l.utm_campaign,
        l.utm_source,
        l.utm_medium,
        l.utm_content || '-',
        l.utm_term || '-',
        l.full_url,
        l.notes || '-'
    ]);

    let csvContent = "data:text/csv;charset=utf-8,"
        + headers.join(",") + "\n"
        + rows.map(e => e.map(val => `"${val}"`).join(",")).join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    const date = new Date().toISOString().split('T')[0];
    link.setAttribute("download", `viciolinks_export_${date}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/** USER MANAGEMENT LOGIC **/

// Add basic listener in setupEventListeners if I could, but I'll add them here for convenience
document.addEventListener('click', e => {
    if (e.target.id === 'nav-users') {
        showScreen('users');
        loadUsers();
    }
});

async function loadUsers() {
    try {
        const res = await authFetch(`${API_BASE}/users`);
        if (res.ok) {
            const users = await res.json();
            renderUsers(users);
        }
    } catch (err) {
        console.error("Failed to load users", err);
    }
}

function renderUsers(users) {
    const list = document.getElementById('users-list');
    if (!list) return;
    list.innerHTML = '';

    users.forEach(u => {
        const item = document.createElement('div');
        item.className = 'user-item';
        item.innerHTML = `
            <div class="user-info">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <h4 style="margin: 0; font-size: 0.95rem;">${u.username}</h4>
                    <span class="role-badge" style="font-size: 0.65rem; padding: 0.1rem 0.5rem;">${u.role}</span>
                    ${u.disabled ? '<span style="color:var(--error); font-size: 0.7rem;">(Desativado)</span>' : ''}
                </div>
            </div>
            <div class="actions">
                <button class="btn btn-secondary btn-sm" onclick="editUser('${u.username}', '${u.role}')">Editar</button>
                ${u.username !== 'admin' ? `<button class="btn btn-danger btn-sm" onclick="deleteUser('${u.username}')">Excluir</button>` : ''}
            </div>
        `;
        list.appendChild(item);
    });
}

const userForm = document.getElementById('user-form');
if (userForm) {
    userForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('user-username').value;
        const password = document.getElementById('user-password').value;
        const role = document.getElementById('user-role').value;
        const isEdit = document.getElementById('edit-user-mode').value === 'true';

        try {
            const method = isEdit ? 'PUT' : 'POST';
            const url = isEdit ? `${API_BASE}/users/${username}` : `${API_BASE}/users`;

            const res = await authFetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, role })
            });

            if (res.ok) {
                showToast(isEdit ? "Usuário atualizado!" : "Usuário criado!");
                resetUserForm();
                loadUsers();
            } else {
                const err = await res.json();
                alert(err.detail || "Erro ao salvar usuário");
            }
        } catch (err) {
            console.error(err);
            alert("Erro na conexão");
        }
    });
}

function editUser(username, role) {
    document.getElementById('user-username').value = username;
    document.getElementById('user-username').disabled = true;
    document.getElementById('user-password').placeholder = "Nova senha (obrigatorio)";
    document.getElementById('user-role').value = role;
    document.getElementById('edit-user-mode').value = "true";
    document.getElementById('user-form-title').innerText = "Editar Usuário: " + username;
    document.getElementById('btn-save-user').querySelector('span').innerText = "Atualizar Usuário";
    document.getElementById('cancel-user-edit').classList.remove('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function resetUserForm() {
    userForm.reset();
    document.getElementById('user-username').disabled = false;
    document.getElementById('user-password').placeholder = "Defina uma senha";
    document.getElementById('edit-user-mode').value = "false";
    document.getElementById('user-form-title').innerText = "Adicionar Novo Usuário";
    document.getElementById('btn-save-user').querySelector('span').innerText = "Salvar Usuário";
    document.getElementById('cancel-user-edit').classList.add('hidden');
}

document.getElementById('cancel-user-edit')?.addEventListener('click', resetUserForm);

async function deleteUser(username) {
    if (!confirm(`Tem certeza que deseja excluir o usuário ${username}?`)) return;
    try {
        const res = await authFetch(`${API_BASE}/users/${username}`, { method: 'DELETE' });
        if (res.ok) {
            showToast("Usuário excluído!");
            loadUsers();
        }
    } catch (err) {
        console.error(err);
    }
}
