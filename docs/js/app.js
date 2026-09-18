/**
 * Expanso Skills Marketplace
 * Vanilla JavaScript for filtering, searching, and displaying skills
 *
 * Security: All user-facing content is escaped via textContent
 */

(function() {
    'use strict';

    // State
    var catalog = null;
    var validationReport = null;
    var filteredSkills = [];
    var currentCategory = 'all';
    var searchQuery = '';
    var filterLocal = false;
    var filterNoCreds = false;

    var SKILLS_BASE = window.location.origin;
    var GITHUB_RAW_BASE = 'https://raw.githubusercontent.com/expanso-io/skills.expanso.io/main';

    // DOM Elements
    var skillsGrid = document.getElementById('skills-grid');
    var searchInput = document.getElementById('search');
    var skillCountEl = document.getElementById('skill-count');
    var modalOverlay = document.getElementById('modal-overlay');
    var modalContent = document.getElementById('modal-content');
    var categoryTabs = document.querySelectorAll('.tab[data-category]');
    var filterLocalCheckbox = document.getElementById('filter-local');
    var filterNoCredsCheckbox = document.getElementById('filter-no-creds');

    var categoryColors = {
        ai: 'badge-ai',
        security: 'badge-security',
        transforms: 'badge-transforms',
        utilities: 'badge-utilities',
        workflows: 'badge-workflows',
        connectors: 'badge-connectors',
        jobs: 'badge-jobs'
    };

    function initThemeToggle() {
        var button = document.getElementById('theme-toggle');
        if (!button) return;
        var root = document.documentElement;
        function render() {
            var dark = root.getAttribute('data-theme') === 'dark';
            button.textContent = dark ? 'Light' : 'Dark';
            button.setAttribute('aria-pressed', dark ? 'true' : 'false');
            button.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
        }
        button.addEventListener('click', function() {
            var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            root.setAttribute('data-theme', next);
            try { localStorage.setItem('theme', next); } catch (e) {}
            render();
        });
        render();
    }

    async function init() {
        initThemeToggle();
        try {
            await loadCatalog();
            await loadValidationReport();
            bindEvents();
            filterAndRender();

            var redirectPath = sessionStorage.getItem('spa-redirect');
            if (redirectPath) {
                sessionStorage.removeItem('spa-redirect');
                history.replaceState(null, '', redirectPath);
            }
            var match = window.location.pathname.match(/^\/skill\/([^/]+)\/?$/);
            if (match && catalog.skills[match[1]]) {
                openModal(match[1], true);
            }
        } catch (error) {
            console.error('Failed to initialize:', error);
            showNoResults('Failed to load skills. Please refresh the page.');
        }
    }

    async function loadCatalog() {
        var urls = ['catalog.json', '../catalog.json', GITHUB_RAW_BASE + '/catalog.json'];
        for (var i = 0; i < urls.length; i++) {
            try {
                var response = await fetch(urls[i]);
                if (response.ok) {
                    catalog = await response.json();
                    skillCountEl.textContent = String(catalog.total_skills);
                    return;
                }
            } catch (e) { continue; }
        }
        throw new Error('Could not load catalog from any source');
    }

    // Best effort: without the report the modal says status is unknown rather
    // than implying a pipeline validates.
    async function loadValidationReport() {
        var urls = ['validation-report.json', '../validation-report.json', GITHUB_RAW_BASE + '/validation-report.json'];
        for (var i = 0; i < urls.length; i++) {
            try {
                var response = await fetch(urls[i]);
                if (response.ok) {
                    validationReport = await response.json();
                    return;
                }
            } catch (e) { continue; }
        }
    }

    function variantStatus(skillName, variant) {
        var entry = validationReport && validationReport.skills && validationReport.skills[skillName];
        return entry && entry.variants ? entry.variants[variant] || null : null;
    }

    function isOffline(skill) {
        return (skill.tags || []).indexOf('offline') !== -1;
    }

    async function fetchSkillFile(skillName, filename, category) {
        var urls = [
            SKILLS_BASE + '/' + skillName + '/' + filename,
            GITHUB_RAW_BASE + '/skills/' + category + '/' + skillName + '/' + filename
        ];
        for (var i = 0; i < urls.length; i++) {
            try {
                var response = await fetch(urls[i]);
                if (response.ok) return await response.text();
            } catch (e) { continue; }
        }
        return null;
    }

    function getSkillUrl(skillName, filename) {
        return 'https://skills.expanso.io/' + skillName + '/' + filename;
    }

    function bindEvents() {
        searchInput.addEventListener('input', debounce(function(e) {
            searchQuery = e.target.value.toLowerCase().trim();
            filterAndRender();
        }, 150));

        categoryTabs.forEach(function(tab) {
            tab.addEventListener('click', function() {
                categoryTabs.forEach(function(t) {
                    t.classList.remove('active');
                    t.setAttribute('aria-selected', 'false');
                });
                tab.classList.add('active');
                tab.setAttribute('aria-selected', 'true');
                currentCategory = tab.dataset.category;
                filterAndRender();
            });
        });

        filterLocalCheckbox.addEventListener('change', function(e) {
            filterLocal = e.target.checked;
            filterAndRender();
        });

        filterNoCredsCheckbox.addEventListener('change', function(e) {
            filterNoCreds = e.target.checked;
            filterAndRender();
        });

        modalOverlay.addEventListener('click', function(e) {
            if (e.target === modalOverlay || e.target.classList.contains('modal-close')) {
                closeModal();
            }
        });

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && modalOverlay.classList.contains('active')) {
                closeModal();
            }
        });

        window.addEventListener('popstate', function(e) {
            if (e.state && e.state.skill) {
                openModal(e.state.skill, true);
            } else {
                closeModal(true);
            }
        });

        document.addEventListener('click', function(e) {
            var copyBtn = e.target.closest('.copy-btn');
            if (copyBtn) {
                var text = copyBtn.dataset.copy;
                if (text) copyToClipboard(text, copyBtn);
            }
        });
    }

    function filterAndRender() {
        if (!catalog) return;
        var skills = Object.entries(catalog.skills);
        filteredSkills = skills.filter(function(entry) {
            var name = entry[0], skill = entry[1];
            if (currentCategory !== 'all' && skill.category !== currentCategory) return false;
            if (searchQuery) {
                var searchStr = (name + ' ' + skill.description).toLowerCase();
                if (!searchStr.includes(searchQuery)) return false;
            }
            if (filterLocal) {
                if (!isOffline(skill)) return false;
            }
            if (filterNoCreds) {
                if (skill.credentials.filter(function(c) { return c.required; }).length > 0) return false;
            }
            return true;
        });
        renderSkills();
    }

    function showNoResults(message) {
        while (skillsGrid.firstChild) skillsGrid.removeChild(skillsGrid.firstChild);
        var div = document.createElement('div');
        div.className = 'no-results';
        div.textContent = message;
        skillsGrid.appendChild(div);
    }

    function renderSkills() {
        while (skillsGrid.firstChild) skillsGrid.removeChild(skillsGrid.firstChild);
        if (filteredSkills.length === 0) {
            showNoResults('No skills found matching your criteria.');
            return;
        }
        filteredSkills.forEach(function(entry) {
            skillsGrid.appendChild(createSkillCard(entry[0], entry[1]));
        });
    }

    function createSkillCard(name, skill) {
        var article = document.createElement('article');
        article.className = 'skill-card';
        article.dataset.skill = name;

        var header = document.createElement('div');
        header.className = 'skill-header';
        var nameSpan = document.createElement('span');
        nameSpan.className = 'skill-name';
        nameSpan.textContent = name;
        header.appendChild(nameSpan);

        var desc = document.createElement('p');
        desc.className = 'skill-description';
        desc.textContent = skill.description;

        var badges = document.createElement('div');
        badges.className = 'skill-badges';
        var categoryBadge = document.createElement('span');
        categoryBadge.className = 'badge ' + (categoryColors[skill.category] || '');
        categoryBadge.textContent = skill.category;
        badges.appendChild(categoryBadge);

        if (isOffline(skill)) {
            var localBadge = document.createElement('span');
            localBadge.className = 'badge badge-local';
            localBadge.textContent = 'offline';
            badges.appendChild(localBadge);
        }

        article.appendChild(header);
        article.appendChild(desc);
        article.appendChild(badges);
        article.addEventListener('click', function() { openModal(name); });
        return article;
    }

    // ── Modal ──────────────────────────────────────────────

    async function openModal(skillName, skipPush) {
        var skill = catalog.skills[skillName];
        if (!skill) return;

        if (!skipPush) history.pushState({ skill: skillName }, '', '/skill/' + skillName);
        updateMetaTags(skillName, skill);

        while (modalContent.firstChild) modalContent.removeChild(modalContent.firstChild);
        var loadingDiv = document.createElement('div');
        loadingDiv.className = 'modal-loading';
        loadingDiv.textContent = 'Loading skill details...';
        modalContent.appendChild(loadingDiv);
        modalOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';

        var hasCloudVariant = !!variantStatus(skillName, 'cloud');
        // Job skills publish their own job specs instead of the cli/mcp pair.
        var jobFiles = skill.job_specs || [];
        var results = await Promise.all([
            fetchSkillFile(skillName, 'skill.yaml', skill.category),
            jobFiles.length ? null : fetchSkillFile(skillName, 'pipeline-cli.yaml', skill.category),
            jobFiles.length ? null : fetchSkillFile(skillName, 'pipeline-mcp.yaml', skill.category),
            hasCloudVariant ? fetchSkillFile(skillName, 'pipeline-cloud.yaml', skill.category) : null
        ].concat(jobFiles.map(function(f) { return fetchSkillFile(skillName, f, skill.category); })));
        var jobSpecs = jobFiles.map(function(f, i) { return { file: f, yaml: results[4 + i] }; })
            .filter(function(j) { return !!j.yaml; });

        while (modalContent.firstChild) modalContent.removeChild(modalContent.firstChild);
        buildModalContent(skillName, skill, results[0], results[1], results[2], results[3], jobSpecs);
        if (window.Prism) Prism.highlightAllUnder(modalContent);
    }

    // Where a job skill was run, from its skill.yaml `proof` block.
    function proofSummary(proof) {
        if (!proof) return '';
        var when = 'On ' + proof.date + ' (expanso-edge ' + proof.expanso_edge + '): ';
        return when + (proof.status === 'executed-cloud-and-local'
            ? 'run end to end on Expanso Cloud (one operator-registered node, not a hosted runner) and on a local-mode node.'
            : 'run end to end on a local-mode node only. It has not been run through Expanso Cloud.');
    }

    function buildModalContent(skillName, skill, skillYaml, pipelineCli, pipelineMcp, pipelineCloud, jobSpecs) {
        jobSpecs = jobSpecs || [];
        // ── Header ──
        var headerDiv = document.createElement('div');
        headerDiv.className = 'modal-header';

        var title = document.createElement('h2');
        title.className = 'modal-title';
        title.textContent = skillName;

        var descP = document.createElement('p');
        descP.className = 'modal-description';
        descP.textContent = skill.description;

        var badgesDiv = document.createElement('div');
        badgesDiv.className = 'skill-badges';
        badgesDiv.style.marginTop = '0.75rem';

        var catBadge = document.createElement('span');
        catBadge.className = 'badge ' + (categoryColors[skill.category] || '');
        catBadge.textContent = skill.category;
        badgesDiv.appendChild(catBadge);

        var verBadge = document.createElement('span');
        verBadge.className = 'badge';
        verBadge.style.background = 'var(--bg-tertiary)';
        verBadge.style.color = 'var(--text-secondary)';
        verBadge.textContent = 'v' + skill.version;
        badgesDiv.appendChild(verBadge);

        skill.backends.forEach(function(b) {
            var badge = document.createElement('span');
            badge.className = 'badge';
            if (b === 'local' || b === 'ollama') {
                badge.style.background = 'var(--success)';
                badge.style.color = 'black';
            } else {
                badge.style.background = 'var(--bg-tertiary)';
                badge.style.color = 'var(--text-primary)';
            }
            badge.textContent = b;
            badgesDiv.appendChild(badge);
        });

        headerDiv.appendChild(title);
        headerDiv.appendChild(descP);
        headerDiv.appendChild(badgesDiv);
        modalContent.appendChild(headerDiv);

        // ── Tabs: Spec | Pipeline ──
        var tabNav = document.createElement('div');
        tabNav.className = 'modal-tabs';

        var tabDefs = [
            { id: 'spec', label: 'Spec' },
            { id: 'pipeline', label: 'Pipeline' }
        ];

        var tabContents = {};

        tabDefs.forEach(function(tab, index) {
            var tabBtn = document.createElement('button');
            tabBtn.className = 'modal-tab' + (index === 0 ? ' active' : '');
            tabBtn.textContent = tab.label;
            tabBtn.dataset.tab = tab.id;
            tabBtn.addEventListener('click', function() {
                tabNav.querySelectorAll('.modal-tab').forEach(function(t) { t.classList.remove('active'); });
                tabBtn.classList.add('active');
                Object.keys(tabContents).forEach(function(key) {
                    tabContents[key].style.display = key === tab.id ? 'block' : 'none';
                });
            });
            tabNav.appendChild(tabBtn);
        });

        modalContent.appendChild(tabNav);

        // ── SPEC tab ──
        var specContent = document.createElement('div');
        specContent.className = 'tab-content';
        tabContents['spec'] = specContent;

        // Inputs
        if (skill.inputs.length > 0) {
            specContent.appendChild(createTableSection('Inputs', ['Name', 'Type', 'Required', 'Default'], skill.inputs.map(function(input) {
                return [input.name, input.type || 'any', input.required ? 'Yes' : 'No', input.default !== undefined ? JSON.stringify(input.default) : '-'];
            }), [true, false, false, true]));
        }

        // Outputs
        if (skill.outputs.length > 0) {
            specContent.appendChild(createTableSection('Outputs', ['Name', 'Type', 'Description'], skill.outputs.map(function(output) {
                return [output.name, output.type || 'any', output.description || ''];
            }), [true, false, false]));
        }

        // Credentials
        if (skill.credentials.length > 0) {
            specContent.appendChild(createTableSection('Credentials', ['Name', 'Required', 'Description'], skill.credentials.map(function(cred) {
                return [cred.name, cred.required ? 'Yes' : 'No', cred.description || ''];
            }), [true, false, false]));
        }

        // skill.yaml source
        if (skillYaml) {
            var yamlSection = document.createElement('div');
            yamlSection.className = 'modal-section';
            var yamlH3 = document.createElement('h3');
            yamlH3.textContent = 'skill.yaml';
            yamlSection.appendChild(yamlH3);
            yamlSection.appendChild(createCodeBlock(skillYaml, 'yaml'));
            specContent.appendChild(yamlSection);
        }

        modalContent.appendChild(specContent);

        // ── PIPELINE tab ──
        var pipelineContent = document.createElement('div');
        pipelineContent.className = 'tab-content';
        pipelineContent.style.display = 'none';
        tabContents['pipeline'] = pipelineContent;

        // Sub-tabs for CLI vs MCP within Pipeline tab
        var hasCli = !!pipelineCli;
        var hasMcp = !!pipelineMcp;
        var hasCloud = !!pipelineCloud;
        var hasJob = jobSpecs.length > 0;

        if (hasJob && skill.proof) {
            var proofDiv = document.createElement('div');
            proofDiv.className = 'modal-section';
            var proofH3 = document.createElement('h3');
            proofH3.textContent = 'Proof';
            proofDiv.appendChild(proofH3);
            var proofP = document.createElement('p');
            proofP.className = 'readiness-note';
            proofP.textContent = proofSummary(skill.proof);
            proofDiv.appendChild(proofP);
            [['Proved', skill.proof.proved], ['Not proved', skill.proof.not_proved]].forEach(function(pair) {
                if (!pair[1] || !pair[1].length) return;
                var h = document.createElement('h4');
                h.textContent = pair[0];
                proofDiv.appendChild(h);
                var ul = document.createElement('ul');
                pair[1].forEach(function(line) {
                    var li = document.createElement('li');
                    li.textContent = line;
                    ul.appendChild(li);
                });
                proofDiv.appendChild(ul);
            });
            pipelineContent.appendChild(proofDiv);
        }

        if (!hasCli && !hasMcp && !hasCloud && !hasJob) {
            var noMsg = document.createElement('p');
            noMsg.className = 'no-content';
            noMsg.textContent = 'No pipeline available for this skill.';
            pipelineContent.appendChild(noMsg);
        } else {
            // Pipeline sub-tab bar
            var pipeSubNav = document.createElement('div');
            pipeSubNav.className = 'pipeline-sub-tabs';

            var pipeSubContents = {};
            var pipeSubDefs = [];
            jobSpecs.forEach(function(j) {
                var isQuery = j.file === 'pipeline-query.yaml';
                pipeSubDefs.push({
                    id: isQuery ? 'query' : 'recipe',
                    label: isQuery ? 'Search job' : 'Job spec',
                    yaml: j.yaml,
                    file: j.file,
                    job: true,
                    desc: isQuery
                        ? 'Second job: answers questions from what the ingest job stored. Deploy it after the job spec has run.'
                        : 'The job that was run, with only the values in its header comment changed. Set up its dependencies from README.md first.'
                });
            });
            if (hasCloud) pipeSubDefs.push({ id: 'cloud', label: 'Cloud Pipeline', yaml: pipelineCloud, file: 'pipeline-cloud.yaml', desc: 'Cloud-scheduled pipeline. Its input needs nothing from your terminal, so it can run on a remote edge node. Start here for a first run against Expanso Cloud.' });
            if (hasCli) pipeSubDefs.push({ id: 'cli', label: 'CLI Pipeline', yaml: pipelineCli, file: 'pipeline-cli.yaml', desc: 'Standalone pipeline. Reads from stdin, processes data, outputs to stdout. A Cloud-scheduled job has no stdin connected to your terminal, so this variant cannot receive your input on a remote node as written.' });
            if (hasMcp) pipeSubDefs.push({ id: 'mcp', label: 'MCP Pipeline', yaml: pipelineMcp, file: 'pipeline-mcp.yaml', desc: 'HTTP server pipeline for MCP integration. Exposes an endpoint for AI assistants.' });

            pipeSubDefs.forEach(function(sub, idx) {
                var btn = document.createElement('button');
                btn.className = 'pipeline-sub-tab' + (idx === 0 ? ' active' : '');
                btn.textContent = sub.label;
                btn.addEventListener('click', function() {
                    pipeSubNav.querySelectorAll('.pipeline-sub-tab').forEach(function(t) { t.classList.remove('active'); });
                    btn.classList.add('active');
                    Object.keys(pipeSubContents).forEach(function(k) {
                        pipeSubContents[k].style.display = k === sub.id ? 'block' : 'none';
                    });
                });
                pipeSubNav.appendChild(btn);
            });

            pipelineContent.appendChild(pipeSubNav);

            pipeSubDefs.forEach(function(sub, idx) {
                var subDiv = document.createElement('div');
                subDiv.style.display = idx === 0 ? 'block' : 'none';
                pipeSubContents[sub.id] = subDiv;

                // ── Copy banner ──
                var banner = document.createElement('div');
                banner.className = 'copy-pipeline-banner';

                var bannerLeft = document.createElement('div');
                bannerLeft.className = 'copy-banner-text';

                var bannerIcon = document.createElement('span');
                bannerIcon.className = 'copy-banner-icon';
                bannerIcon.textContent = '📋';
                bannerLeft.appendChild(bannerIcon);

                var bannerInfo = document.createElement('div');
                var bannerTitle = document.createElement('div');
                bannerTitle.className = 'copy-banner-title';
                var status = variantStatus(skillName, sub.id);
                var rejected = !!status && !status.validates;
                var cloudUntested = sub.job && skill.proof && skill.proof.status !== 'executed-cloud-and-local';
                bannerTitle.textContent = rejected ? 'Rejected by the local validator'
                    : (cloudUntested ? 'Deploy to Expanso Cloud (untested there)' : 'Deploy to Expanso Cloud');
                var bannerSub = document.createElement('div');
                bannerSub.className = 'copy-banner-subtitle';
                bannerSub.textContent = rejected
                    ? 'Fix the validation error below before deploying this pipeline.'
                    : 'Copy this pipeline, validate it, then deploy it to your control plane.';
                bannerInfo.appendChild(bannerTitle);
                bannerInfo.appendChild(bannerSub);
                bannerLeft.appendChild(bannerInfo);

                var copyBtn = document.createElement('button');
                copyBtn.className = 'copy-pipeline-btn';
                copyBtn.textContent = 'Copy Full Pipeline';
                copyBtn.addEventListener('click', function() {
                    copyToClipboard(sub.yaml, copyBtn).then(function() {
                        copyBtn.textContent = '✅ Copied!';
                        copyBtn.classList.add('copied-state');
                        setTimeout(function() {
                            copyBtn.textContent = 'Copy Full Pipeline';
                            copyBtn.classList.remove('copied-state');
                        }, 2500);
                    });
                });

                banner.appendChild(bannerLeft);
                banner.appendChild(copyBtn);
                subDiv.appendChild(banner);

                // Description
                var descEl = document.createElement('p');
                descEl.className = 'pipeline-description';
                descEl.textContent = sub.desc;
                subDiv.appendChild(descEl);

                // Readiness, from validation-report.json
                var readinessEl = document.createElement('p');
                readinessEl.className = 'readiness-note' + (status && status.validates ? '' : ' readiness-warn');
                var validatorVersion = validationReport && validationReport.validator ? validationReport.validator.version : '';
                if (!status) {
                    readinessEl.textContent = 'Validation status unknown. Run both validators below before deploying. Not confirmed by an end-to-end run.';
                } else if (status.validates && sub.job && skill.proof) {
                    readinessEl.textContent = 'Passes local validation (expanso-edge validate ' + validatorVersion + '). ' + proofSummary(skill.proof);
                } else if (status.validates) {
                    readinessEl.textContent = 'Passes local validation (expanso-edge validate ' + validatorVersion + '). Not confirmed by an end-to-end run on Expanso Cloud.';
                } else {
                    readinessEl.textContent = 'Rejected by expanso-edge validate ' + validatorVersion + ': ' + (status.error || 'see validation-report.json');
                }
                subDiv.appendChild(readinessEl);

                // Code block
                subDiv.appendChild(createCodeBlock(sub.yaml, 'yaml'));

                // Deploy section
                var deployDiv = document.createElement('div');
                deployDiv.className = 'modal-section';
                var deployH3 = document.createElement('h3');
                deployH3.textContent = 'Deploy';
                deployDiv.appendChild(deployH3);

                if (rejected) {
                    var blocked = document.createElement('p');
                    blocked.className = 'readiness-note readiness-warn';
                    blocked.textContent = 'No deploy command is shown for this pipeline because the local validator rejects it. A deploy could still be accepted and stored, but the job is known not to be valid.';
                    deployDiv.appendChild(blocked);
                } else {
                    var skillUrl = getSkillUrl(skillName, sub.file);
                    var deployCmd =
                        '# Requires: a saved Cloud profile and a connected edge node.\n' +
                        '# expanso-cli job deploy reads a FILE path or \'-\', not a URL.\n' +
                        'curl -fsSL -O ' + skillUrl + '\n' +
                        (sub.job ? '# Set up its dependencies first (README.md), and edit the\n' +
                            '# values listed in the job spec\'s header comment.\n' +
                            'curl -fsSL -O ' + getSkillUrl(skillName, 'README.md') + '\n' : '') +
                        '# Run both validators; job validate accepts files edge rejects.\n' +
                        'expanso-edge validate ' + sub.file + '\n' +
                        'expanso-cli job validate ' + sub.file + ' --offline\n' +
                        'expanso-cli job deploy ' + sub.file + '\n\n' +
                        '# Deploying stores the job; it does not prove it ran.\n' +
                        '# Confirm the control plane actually scheduled and executed it:\n' +
                        'expanso-cli job describe <job-name>\n' +
                        'expanso-cli execution list --job-id <job-id>';
                    deployDiv.appendChild(createCodeBlock(deployCmd, 'bash'));
                }

                subDiv.appendChild(deployDiv);

                pipelineContent.appendChild(subDiv);
            });
        }

        modalContent.appendChild(pipelineContent);

        // ── Footer actions ──
        var actionsDiv = document.createElement('div');
        actionsDiv.className = 'modal-actions';

        var githubLink = document.createElement('a');
        githubLink.href = 'https://github.com/expanso-io/skills.expanso.io/tree/main/skills/' + skill.category + '/' + skillName;
        githubLink.target = '_blank';
        githubLink.rel = 'noopener';
        githubLink.className = 'btn btn-primary';
        githubLink.textContent = 'View Source';
        actionsDiv.appendChild(githubLink);

        modalContent.appendChild(actionsDiv);
    }

    // ── SEO Helpers ─────────────────────────────────────────

    var defaultTitle = document.title;
    var defaultDescription = document.querySelector('meta[name="description"]').getAttribute('content');

    function updateMetaTags(skillName, skill) {
        var prettyName = skillName.replace(/-/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); });
        var category = skill.category.charAt(0).toUpperCase() + skill.category.slice(1);
        var title = prettyName + ' \u2013 ' + category + ' Skill | Expanso Skills';
        var desc = skill.description || '';
        var suffix = ' Install and deploy with Expanso.';
        if (desc.length + suffix.length <= 160) desc = desc + suffix;
        else if (desc.length > 160) desc = desc.substring(0, 157) + '...';
        var canonical = 'https://skills.expanso.io/skill/' + skillName + '/';

        document.title = title;
        setMetaContent('name', 'description', desc);
        setMetaContent('property', 'og:title', title);
        setMetaContent('property', 'og:description', desc);
        setMetaContent('property', 'og:url', canonical);
        setMetaContent('name', 'twitter:title', title);
        setMetaContent('name', 'twitter:description', desc);
        var link = document.querySelector('link[rel="canonical"]');
        if (link) link.setAttribute('href', canonical);
    }

    function resetMetaTags() {
        document.title = defaultTitle;
        setMetaContent('name', 'description', defaultDescription);
        setMetaContent('property', 'og:title', defaultTitle);
        setMetaContent('property', 'og:description', defaultDescription);
        setMetaContent('property', 'og:url', 'https://skills.expanso.io/');
        setMetaContent('name', 'twitter:title', defaultTitle);
        setMetaContent('name', 'twitter:description', defaultDescription);
        var link = document.querySelector('link[rel="canonical"]');
        if (link) link.setAttribute('href', 'https://skills.expanso.io/');
    }

    function setMetaContent(attr, name, content) {
        var el = document.querySelector('meta[' + attr + '="' + name + '"]');
        if (el) el.setAttribute('content', content);
    }

    // ── Helpers ──────────────────────────────────────────────

    function createCodeBlock(code, language) {
        var wrapper = document.createElement('div');
        wrapper.className = 'code-block';

        var pre = document.createElement('pre');
        var codeEl = document.createElement('code');
        codeEl.className = 'language-' + language;
        codeEl.textContent = code;
        pre.appendChild(codeEl);

        var copyBtn = createCopyButton(code);
        copyBtn.className = 'copy-btn code-copy-btn';

        wrapper.appendChild(pre);
        wrapper.appendChild(copyBtn);
        return wrapper;
    }

    function createTableSection(title, headers, rows, codeColumns) {
        var section = document.createElement('div');
        section.className = 'modal-section';

        var h3 = document.createElement('h3');
        h3.textContent = title;
        section.appendChild(h3);

        var table = document.createElement('table');
        table.className = 'modal-table';

        var thead = document.createElement('thead');
        var headerRow = document.createElement('tr');
        headers.forEach(function(header) {
            var th = document.createElement('th');
            th.textContent = header;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        var tbody = document.createElement('tbody');
        rows.forEach(function(row) {
            var tr = document.createElement('tr');
            row.forEach(function(cell, index) {
                var td = document.createElement('td');
                if (codeColumns && codeColumns[index]) {
                    var code = document.createElement('code');
                    code.textContent = cell;
                    td.appendChild(code);
                } else {
                    td.textContent = cell;
                }
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);

        section.appendChild(table);
        return section;
    }

    function createCopyButton(text) {
        var button = document.createElement('button');
        button.className = 'copy-btn';
        button.dataset.copy = text;
        button.title = 'Copy to clipboard';

        var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '16');
        svg.setAttribute('height', '16');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
        svg.setAttribute('stroke-width', '2');

        var rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', '9');
        rect.setAttribute('y', '9');
        rect.setAttribute('width', '13');
        rect.setAttribute('height', '13');
        rect.setAttribute('rx', '2');
        rect.setAttribute('ry', '2');

        var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1');

        svg.appendChild(rect);
        svg.appendChild(path);
        button.appendChild(svg);
        return button;
    }

    function closeModal(skipPush) {
        modalOverlay.classList.remove('active');
        document.body.style.overflow = '';
        if (!skipPush) history.pushState({}, '', '/');
        resetMetaTags();
    }

    async function copyToClipboard(text, button) {
        try {
            await navigator.clipboard.writeText(text);
            if (button) {
                button.classList.add('copied');
                var originalTitle = button.title;
                button.title = 'Copied!';
                setTimeout(function() {
                    button.classList.remove('copied');
                    button.title = originalTitle;
                }, 1500);
            }
        } catch (err) {
            // Fallback
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        }
    }

    function debounce(fn, delay) {
        var timeoutId;
        return function() {
            var context = this, args = arguments;
            clearTimeout(timeoutId);
            timeoutId = setTimeout(function() { fn.apply(context, args); }, delay);
        };
    }

    init();
})();
