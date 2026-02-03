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
    var filteredSkills = [];
    var currentCategory = 'all';
    var searchQuery = '';
    var filterLocal = false;
    var filterNoCreds = false;

    // Base URL for skills - served directly from this site
    var SKILLS_BASE = window.location.origin;
    // Fallback to GitHub for local development
    var GITHUB_RAW_BASE = 'https://raw.githubusercontent.com/expanso-io/expanso-skills/main';

    // DOM Elements
    var skillsGrid = document.getElementById('skills-grid');
    var searchInput = document.getElementById('search');
    var skillCountEl = document.getElementById('skill-count');
    var modalOverlay = document.getElementById('modal-overlay');
    var modalContent = document.getElementById('modal-content');
    var categoryTabs = document.querySelectorAll('.tab[data-category]');
    var filterLocalCheckbox = document.getElementById('filter-local');
    var filterNoCredsCheckbox = document.getElementById('filter-no-creds');

    // Category colors for badges
    var categoryColors = {
        ai: 'badge-ai',
        security: 'badge-security',
        transforms: 'badge-transforms',
        utilities: 'badge-utilities',
        workflows: 'badge-workflows'
    };

    // Initialize
    async function init() {
        try {
            await loadCatalog();
            bindEvents();
            filterAndRender();
        } catch (error) {
            console.error('Failed to initialize:', error);
            showNoResults('Failed to load skills. Please refresh the page.');
        }
    }

    // Load catalog from GitHub or local
    async function loadCatalog() {
        var urls = [
            'catalog.json',
            '../catalog.json',
            GITHUB_RAW_BASE + '/catalog.json'
        ];

        for (var i = 0; i < urls.length; i++) {
            try {
                var response = await fetch(urls[i]);
                if (response.ok) {
                    catalog = await response.json();
                    skillCountEl.textContent = String(catalog.total_skills);
                    return;
                }
            } catch (e) {
                continue;
            }
        }

        throw new Error('Could not load catalog from any source');
    }

    // Fetch a file from the skill directory
    // Flat structure: skills.expanso.io/<name>/<file>
    // Fall back to GitHub (with category) for dev
    async function fetchSkillFile(skillName, filename, category) {
        var urls = [
            SKILLS_BASE + '/' + skillName + '/' + filename,
            GITHUB_RAW_BASE + '/skills/' + category + '/' + skillName + '/' + filename
        ];

        for (var i = 0; i < urls.length; i++) {
            try {
                var response = await fetch(urls[i]);
                if (response.ok) {
                    return await response.text();
                }
            } catch (e) {
                continue;
            }
        }
        console.warn('Could not fetch ' + filename + ' for ' + skillName);
        return null;
    }

    // Get the public URL for a skill file (for users to copy/deploy)
    // Flat structure: skills.expanso.io/<name>/<file>
    function getSkillUrl(skillName, filename) {
        return 'https://skills.expanso.io/' + skillName + '/' + filename;
    }

    // Bind event listeners
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

        document.addEventListener('click', function(e) {
            var copyBtn = e.target.closest('.copy-btn');
            if (copyBtn) {
                var text = copyBtn.dataset.copy;
                if (text) {
                    copyToClipboard(text, copyBtn);
                }
            }
        });
    }

    // Filter skills based on current state
    function filterAndRender() {
        if (!catalog) return;

        var skills = Object.entries(catalog.skills);

        filteredSkills = skills.filter(function(entry) {
            var name = entry[0];
            var skill = entry[1];

            if (currentCategory !== 'all' && skill.category !== currentCategory) {
                return false;
            }

            if (searchQuery) {
                var searchStr = (name + ' ' + skill.description).toLowerCase();
                if (!searchStr.includes(searchQuery)) {
                    return false;
                }
            }

            if (filterLocal) {
                var hasLocal = skill.backends.some(function(b) {
                    return b === 'local' || b === 'ollama';
                });
                if (!hasLocal) return false;
            }

            if (filterNoCreds) {
                var requiredCreds = skill.credentials.filter(function(c) {
                    return c.required;
                });
                if (requiredCreds.length > 0) return false;
            }

            return true;
        });

        renderSkills();
    }

    function showNoResults(message) {
        while (skillsGrid.firstChild) {
            skillsGrid.removeChild(skillsGrid.firstChild);
        }
        var div = document.createElement('div');
        div.className = 'no-results';
        div.textContent = message;
        skillsGrid.appendChild(div);
    }

    function renderSkills() {
        while (skillsGrid.firstChild) {
            skillsGrid.removeChild(skillsGrid.firstChild);
        }

        if (filteredSkills.length === 0) {
            showNoResults('No skills found matching your criteria.');
            return;
        }

        filteredSkills.forEach(function(entry) {
            var name = entry[0];
            var skill = entry[1];
            var card = createSkillCard(name, skill);
            skillsGrid.appendChild(card);
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

        var badges = document.createElement('div');
        badges.className = 'skill-badges';

        var categoryBadge = document.createElement('span');
        categoryBadge.className = 'badge ' + (categoryColors[skill.category] || '');
        categoryBadge.textContent = skill.category;
        badges.appendChild(categoryBadge);

        var isLocal = skill.backends.some(function(b) {
            return b === 'local' || b === 'ollama';
        });
        if (isLocal) {
            var localBadge = document.createElement('span');
            localBadge.className = 'badge badge-local';
            localBadge.textContent = 'local';
            badges.appendChild(localBadge);
        }

        header.appendChild(nameSpan);
        header.appendChild(badges);

        var desc = document.createElement('p');
        desc.className = 'skill-description';
        desc.textContent = skill.description;

        var meta = document.createElement('div');
        meta.className = 'skill-meta';

        var inputs = document.createElement('div');
        inputs.className = 'skill-inputs';
        var displayInputs = skill.inputs.slice(0, 2);
        displayInputs.forEach(function(input) {
            var tag = document.createElement('span');
            tag.className = 'input-tag';
            tag.textContent = input.name;
            inputs.appendChild(tag);
        });
        if (skill.inputs.length > 2) {
            var moreTag = document.createElement('span');
            moreTag.className = 'input-tag';
            moreTag.textContent = '+' + (skill.inputs.length - 2);
            inputs.appendChild(moreTag);
        }

        var backends = document.createElement('div');
        backends.className = 'skill-backends';
        skill.backends.forEach(function(b) {
            var icon = document.createElement('span');
            icon.className = 'backend-icon';
            icon.title = b;
            icon.textContent = getBackendIcon(b);
            backends.appendChild(icon);
        });

        meta.appendChild(inputs);
        meta.appendChild(backends);

        article.appendChild(header);
        article.appendChild(desc);
        article.appendChild(meta);

        article.addEventListener('click', function() {
            openModal(name);
        });

        return article;
    }

    function getBackendIcon(backend) {
        var icons = {
            openai: 'AI',
            ollama: 'OL',
            local: 'L',
            remote: 'R'
        };
        return icons[backend] || backend.charAt(0).toUpperCase();
    }

    // Open modal with skill details and fetch documentation + pipelines
    async function openModal(skillName) {
        var skill = catalog.skills[skillName];
        if (!skill) return;

        // Clear and show loading
        while (modalContent.firstChild) {
            modalContent.removeChild(modalContent.firstChild);
        }

        var loadingDiv = document.createElement('div');
        loadingDiv.className = 'modal-loading';
        loadingDiv.textContent = 'Loading skill details...';
        modalContent.appendChild(loadingDiv);

        modalOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';

        // Fetch files in parallel (pass category for GitHub fallback)
        var fetchPromises = [
            fetchSkillFile(skillName, 'README.md', skill.category),
            fetchSkillFile(skillName, 'pipeline-cli.yaml', skill.category),
            fetchSkillFile(skillName, 'pipeline-mcp.yaml', skill.category),
            fetchSkillFile(skillName, 'skill.yaml', skill.category)
        ];

        var results = await Promise.all(fetchPromises);
        var readme = results[0];
        var pipelineCli = results[1];
        var pipelineMcp = results[2];
        var skillYaml = results[3];

        // Clear loading
        while (modalContent.firstChild) {
            modalContent.removeChild(modalContent.firstChild);
        }

        // Build modal content
        buildModalContent(skillName, skill, readme, pipelineCli, pipelineMcp, skillYaml);

        // Apply syntax highlighting
        if (window.Prism) {
            Prism.highlightAllUnder(modalContent);
        }
    }

    function buildModalContent(skillName, skill, readme, pipelineCli, pipelineMcp, skillYaml) {
        // Header
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

        var verBadge = document.createElement('span');
        verBadge.className = 'badge';
        verBadge.style.background = 'var(--bg-tertiary)';
        verBadge.style.color = 'var(--text-secondary)';
        verBadge.textContent = 'v' + skill.version;

        badgesDiv.appendChild(catBadge);
        badgesDiv.appendChild(verBadge);

        // Add backend badges
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

        // Tab navigation for different views
        var tabNav = document.createElement('div');
        tabNav.className = 'modal-tabs';

        var tabs = [
            { id: 'overview', label: 'Overview' },
            { id: 'cli-pipeline', label: 'CLI Pipeline' },
            { id: 'mcp-pipeline', label: 'MCP Pipeline' }
        ];

        var tabContents = {};

        tabs.forEach(function(tab, index) {
            var tabBtn = document.createElement('button');
            tabBtn.className = 'modal-tab' + (index === 0 ? ' active' : '');
            tabBtn.textContent = tab.label;
            tabBtn.dataset.tab = tab.id;
            tabBtn.addEventListener('click', function() {
                // Update active tab
                tabNav.querySelectorAll('.modal-tab').forEach(function(t) {
                    t.classList.remove('active');
                });
                tabBtn.classList.add('active');

                // Show corresponding content
                Object.keys(tabContents).forEach(function(key) {
                    tabContents[key].style.display = key === tab.id ? 'block' : 'none';
                });
            });
            tabNav.appendChild(tabBtn);
        });

        modalContent.appendChild(tabNav);

        // Overview tab content
        var overviewContent = document.createElement('div');
        overviewContent.className = 'tab-content';
        tabContents['overview'] = overviewContent;

        // Inputs section
        if (skill.inputs.length > 0) {
            var inputsSection = createTableSection('Inputs', ['Name', 'Type', 'Required', 'Default'], skill.inputs.map(function(input) {
                return [
                    input.name,
                    input.type || 'any',
                    input.required ? 'Yes' : 'No',
                    input.default !== undefined ? JSON.stringify(input.default) : '-'
                ];
            }), [true, false, false, true]);
            overviewContent.appendChild(inputsSection);
        }

        // Outputs section
        if (skill.outputs.length > 0) {
            var outputsSection = createTableSection('Outputs', ['Name', 'Type', 'Description'], skill.outputs.map(function(output) {
                return [
                    output.name,
                    output.type || 'any',
                    output.description || ''
                ];
            }), [true, false, false]);
            overviewContent.appendChild(outputsSection);
        }

        // Credentials section
        if (skill.credentials.length > 0) {
            var credsSection = createTableSection('Credentials', ['Name', 'Required', 'Description'], skill.credentials.map(function(cred) {
                return [
                    cred.name,
                    cred.required ? 'Yes' : 'No',
                    cred.description || ''
                ];
            }), [true, false, false]);
            overviewContent.appendChild(credsSection);
        }

        // Deploy to Expanso Cloud section
        var deploySection = document.createElement('div');
        deploySection.className = 'modal-section';
        var deployH3 = document.createElement('h3');
        deployH3.textContent = 'Deploy to Expanso Cloud';
        deploySection.appendChild(deployH3);

        var deployDesc = document.createElement('p');
        deployDesc.className = 'deploy-description';
        deployDesc.textContent = 'Deploy this skill to your Expanso Cloud instance. It will run on your Expanso Edge nodes and be available to OpenClaw via MCP.';
        deploySection.appendChild(deployDesc);

        // CLI deploy command
        var cliLabel = document.createElement('div');
        cliLabel.className = 'field-label';
        cliLabel.textContent = 'Deploy via CLI';
        deploySection.appendChild(cliLabel);

        var cliCommand = '# Set your Expanso Cloud endpoint\nexport EXPANSO_CLI_ENDPOINT="https://your-instance.us1.cloud.expanso.io"\n\n# Deploy the skill\nexpanso-cli job deploy ' + getSkillUrl(skillName, 'pipeline-cli.yaml');

        var cliCode = createCodeBlock(cliCommand, 'bash');
        deploySection.appendChild(cliCode);

        // Cloud UI instructions
        var cloudLabel = document.createElement('div');
        cloudLabel.className = 'field-label';
        cloudLabel.textContent = 'Deploy via Cloud UI';
        deploySection.appendChild(cloudLabel);

        var cloudInstructions = document.createElement('ol');
        cloudInstructions.className = 'cloud-instructions';
        var steps = [
            'Open cloud.expanso.io and sign in',
            'Navigate to Pipelines → Add Pipeline',
            'Paste the Pipeline URL above',
            'Configure any required credentials',
            'Deploy to your Edge nodes'
        ];
        steps.forEach(function(step) {
            var li = document.createElement('li');
            li.textContent = step;
            cloudInstructions.appendChild(li);
        });
        deploySection.appendChild(cloudInstructions);

        overviewContent.appendChild(deploySection);

        // Skill.yaml section
        if (skillYaml) {
            var skillYamlSection = document.createElement('div');
            skillYamlSection.className = 'modal-section';
            var skillYamlH3 = document.createElement('h3');
            skillYamlH3.textContent = 'Skill Definition (skill.yaml)';
            skillYamlSection.appendChild(skillYamlH3);
            var skillYamlCode = createCodeBlock(skillYaml, 'yaml');
            skillYamlSection.appendChild(skillYamlCode);
            overviewContent.appendChild(skillYamlSection);
        }

        modalContent.appendChild(overviewContent);

        // CLI Pipeline tab content
        var cliContent = document.createElement('div');
        cliContent.className = 'tab-content';
        cliContent.style.display = 'none';
        tabContents['cli-pipeline'] = cliContent;

        if (pipelineCli) {
            var cliDesc = document.createElement('p');
            cliDesc.className = 'pipeline-description';
            cliDesc.textContent = 'Standalone CLI pipeline. Reads from stdin, processes data, outputs to stdout.';
            cliContent.appendChild(cliDesc);

            var cliCodeBlock = createCodeBlock(pipelineCli, 'yaml');
            cliContent.appendChild(cliCodeBlock);
        } else {
            var noCliMsg = document.createElement('p');
            noCliMsg.className = 'no-content';
            noCliMsg.textContent = 'CLI pipeline not available for this skill.';
            cliContent.appendChild(noCliMsg);
        }

        modalContent.appendChild(cliContent);

        // MCP Pipeline tab content
        var mcpContent = document.createElement('div');
        mcpContent.className = 'tab-content';
        mcpContent.style.display = 'none';
        tabContents['mcp-pipeline'] = mcpContent;

        if (pipelineMcp) {
            var mcpDesc = document.createElement('p');
            mcpDesc.className = 'pipeline-description';
            mcpDesc.textContent = 'HTTP server pipeline for MCP integration. Exposes an endpoint for AI assistants.';
            mcpContent.appendChild(mcpDesc);

            var mcpCodeBlock = createCodeBlock(pipelineMcp, 'yaml');
            mcpContent.appendChild(mcpCodeBlock);
        } else {
            var noMcpMsg = document.createElement('p');
            noMcpMsg.className = 'no-content';
            noMcpMsg.textContent = 'MCP pipeline not available for this skill.';
            mcpContent.appendChild(noMcpMsg);
        }

        modalContent.appendChild(mcpContent);

        // Actions
        var actionsDiv = document.createElement('div');
        actionsDiv.className = 'modal-actions';

        var githubLink = document.createElement('a');
        githubLink.href = 'https://github.com/expanso-io/expanso-skills/tree/main/skills/' + skill.category + '/' + skillName;
        githubLink.target = '_blank';
        githubLink.rel = 'noopener';
        githubLink.className = 'btn btn-primary';
        githubLink.textContent = 'View Source';

        actionsDiv.appendChild(githubLink);
        modalContent.appendChild(actionsDiv);
    }

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

    function closeModal() {
        modalOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    async function copyToClipboard(text, button) {
        try {
            await navigator.clipboard.writeText(text);
            button.classList.add('copied');
            var originalTitle = button.title;
            button.title = 'Copied!';
            setTimeout(function() {
                button.classList.remove('copied');
                button.title = originalTitle;
            }, 1500);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    }

    function debounce(fn, delay) {
        var timeoutId;
        return function() {
            var context = this;
            var args = arguments;
            clearTimeout(timeoutId);
            timeoutId = setTimeout(function() {
                fn.apply(context, args);
            }, delay);
        };
    }

    init();
})();
