(function (global) {
  'use strict';

  var DEFAULT_STORAGE_KEY = 'preset-switcher';
  var VALID_POSITIONS = ['bottom-right', 'bottom-left', 'top-right', 'top-left'];

  function validCombo(axes, candidate) {
    var combo = {};
    Object.keys(axes).forEach(function (key) {
      var options = Array.isArray(axes[key].options) ? axes[key].options : [];
      var requested = candidate && candidate[key];
      if (axes[key].allowDefault === true && requested === '') {
        combo[key] = '';
        return;
      }
      var match = options.find(function (option) { return option.id === requested; });
      if (match) combo[key] = match.id;
    });
    return combo;
  }

  function defaultCombo(axes) {
    var combo = {};
    Object.keys(axes).forEach(function (key) {
      var options = Array.isArray(axes[key].options) ? axes[key].options : [];
      if (axes[key].allowDefault === true) combo[key] = '';
      else if (options.length) combo[key] = options[0].id;
    });
    return combo;
  }

  function applyCombo(combo) {
    Object.keys(combo).forEach(function (key) {
      if (combo[key] === '') document.documentElement.removeAttribute('data-' + key.replace(/[A-Z]/g, function (letter) { return '-' + letter.toLowerCase(); }));
      else document.documentElement.dataset[key] = combo[key];
    });
  }

  function readStorage(key) {
    try {
      return JSON.parse(global.localStorage.getItem(key) || '{}');
    } catch (error) {
      return {};
    }
  }

  function writeStorage(key, combo) {
    try {
      global.localStorage.setItem(key, JSON.stringify(combo));
    } catch (error) {
      // Selection still works when storage is unavailable.
    }
  }

  function readAxisStorage(key, axes) {
    var combo = {};
    Object.keys(axes).forEach(function (axisKey) {
      try {
        var value = global.localStorage.getItem(key + ':' + axisKey);
        if (value !== null) combo[axisKey] = value;
      } catch (error) {
        // Defaults still work when storage is unavailable.
      }
    });
    return combo;
  }

  function writeAxisStorage(key, combo) {
    Object.keys(combo).forEach(function (axisKey) {
      try {
        global.localStorage.setItem(key + ':' + axisKey, combo[axisKey]);
      } catch (error) {
        // Selection still works when storage is unavailable.
      }
    });
  }

  function readHash() {
    var combo = {};
    new URLSearchParams(global.location.hash.slice(1)).forEach(function (value, key) {
      combo[key] = value;
    });
    return combo;
  }

  function writeHash(combo) {
    var params = new URLSearchParams();
    Object.keys(combo).forEach(function (key) {
      if (combo[key] !== '') params.set(key, combo[key]);
    });
    global.history.replaceState(null, '', global.location.pathname + global.location.search + '#' + params.toString());
  }

  function lockedOutput(combo) {
    var attributes = Object.keys(combo).map(function (key) {
      if (combo[key] === '') return '';
      return 'data-' + key.replace(/[A-Z]/g, function (letter) { return '-' + letter.toLowerCase(); }) + '="' + combo[key].replace(/&/g, '&amp;').replace(/"/g, '&quot;') + '"';
    }).filter(Boolean).join(' ');
    return 'LOCKED COMBO\n\nHTML attributes:\n' + attributes + '\n\nJSON:\n' + JSON.stringify(combo, null, 2);
  }

  function showLockedOutput(output) {
    var readout = document.createElement('div');
    readout.className = 'preset-switcher-lock-readout';
    readout.setAttribute('role', 'status');

    var title = document.createElement('strong');
    title.textContent = 'Combo locked';
    var pre = document.createElement('pre');
    pre.textContent = output;
    var close = document.createElement('button');
    close.type = 'button';
    close.textContent = 'Close';
    close.addEventListener('click', function () { readout.remove(); });

    readout.appendChild(title);
    readout.appendChild(pre);
    readout.appendChild(close);
    document.body.appendChild(readout);
  }

  function render(options, combo, theme, onChange, onTheme, onLock) {
    var panel = document.createElement('aside');
    panel.className = 'preset-switcher preset-switcher--' + options.position;
    panel.setAttribute('aria-label', 'Design preset selector');

    var toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'preset-switcher__toggle';
    toggle.textContent = 'Design presets';

    // Panel starts collapsed below 720px so it doesn't overlay the deck on phones.
    // At wider viewports it opens by default and the user can collapse it.
    var collapsed = global.matchMedia && global.matchMedia('(max-width: 719px)').matches;
    if (collapsed) {
      panel.classList.add('is-collapsed');
      toggle.setAttribute('aria-expanded', 'false');
    } else {
      toggle.setAttribute('aria-expanded', 'true');
    }

    var body = document.createElement('div');
    body.className = 'preset-switcher__body';
    Object.keys(options.axes).forEach(function (axisKey) {
      var axis = options.axes[axisKey];
      var group = document.createElement('fieldset');
      group.className = 'preset-switcher__axis';
      var legend = document.createElement('legend');
      legend.textContent = axis.label || axisKey;
      group.appendChild(legend);
      if (axis.renderAs === 'select') {
        var select = document.createElement('select');
        select.className = 'preset-switcher__select';
        select.dataset.axis = axisKey;
        select.setAttribute('aria-label', axis.label || axisKey);
        if (axis.allowDefault === true) {
          var defaultOption = document.createElement('option');
          defaultOption.value = '';
          defaultOption.textContent = axis.defaultLabel || 'Default';
          select.appendChild(defaultOption);
        }
        axis.options.forEach(function (option) {
          var item = document.createElement('option');
          item.value = option.id;
          item.textContent = option.label || option.id;
          select.appendChild(item);
        });
        select.value = combo[axisKey] || '';
        select.addEventListener('change', function () { onChange(axisKey, select.value, panel); });
        group.appendChild(select);
      } else {
        var segments = document.createElement('div');
        segments.className = 'preset-switcher__segments';
        axis.options.forEach(function (option) {
          var button = document.createElement('button');
          button.type = 'button';
          button.textContent = option.label || option.id;
          button.dataset.axis = axisKey;
          button.dataset.option = option.id;
          button.setAttribute('aria-pressed', String(combo[axisKey] === option.id));
          button.addEventListener('click', function () { onChange(axisKey, option.id, panel); });
          segments.appendChild(button);
        });
        group.appendChild(segments);
      }
      body.appendChild(group);
    });

    if (options.themeToggle) {
      var themeButton = document.createElement('button');
      themeButton.type = 'button';
      themeButton.className = 'preset-switcher__theme';
      themeButton.addEventListener('click', function () { onTheme(themeButton); });
      updateThemeButton(themeButton, theme);
      body.appendChild(themeButton);
    }

    var lock = document.createElement('button');
    lock.type = 'button';
    lock.className = 'preset-switcher__lock';
    lock.textContent = 'Lock this combo';
    lock.addEventListener('click', function () { onLock(panel); });
    body.appendChild(lock);

    toggle.addEventListener('click', function () {
      var collapsed = panel.classList.toggle('is-collapsed');
      toggle.setAttribute('aria-expanded', String(!collapsed));
    });
    panel.appendChild(toggle);
    panel.appendChild(body);
    document.body.appendChild(panel);
    return panel;
  }

  function updateThemeButton(button, theme) {
    var dark = theme === 'dark';
    button.textContent = dark ? 'Light mode' : 'Dark mode';
    button.setAttribute('aria-pressed', String(dark));
    button.setAttribute('aria-label', 'Switch to ' + (dark ? 'light' : 'dark') + ' theme');
  }

  var PresetSwitcher = {
    init: function (config) {
      config = config || {};
      var axes = config.axes || {};
      var locked = config.mode === 'locked';
      var storageKey = config.storageKey || DEFAULT_STORAGE_KEY;
      var explicitPersistence = Object.prototype.hasOwnProperty.call(config, 'persist');
      var persist = config.persist !== false;
      var useHash = config.useHash === true;
      var position = VALID_POSITIONS.indexOf(config.position) >= 0 ? config.position : 'bottom-right';
      var combo;

      if (locked) {
        combo = validCombo(axes, config.combo || {});
        applyCombo(combo);
        return { combo: combo, panel: null };
      }

      var saved = persist ? (explicitPersistence ? readAxisStorage(storageKey, axes) : readStorage(storageKey)) : {};
      combo = Object.assign(defaultCombo(axes), validCombo(axes, saved));
      if (useHash && global.location.hash.length > 1) {
        combo = Object.assign(combo, validCombo(axes, readHash()));
      }
      applyCombo(combo);
      if (persist) {
        if (explicitPersistence) writeAxisStorage(storageKey, combo);
        else writeStorage(storageKey, combo);
      }
      if (useHash) writeHash(combo);

      var theme = document.documentElement.dataset.theme;
      if (config.themeToggle === true) {
        if (theme !== 'light' && theme !== 'dark') {
          try { theme = global.localStorage.getItem(storageKey + ':theme'); } catch (error) { theme = ''; }
        }
        if (theme !== 'light' && theme !== 'dark') theme = global.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        document.documentElement.dataset.theme = theme;
      }

      var api = { combo: combo, panel: null };
      function change(axisKey, optionId, panel) {
        combo[axisKey] = optionId;
        applyCombo((function () { var changed = {}; changed[axisKey] = optionId; return changed; })());
        panel.querySelectorAll('button[data-axis="' + axisKey + '"]').forEach(function (button) {
          button.setAttribute('aria-pressed', String(button.dataset.option === optionId));
        });
        var select = panel.querySelector('select[data-axis="' + axisKey + '"]');
        if (select) select.value = optionId;
        if (persist) {
          if (explicitPersistence) writeAxisStorage(storageKey, combo);
          else writeStorage(storageKey, combo);
        }
        if (useHash) writeHash(combo);
      }
      function changeTheme(button) {
        theme = theme === 'dark' ? 'light' : 'dark';
        document.documentElement.dataset.theme = theme;
        if (persist) {
          try { global.localStorage.setItem(storageKey + ':theme', theme); } catch (error) {}
        }
        updateThemeButton(button, theme);
      }
      function lock(panel) {
        var snapshot = Object.assign({}, combo);
        applyCombo(snapshot);
        var output = lockedOutput(snapshot);
        console.log(output);
        showLockedOutput(output);
        panel.remove();
        api.panel = null;
        api.combo = snapshot;
      }

      function mount() {
        api.panel = render({ axes: axes, position: position, themeToggle: config.themeToggle === true }, combo, theme, change, changeTheme, lock);
      }
      if (document.body) mount();
      else document.addEventListener('DOMContentLoaded', mount, { once: true });
      return api;
    }
  };

  global.PresetSwitcher = PresetSwitcher;
})(window);
