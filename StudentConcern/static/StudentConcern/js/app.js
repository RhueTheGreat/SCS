(function () {
  var LOAD_MS = 500;
  var loader = document.getElementById('loader');
  var loaderText = document.getElementById('loader-text');

  document.querySelectorAll('form[data-loading]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (form.dataset.submitting) return;
      e.preventDefault();
      form.dataset.submitting = 'true';
      loaderText.textContent = form.dataset.loading || 'Loading';
      loader.classList.add('active');
      setTimeout(function () { form.submit(); }, LOAD_MS);
    });
  });

  window.addEventListener('pageshow', function (e) {
    if (e.persisted) {
      loader.classList.remove('active');
      document.querySelectorAll('form[data-submitting]').forEach(function (f) { delete f.dataset.submitting; });
    }
  });

  document.querySelectorAll('form.filters select').forEach(function (select) {
    select.addEventListener('change', function () {
      if (select.form.requestSubmit) select.form.requestSubmit();
      else select.form.submit();
    });
  });

  document.querySelectorAll('textarea[data-counter]').forEach(function (ta) {
    var max = ta.getAttribute('maxlength');
    var out = ta.closest('.field').querySelector('.counter');
    if (!out || !max) return;
    function update() { out.textContent = ta.value.length + ' / ' + max; }
    ta.addEventListener('input', update);
    update();
  });

  document.querySelectorAll('.messages li').forEach(function (li) {
    function close() { li.classList.add('hide'); setTimeout(function () { li.remove(); }, 400); }
    var btn = li.querySelector('button');
    if (btn) btn.addEventListener('click', close);
    setTimeout(close, 4500);
  });

  var loginForm = document.querySelector('.login-form');
  if (loginForm) {
    var roleInput = loginForm.querySelector('#login-role');
    var setMode = function (mode) {
      loginForm.dataset.mode = mode;
      roleInput.value = mode;
      loginForm.querySelectorAll('.role-tab').forEach(function (tab) {
        tab.classList.toggle('active', tab.dataset.role === mode);
      });
      loginForm.querySelectorAll('[data-for]').forEach(function (group) {
        var show = group.dataset.for.split(' ').indexOf(mode) !== -1;
        group.hidden = !show;
        group.querySelectorAll('input, select').forEach(function (el) {
          el.disabled = !show;
          el.required = show;
        });
      });
    };
    document.querySelectorAll('[data-role]').forEach(function (btn) {
      btn.addEventListener('click', function () { setMode(btn.dataset.role); });
    });
    setMode(loginForm.dataset.mode || 'student');
  }

  document.querySelectorAll('input[type=file][name=evidence]').forEach(function (input) {
    var MAX = 5 * 1024 * 1024;
    var field = input.closest('.field');
    var box = field.querySelector('.preview');
    var img = box.querySelector('img');
    var help = field.querySelector('.help[data-default]');
    function reset(message) {
      box.hidden = true;
      img.removeAttribute('src');
      if (help) {
        help.textContent = message || help.dataset.default;
        help.classList.toggle('bad', !!message);
      }
    }
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      if (!file) { reset(); return; }
      if (file.type.indexOf('image/') !== 0) { input.value = ''; reset('Choose an image file.'); return; }
      if (file.size > MAX) { input.value = ''; reset('Image must be 5 MB or smaller.'); return; }
      reset();
      img.src = URL.createObjectURL(file);
      box.hidden = false;
    });
  });

  var lightbox = document.getElementById('lightbox');
  if (lightbox) {
    var lightboxImg = lightbox.querySelector('img');
    var closeLightbox = function () { lightbox.hidden = true; lightboxImg.removeAttribute('src'); };
    document.querySelectorAll('[data-lightbox]').forEach(function (el) {
      el.addEventListener('click', function () {
        lightboxImg.src = el.dataset.lightbox;
        lightbox.hidden = false;
      });
    });
    lightbox.addEventListener('click', function (e) { if (e.target !== lightboxImg) closeLightbox(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !lightbox.hidden) closeLightbox(); });
  }

  var accountForm = document.querySelector('form[data-account-form]');
  if (accountForm) {
    var roleSelect = accountForm.querySelector('select[name=role]');
    var idField = accountForm.querySelector('[data-field=StudentID]');
    var syncRole = function () {
      var isStudent = roleSelect.value === 'student';
      idField.hidden = !isStudent;
      idField.querySelector('input').disabled = !isStudent;
    };
    roleSelect.addEventListener('change', syncRole);
    syncRole();
  }

  var logTable = document.getElementById('log-table');
  if (logTable && logTable.dataset.live === '1') {
    var tbody = logTable.querySelector('tbody');
    var emptyBox = document.getElementById('log-empty');
    var lastId = parseInt(logTable.dataset.last, 10) || 0;
    var feedUrl = logTable.dataset.feed;
    var busy = false;

    var cell = function (label, text, asTag, extra) {
      var td = document.createElement('td');
      td.setAttribute('data-label', label);
      if (extra) td.className = extra;
      if (asTag) {
        var span = document.createElement('span');
        span.className = 'tag';
        span.textContent = text;
        td.appendChild(span);
      } else {
        td.textContent = text;
      }
      return td;
    };

    var addRow = function (r) {
      var tr = document.createElement('tr');
      tr.appendChild(cell('Time', r.time));
      tr.appendChild(cell('Student ID', r.student_id));
      tr.appendChild(cell('Full Name', r.name, false, 'name'));
      tr.appendChild(cell('Account Type', r.role, true));
      tr.appendChild(cell('Activity', r.action, true));
      tr.appendChild(cell('Details', r.detail));
      tr.appendChild(cell('IP', r.ip));
      tbody.insertBefore(tr, tbody.firstChild);
    };

    var poll = function () {
      if (busy || document.hidden) return;
      busy = true;
      var url = feedUrl + (feedUrl.indexOf('?') === feedUrl.length - 1 ? '' : '&') + 'after=' + lastId;
      fetch(url, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          data.rows.forEach(addRow);
          lastId = data.last_id;
          if (data.rows.length && emptyBox) emptyBox.hidden = true;
          while (tbody.rows.length > 100) tbody.deleteRow(-1);
        })
        .catch(function () {})
        .then(function () { busy = false; });
    };
    setInterval(poll, 2500);
  }


  var appScript = document.querySelector('script[data-heartbeat]');
  if (appScript) {
    function heartbeat() {
      if (document.hidden) return;
      var tokenInput = document.querySelector('input[name=csrfmiddlewaretoken]');
      var token = tokenInput ? tokenInput.value : '';
      fetch(appScript.dataset.heartbeat, {method:'POST', credentials:'same-origin', headers:{'X-CSRFToken':token, 'X-Requested-With':'XMLHttpRequest'}}).catch(function () {});
    }
    heartbeat(); setInterval(heartbeat, 30000);
  }

  var notificationNav = document.querySelector('[data-notifications]');
  if (notificationNav) {
    var previousCounts = null;
    var audioContext = null;
    document.addEventListener('pointerdown', function () {
      try { var Ctx = window.AudioContext || window.webkitAudioContext; if (Ctx && !audioContext) audioContext = new Ctx(); if (audioContext && audioContext.state === 'suspended') audioContext.resume(); } catch (e) {}
    }, { once: true });
    function beep() {
      try {
        var AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        audioContext = audioContext || new AudioCtx();
        if (audioContext.state === 'suspended') audioContext.resume();
        var oscillator = audioContext.createOscillator();
        var gain = audioContext.createGain();
        oscillator.type = 'sine'; oscillator.frequency.value = 880;
        gain.gain.setValueAtTime(0.0001, audioContext.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.12, audioContext.currentTime + 0.015);
        gain.gain.exponentialRampToValueAtTime(0.0001, audioContext.currentTime + 0.18);
        oscillator.connect(gain); gain.connect(audioContext.destination);
        oscillator.start(); oscillator.stop(audioContext.currentTime + 0.19);
      } catch (e) {}
    }
    var updateNotices = function () {
      if (document.hidden) return;
      fetch(notificationNav.dataset.notifications, {credentials:'same-origin', headers:{'X-Requested-With':'XMLHttpRequest'}})
        .then(function (r) { return r.json(); }).then(function (data) {
          var activeSection = notificationNav.dataset.active;
          var hasNew = false;
          Object.keys(data).forEach(function (key) {
            var count = Number(data[key]) || 0;
            if (previousCounts && count > (previousCounts[key] || 0)) hasNew = true;
            if (key === activeSection) count = 0;
            var badge = notificationNav.querySelector('[data-count="' + key + '"]');
            if (badge) { badge.textContent = count; badge.hidden = !count; }
          });
          if (hasNew && previousCounts) beep();
          previousCounts = data;
        }).catch(function () {});
    };
    updateNotices(); setInterval(updateNotices, 2500);
  }

  var dmThread = document.querySelector('.dm-thread[data-presence]');
  if (dmThread) {
    var presenceDot = document.getElementById('partner-presence');
    function updatePresence() {
      fetch(dmThread.dataset.presence, {credentials:'same-origin', headers:{'X-Requested-With':'XMLHttpRequest'}})
        .then(function (r) { return r.json(); }).then(function (data) {
          if (!presenceDot) return;
          presenceDot.classList.toggle('online', !!data.online);
          presenceDot.classList.toggle('offline', !data.online);
          presenceDot.setAttribute('aria-label', data.online ? 'Online' : 'Offline');
        }).catch(function () {});
    }
    updatePresence(); setInterval(updatePresence, 15000);
    var nicknameForm = document.getElementById('nickname-form');
    var nicknameEdit = document.getElementById('nickname-edit');
    var nicknameInput = document.getElementById('nickname-input');
    var nicknameStatus = document.getElementById('nickname-status');
    if (nicknameEdit && nicknameForm) nicknameEdit.addEventListener('click', function () { nicknameForm.hidden = !nicknameForm.hidden; if (!nicknameForm.hidden) nicknameInput.focus(); });
    function saveNickname(value) {
      var token = nicknameForm.querySelector('[name=csrfmiddlewaretoken]').value;
      var body = new URLSearchParams(); body.set('csrfmiddlewaretoken', token); body.set('nickname', value);
      fetch(dmThread.dataset.nickname, {method:'POST', credentials:'same-origin', headers:{'X-Requested-With':'XMLHttpRequest','Content-Type':'application/x-www-form-urlencoded'}, body:body.toString()})
        .then(function (r) { return r.json(); }).then(function (data) {
          if (!data.ok) throw new Error('Could not save nickname');
          var display = document.getElementById('partner-display-name');
          if (display) display.textContent = data.nickname || display.dataset.fullname || 'Unknown';
          nicknameInput.value = data.nickname;
          nicknameStatus.textContent = data.nickname ? 'Nickname saved.' : 'Nickname reset.';
        }).catch(function () { nicknameStatus.textContent = 'Could not save nickname. Please try again.'; });
    }
    if (nicknameForm) {
      var displayName = document.getElementById('partner-display-name');
      if (displayName) displayName.dataset.fullname = displayName.textContent;
      nicknameForm.addEventListener('submit', function (e) { e.preventDefault(); saveNickname(nicknameInput.value.trim()); });
      document.getElementById('nickname-reset').addEventListener('click', function () { nicknameInput.value = ''; saveNickname(''); });
    }
  }


  // SCSS custom 2D emoji system: bold yellow expression faces + refined white line-art gestures.
  var emojiItems = {
    faces: [
      ['smile','Smile'],['open_mouth','Open mouth'],['grin','Big grin'],['sweat_laugh','Sweat laugh'],
      ['laugh','Laugh'],['sad','Sad'],['cry','Crying'],['surprised','Surprised'],
      ['angry','Angry'],['grimace','Grimace'],['kiss','Kiss'],['heart_eyes','Heart eyes'],
      ['pleading','Pleading'],['tongue','Tongue out'],['cool','Cool'],['meh','Meh'],['smirk','Smirk']
    ],
    hands: [
      ['like','Thumbs up'],['dislike','Thumbs down'],['point','Pointing'],['peace','Peace sign'],
      ['open_hand','Open hand'],['fist','Fist'],['handshake','Handshake'],['heart','Heart'],
      ['heart_hands','Heart hands'],['clap','Clapping'],['folded_hands','Folded hands'],['ok_hand','OK sign'],
      ['index_up','Index finger'],['wave','Waving'],['question','Question'],['exclamation','Exclamation'],
      ['one','1'],['two','2'],['three','3'],['four','4'],['five','5']
    ],
    fun: [
      ['fire','Fire','🔥'],['hug','Hug','🫂'],['red_heart','Red Heart','❤️'],['fireworks','Fireworks','🎆'],
      ['cake','Cake','🎂'],['party','Party','🥳'],['sparkles','Sparkles','✨'],['star','Star','⭐'],
      ['thumbs_up','Thumbs Up','👍'],['thumbs_down','Thumbs Down','👎'],['laughing','Laughing','🤣'],
      ['sob','Sobbing','😭'],['thinking','Thinking','🤔'],['rocket','Rocket','🚀'],['tada','Tada','🎉'],
      ['gift','Gift','🎁'],['balloon','Balloon','🎈'],['coffee','Coffee','☕'],['pizza','Pizza','🍕'],
      ['sun','Sun','☀️'],['moon','Moon','🌙'],['check','Check','✅'],['x_mark','Cross mark','❌']
    ]
  };
  function emojiSvg(name) {
    var faces = ['smile','open_mouth','grin','sweat_laugh','laugh','sad','cry','surprised','angry','grimace','kiss','heart_eyes','pleading','tongue','cool','meh','smirk'];
    var inner = '';
    if (faces.indexOf(name) >= 0) {
      var eyes = '<circle cx="23" cy="27" r="4.2"/><circle cx="41" cy="27" r="4.2"/>', brows = '', mouth = '<path d="M23 39 Q32 51 41 39"/>', extras = '';
      if (name === 'open_mouth' || name === 'surprised') mouth = '<ellipse cx="32" cy="42" rx="7" ry="9" fill="#050505"/>';
      if (name === 'grin') mouth = '<path d="M16 38 Q32 35 48 38 Q47 53 32 53 Q17 53 16 38Z" fill="#050505"/><path d="M19 41 H45" stroke="#FFD633" stroke-width="2.5"/>';
      if (name === 'sweat_laugh' || name === 'laugh') { eyes='<path d="M18 28 Q23 21 28 28 M36 28 Q41 21 46 28"/>'; mouth='<path d="M16 36 Q32 61 48 36 Q47 53 32 53 Q17 53 16 36Z" fill="#050505"/><path d="M23 47 Q32 51 41 47" stroke="#FFD633" stroke-width="2.5"/>'; if(name==='sweat_laugh') extras='<path d="M49 5 Q43 15 49 19 Q56 19 54 12Z" fill="#FFD633"/>'; }
      if (name === 'sad') mouth='<path d="M22 47 Q32 32 42 47"/>';
      if (name === 'cry') { mouth='<path d="M22 47 Q32 34 42 47"/>'; extras='<path d="M22 32 Q13 43 20 49 Q27 47 22 32Z M42 32 Q35 43 42 49 Q49 47 42 32Z" fill="#FFD633"/>'; }
      if (name === 'angry') { brows='<path d="M17 22 L28 26 M47 22 L36 26"/>'; mouth='<path d="M21 48 Q32 33 43 48"/>'; }
      if (name === 'grimace') mouth='<rect x="17" y="37" width="30" height="16" rx="5" fill="#050505"/><path d="M24 38 V52 M32 38 V53 M40 38 V52" stroke="#FFD633" stroke-width="2.5"/>';
      if (name === 'kiss') { eyes='<path d="M18 26 Q23 31 28 26 M36 26 Q41 31 46 26"/>'; mouth='<path d="M28 42 Q32 37 36 42 Q32 49 28 42Z" fill="#050505"/>'; extras='<path d="M49 37 C45 31 37 36 43 43 L49 49 L55 43 C61 36 53 31 49 37Z" fill="#FFD633"/>'; }
      if (name === 'heart_eyes') { eyes='<path d="M23 21 C16 14 8 24 23 35 C38 24 30 14 23 21Z M41 21 C34 14 26 24 41 35 C56 24 48 14 41 21Z" fill="#050505"/>'; }
      if (name === 'pleading') { eyes='<circle cx="23" cy="27" r="5.5"/><circle cx="41" cy="27" r="5.5"/><circle cx="21" cy="25" r="1.8" fill="#FFD633"/><circle cx="39" cy="25" r="1.8" fill="#FFD633"/>'; mouth='<path d="M27 45 Q32 39 37 45"/>'; }
      if (name === 'tongue') { eyes='<path d="M18 27 Q23 21 28 27 M36 27 Q41 21 46 27"/>'; mouth='<path d="M16 37 H48 Q48 55 32 55 Q16 55 16 37Z" fill="#050505"/><path d="M26 47 Q25 60 35 59 Q42 58 38 46Z" fill="#FFD633"/>'; }
      if (name === 'cool') { eyes='<path d="M13 24 H29 L27 34 H16Z M35 24 H51 L48 34 H37Z" fill="#050505"/><path d="M29 27 H35"/>'; }
      if (name === 'meh') mouth='<path d="M23 43 H41"/>';
      if (name === 'smirk') { eyes='<circle cx="23" cy="27" r="4.2"/><path d="M37 26 Q42 21 47 26"/>'; mouth='<path d="M23 43 Q38 49 45 37"/>'; }
      inner='<circle cx="32" cy="32" r="27" fill="#FFD633" stroke="#050505" stroke-width="3.2"/><g fill="#050505" stroke="#050505" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">'+eyes+'</g><g fill="none" stroke="#050505" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">'+brows+mouth+'</g><g stroke="#050505" stroke-width="2.2" stroke-linejoin="round">'+extras+'</g>';
    } else {
      var paths = {
        like:'<path d="M19 30 L28 30 L35 15 Q38 10 42 14 Q44 17 41 29 L51 29 Q56 29 54 35 L49 49 Q48 52 43 52 H20Z M11 30 H19 V52 H11Z"/>',
        dislike:'<path d="M19 34 L28 34 L35 49 Q38 54 42 50 Q44 47 41 35 L51 35 Q56 35 54 29 L49 15 Q48 12 43 12 H20Z M11 12 H19 V34 H11Z"/>',
        point:'<path d="M15 36 Q12 32 16 29 Q19 27 23 31 L35 35 L47 35 Q53 35 53 40 Q53 45 47 45 H31 L24 51 H16 Q11 50 11 45Z M23 31 L37 20 Q41 17 44 20 Q47 24 42 28 L35 35"/>',
        peace:'<path d="M20 52 L18 30 Q17 25 21 24 Q25 24 26 29 L27 10 Q27 5 31 5 Q35 5 35 10 L36 29 L38 12 Q39 7 43 8 Q47 9 46 14 L44 34 Q43 51 34 54Z"/>',
        open_hand:'<path d="M13 53 L12 30 Q12 25 16 25 Q20 25 20 30 L20 13 Q20 8 24 8 Q28 8 28 13 L28 29 L29 9 Q29 4 33 4 Q37 4 37 9 L37 29 L39 14 Q40 9 44 10 Q48 11 47 16 L45 35 Q44 52 34 55Z"/>',
        fist:'<path d="M15 30 Q15 24 20 24 H23 V17 Q23 12 28 12 Q33 12 33 17 V23 V15 Q33 10 38 10 Q43 10 43 15 V24 Q49 22 51 28 L50 43 Q49 54 38 54 H26 Q15 54 15 43Z M17 30 H49 M25 24 V31 M34 23 V31 M43 24 V31"/>',
        handshake:'<path d="M7 29 L18 19 L27 23 L34 20 L56 31 L48 43 L39 39 L33 45 L27 41 L22 44 L12 36Z M18 19 L28 30 L34 25 L42 31 M22 44 L29 36 M27 41 L34 34 M33 45 L39 38"/>',
        heart:'<path d="M32 53 C26 47 10 37 10 25 Q10 13 22 13 Q29 13 32 22 Q36 13 43 13 Q55 13 55 25 Q55 37 32 53Z"/>',
        heart_hands:'<path d="M8 30 Q14 19 25 25 L32 32 L39 25 Q50 19 56 30 Q52 42 32 53 Q12 42 8 30Z M8 30 L20 40 M56 30 L44 40"/>',
        clap:'<path d="M8 24 L17 14 Q20 11 23 14 L32 23 L39 17 Q43 14 46 18 L55 29 L42 49 Q39 53 34 50 L15 39Z M17 14 L28 25 M23 14 L33 24 M39 17 L47 28"/>',
        folded_hands:'<path d="M12 16 Q16 12 20 17 L32 32 L44 17 Q48 12 52 16 Q56 20 52 25 L39 48 Q32 56 25 48 L12 25 Q8 20 12 16Z M20 17 L32 32 L44 17"/>',
        ok_hand:'<path d="M24 19 Q31 8 40 15 Q46 20 39 26 L29 34 Q25 38 20 34 L13 28 Q9 24 13 20 Q17 16 21 20 L27 25 Q31 28 34 24 Q37 21 34 18 Q31 15 28 19Z M20 34 L16 49 Q15 54 20 55 H39 Q45 54 46 48 L47 34"/>',
        index_up:'<path d="M20 54 L18 34 Q18 29 22 29 Q26 29 26 34 L27 9 Q27 4 31 4 Q35 4 35 9 L36 31 L39 25 Q43 21 47 25 Q50 28 47 33 L42 48 Q39 55 31 55Z"/>',
        wave:'<path d="M12 54 L8 35 Q7 30 11 29 Q15 28 17 34 L16 15 Q16 10 20 10 Q24 10 24 15 L25 31 L27 8 Q27 3 31 4 Q35 4 35 9 L36 30 L39 13 Q40 8 44 10 Q48 11 47 16 L44 37 Q42 53 32 56Z"/>',
        question:'<path d="M22 22 Q22 12 32 12 Q44 12 44 23 Q44 30 33 36 L33 41 M33 49 V50"/>',
        exclamation:'<path d="M32 12 V39 M32 49 V50"/>',
        one:'<path d="M24 21 L34 12 V51"/>', two:'<path d="M20 22 Q21 12 32 12 Q45 12 44 24 Q43 32 20 50 H46"/>',
        three:'<path d="M21 16 Q45 8 45 24 Q44 31 33 32 Q45 33 45 43 Q44 54 20 48"/>',
        four:'<path d="M39 51 V12 L17 38 H49"/>', five:'<path d="M44 13 H22 L20 30 Q45 22 45 40 Q44 54 20 48"/>'
      };
      inner='<g fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'+(paths[name] || paths.point)+'</g>';
    }
    return '<svg viewBox="0 0 64 64" aria-hidden="true" class="emoji-svg">'+inner+'</svg>';
  }
  function iconNode(name) {
    var wrap=document.createElement('span'); wrap.className='emoji-mark'; wrap.dataset.emoji=name;
    var unicode = {fire:'🔥',hug:'🫂',red_heart:'❤️',fireworks:'🎆',cake:'🎂',party:'🥳',sparkles:'✨',star:'⭐',thumbs_up:'👍',thumbs_down:'👎',laughing:'🤣',sob:'😭',thinking:'🤔',rocket:'🚀',tada:'🎉',gift:'🎁',balloon:'🎈',coffee:'☕',pizza:'🍕',sun:'☀️',moon:'🌙',check:'✅',x_mark:'❌'};
    if (unicode[name]) { wrap.textContent=unicode[name]; wrap.classList.add('unicode-emoji'); }
    else wrap.innerHTML=emojiSvg(name);
    return wrap;
  }
  function renderEmojiText(root) {
    var tokenPattern = /:([a-z0-9_]+):/g;
    var urlPattern = /(https?:\/\/[^\s<]+|www\.[^\s<]+)/gi;
    var supported = new Set(['smile','open_mouth','grin','sweat_laugh','laugh','sad','cry','surprised','angry','grimace','kiss','heart_eyes','pleading','tongue','cool','meh','smirk','heart','like','dislike','handshake','heart_hands','clap','folded_hands','ok_hand','index_up','wave','question','exclamation','one','two','three','four','five','point','peace','open_hand','fist','fire','hug','red_heart','fireworks','cake','party','sparkles','star','thumbs_up','thumbs_down','laughing','sob','thinking','rocket','tada','gift','balloon','coffee','pizza','sun','moon','check','x_mark']);
    root.querySelectorAll('p.chat-message-text').forEach(function(p) {
      if (p.dataset.emojiRendered) return;
      var raw = p.textContent || '';
      var matches = [], match;
      var combined = /(:[a-z0-9_]+:|(?:https?:\/\/|www\.)[^\s<]+|(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}(?:\/[^\s<]*)?)/gi;
      while ((match = combined.exec(raw))) {
        var value = match[0], type = value.charAt(0) === ':' ? 'emoji' : 'url';
        if (type === 'emoji' && !supported.has(value.slice(1,-1))) continue;
        matches.push({start:match.index,end:combined.lastIndex,value:value,type:type});
      }
      if (!matches.length) return;
      p.textContent = '';
      var last = 0;
      matches.forEach(function(item) {
        p.appendChild(document.createTextNode(raw.slice(last,item.start)));
        if (item.type === 'emoji') p.appendChild(iconNode(item.value.slice(1,-1)));
        else {
          var clean = item.value.replace(/[),.!?;:]+$/, '');
          var trailing = item.value.slice(clean.length);
          var href = /^(https?:\/\/)/i.test(clean) ? clean : 'https://' + clean;
          try {
            var parsed = new URL(href);
            if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
              var a = document.createElement('a'); a.className='chat-link'; a.href=parsed.href; a.target='_blank'; a.rel='noopener noreferrer'; a.textContent=clean; p.appendChild(a);
            } else p.appendChild(document.createTextNode(clean));
          } catch (e) { p.appendChild(document.createTextNode(clean)); }
          if (trailing) p.appendChild(document.createTextNode(trailing));
        }
        last = item.end;
      });
      p.appendChild(document.createTextNode(raw.slice(last)));
      p.dataset.emojiRendered = '1';
    });
  }
  document.querySelectorAll('.emoji-picker-wrap').forEach(function(wrap){
    var toggle=wrap.querySelector('.emoji-picker-toggle'), picker=wrap.querySelector('.emoji-picker'), form=wrap.closest('form'), input=form.querySelector('input[name=message]');
    Object.keys(emojiItems).forEach(function(group){ var grid=wrap.querySelector('[data-emoji-grid="'+group+'"]'); emojiItems[group].forEach(function(item){ var b=document.createElement('button'); b.type='button'; b.className='emoji-option '+(group==='faces'?'face':'hand'); b.title=item[1]; b.appendChild(iconNode(item[0])); b.addEventListener('click',function(){ var token=':'+item[0]+':'; var start=input.selectionStart||input.value.length, end=input.selectionEnd||start; input.value=input.value.slice(0,start)+token+input.value.slice(end); input.focus(); input.setSelectionRange(start+token.length,start+token.length); }); grid.appendChild(b); }); });
    toggle.addEventListener('click',function(){picker.hidden=!picker.hidden;toggle.setAttribute('aria-expanded',String(!picker.hidden));});
    wrap.querySelectorAll('[data-emoji-tab]').forEach(function(tab){tab.addEventListener('click',function(){wrap.querySelectorAll('[data-emoji-tab]').forEach(function(t){t.classList.toggle('active',t===tab);});wrap.querySelectorAll('[data-emoji-grid]').forEach(function(g){g.hidden=g.dataset.emojiGrid!==tab.dataset.emojiTab;});});});
  });

  var chatLog = document.getElementById('chat-log');
  if (chatLog) {
    var chatForm = document.getElementById('chat-form');
    var chatInput = chatForm.querySelector('input[name=message]');
    var chatEmpty = document.getElementById('chat-empty');
    var chatError = document.getElementById('chat-error');
    var chatLast = parseInt(chatLog.dataset.last, 10) || 0;
    var chatSince = parseFloat(chatLog.dataset.since) || 0;
    var chatBusy = false;
    var csrf = chatForm.querySelector('input[name=csrfmiddlewaretoken]').value;

    // Public Chat @-mention autocomplete: search registered accounts by name prefix.
    var mentionBox = document.getElementById('mention-suggestions');
    var mentionMatches = [];
    var mentionActive = -1;
    var mentionRequest = 0;
    var mentionToken = null;
    var hideMentions = function () {
      if (!mentionBox) return;
      mentionBox.hidden = true;
      mentionBox.textContent = '';
      mentionMatches = [];
      mentionActive = -1;
      mentionToken = null;
      chatInput.removeAttribute('aria-activedescendant');
      chatInput.setAttribute('aria-expanded', 'false');
    };
    var renderMentions = function (accounts) {
      mentionBox.textContent = '';
      mentionMatches = accounts || [];
      mentionActive = -1;
      if (!mentionMatches.length) { hideMentions(); return; }
      mentionMatches.forEach(function (account, index) {
        var option = el('button', 'mention-option');
        option.type = 'button';
        option.id = 'mention-option-' + index;
        option.setAttribute('role', 'option');
        option.setAttribute('aria-selected', 'false');
        option.appendChild(el('strong', 'mention-option-name', account.name));
        option.appendChild(el('small', 'mention-option-role', account.role));
        option.addEventListener('mousedown', function (event) { event.preventDefault(); chooseMention(index); });
        mentionBox.appendChild(option);
      });
      mentionBox.hidden = false;
      chatInput.setAttribute('aria-expanded', 'true');
    };
    var chooseMention = function (index) {
      var account = mentionMatches[index];
      if (!account || !mentionToken) return;
      var before = chatInput.value.slice(0, mentionToken.start);
      var after = chatInput.value.slice(chatInput.selectionStart);
      var inserted = '@' + account.name + ' ';
      chatInput.value = before + inserted + after;
      var caret = (before + inserted).length;
      chatInput.focus();
      chatInput.setSelectionRange(caret, caret);
      hideMentions();
    };
    var updateMentionActive = function (next) {
      if (!mentionMatches.length) return;
      mentionActive = (next + mentionMatches.length) % mentionMatches.length;
      Array.prototype.forEach.call(mentionBox.children, function (option, index) {
        option.setAttribute('aria-selected', index === mentionActive ? 'true' : 'false');
        option.classList.toggle('active', index === mentionActive);
      });
      chatInput.setAttribute('aria-activedescendant', 'mention-option-' + mentionActive);
    };
    if (mentionBox) {
      chatInput.addEventListener('input', function () {
        var caret = chatInput.selectionStart;
        var before = chatInput.value.slice(0, caret);
        var match = /(^|\s)@([^\s@]*)$/.exec(before);
        if (!match) { hideMentions(); return; }
        var query = match[2];
        mentionToken = {start: caret - query.length - 1};
        var requestId = ++mentionRequest;
        fetch(chatLog.dataset.mentions + '?q=' + encodeURIComponent(query), {
          credentials: 'same-origin', headers: {'X-Requested-With': 'XMLHttpRequest'}
        }).then(function (response) { return response.json(); }).then(function (data) {
          if (requestId !== mentionRequest || !mentionToken) return;
          renderMentions(data.accounts || []);
        }).catch(function () { if (requestId === mentionRequest) hideMentions(); });
      });
      chatInput.addEventListener('keydown', function (event) {
        if (mentionBox.hidden || !mentionMatches.length) return;
        if (event.key === 'ArrowDown') { event.preventDefault(); updateMentionActive(mentionActive + 1); }
        else if (event.key === 'ArrowUp') { event.preventDefault(); updateMentionActive(mentionActive < 0 ? mentionMatches.length - 1 : mentionActive - 1); }
        else if (event.key === 'Enter' && mentionActive >= 0) { event.preventDefault(); chooseMention(mentionActive); }
        else if (event.key === 'Escape') { event.preventDefault(); hideMentions(); }
      });
      document.addEventListener('click', function (event) {
        if (!mentionBox.contains(event.target) && event.target !== chatInput) hideMentions();
      });
    }

    var nearBottom = function () {
      return chatLog.scrollHeight - chatLog.scrollTop - chatLog.clientHeight < 90;
    };
    var toBottom = function () { chatLog.scrollTop = chatLog.scrollHeight; };
    var showError = function (text) {
      chatError.textContent = text || '';
      chatError.hidden = !text;
    };
    var el = function (tag, cls, text) {
      var node = document.createElement(tag);
      if (cls) node.className = cls;
      if (text !== undefined) node.textContent = text;
      return node;
    };
    var appendLinkedText = function (parent, text) {
      var value = String(text || '');
      var pattern = /((https?:\/\/|www\.)[^\s<]+)/gi;
      var last = 0, match;
      while ((match = pattern.exec(value))) {
        parent.appendChild(document.createTextNode(value.slice(last, match.index)));
        var raw = match[0].replace(/[),.!?;:]+$/, '');
        var trailing = match[0].slice(raw.length);
        var href = raw.indexOf('www.') === 0 ? 'https://' + raw : raw;
        try {
          var parsed = new URL(href);
          if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
            var a = el('a', 'chat-link', raw); a.href = parsed.href; a.target = '_blank'; a.rel = 'noopener noreferrer';
            parent.appendChild(a);
          } else parent.appendChild(document.createTextNode(raw));
        } catch (err) { parent.appendChild(document.createTextNode(raw)); }
        if (trailing) parent.appendChild(document.createTextNode(trailing));
        last = match.index + match[0].length;
      }
      parent.appendChild(document.createTextNode(value.slice(last)));
    };
    var attachmentNode = function (m) {
      if (!m.attachment_url) return null;
      if (m.attachment_type === 'image') {
        var a = el('a', 'chat-attachment-image'); a.href = m.attachment_url; a.target = '_blank'; a.rel = 'noopener';
        var img = el('img'); img.src = m.attachment_url; img.alt = m.attachment_name || 'Shared image'; a.appendChild(img); return a;
      }
      if (m.attachment_type === 'audio') {
        var audio = el('audio', 'chat-audio'); audio.controls = true; audio.preload = 'metadata'; audio.src = m.attachment_url; return audio;
      }
      var link = el('a', 'chat-file-link'); link.innerHTML = '<svg class="chat-icon chat-file-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m21.4 11.1-8.5 8.5a6 6 0 0 1-8.5-8.5l9.2-9.2a4 4 0 0 1 5.7 5.7l-9.2 9.2a2 2 0 0 1-2.8-2.8l8.5-8.5"/></svg>'; link.appendChild(document.createTextNode(m.attachment_name || 'Download file')); 
      link.href = m.attachment_url; link.target = '_blank'; link.rel = 'noopener'; link.download = m.attachment_name || ''; return link;
    };
    var urlFor = function (template, id) { return template.replace('/0/', '/' + id + '/'); };
    var post = function (url, fields) {
      var body = new URLSearchParams();
      body.append('csrfmiddlewaretoken', csrf);
      Object.keys(fields || {}).forEach(function (k) { body.append(k, fields[k]); });
      return fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' }, body: body })
        .then(function (res) { return res.json(); });
    };
    var findMsg = function (id) { return chatLog.querySelector('[data-id="' + id + '"]'); };
    var reactionUrl = function(id){ return urlFor(chatLog.dataset.reaction,id); };
    var paintReactions = function(li, rows){ var old=li.querySelector('.message-reactions'); if(old) old.remove(); if(!rows || !rows.length) return; var box=el('div','message-reactions'); rows.forEach(function(r){ var b=el('button','reaction-chip'); b.type='button'; b.dataset.reaction=r.reaction; b.appendChild(iconNode(r.reaction)); b.appendChild(el('small','',String(r.count))); box.appendChild(b); }); var bubble=li.querySelector('.chat-bubble'); if(bubble) bubble.appendChild(box); };
    var react = function(li, key){ post(reactionUrl(li.dataset.id),{reaction:key}).then(function(d){if(!d.ok){showError(d.error||'Reaction could not be saved.');return;}paintReactions(li,d.reactions);}).catch(function(){showError('Reaction could not be saved.');}); };
    var showReactionPicker = function(li, anchor){
      var old=document.querySelector('.reaction-tray'); if(old){old.remove();if(old.dataset.messageId===li.dataset.id)return;}
      var tray=el('div','reaction-tray'); tray.dataset.messageId=li.dataset.id; tray.setAttribute('role','group'); tray.setAttribute('aria-label','Choose a reaction');
      emojiItems.faces.concat(emojiItems.hands, emojiItems.fun || []).forEach(function(item){var b=el('button','reaction-option');b.type='button';b.title=item[1];b.setAttribute('aria-label',item[1]);b.appendChild(iconNode(item[0]));b.addEventListener('click',function(){react(li,item[0]);tray.remove();});tray.appendChild(b);});
      document.body.appendChild(tray);
      var rect=anchor.getBoundingClientRect(), pad=8, width=Math.min(340,window.innerWidth-pad*2);
      tray.style.width=width+'px';
      var left=Math.max(pad,Math.min(rect.right-width,window.innerWidth-width-pad));
      var height=tray.offsetHeight, top=rect.top-height-8;
      if(top<pad) top=Math.min(window.innerHeight-height-pad,rect.bottom+8);
      tray.style.left=left+'px'; tray.style.top=Math.max(pad,top)+'px';
    };
    document.addEventListener('pointerdown',function(e){var tray=document.querySelector('.reaction-tray');if(tray&&!tray.contains(e.target)&&!e.target.closest('.chat-react-btn'))tray.remove();});
    chatLog.addEventListener('scroll',function(){var tray=document.querySelector('.reaction-tray');if(tray)tray.remove();},{passive:true});
    window.addEventListener('resize',function(){var tray=document.querySelector('.reaction-tray');if(tray)tray.remove();});
    var syncEmpty = function () {
      if (chatEmpty) chatEmpty.hidden = chatLog.children.length > 0;
    };

    var buildActions = function (m) {
      var box = el('span', 'chat-actions');
      if (m.can_edit) {
        box.appendChild(el('span', 'chat-timer', m.seconds_left + 's'));
        var edit = el('button', 'chat-act', 'Edit');
        edit.type = 'button';
        edit.setAttribute('data-act', 'edit');
        box.appendChild(edit);
      }
      if (m.can_delete) {
        var del = el('button', 'chat-act', 'Delete');
        del.type = 'button';
        del.setAttribute('data-act', 'delete');
        box.appendChild(del);
      }
      return box;
    };

    var fillMessage = function (li, m) {
      li.className = 'chat-msg' + (m.own ? ' own' : '') + (m.role === 'admin' ? ' admin-message' : '');
      li.setAttribute('data-id', m.id);
      li.removeAttribute('data-seconds');
      li.removeAttribute('data-admin');
      if (m.can_edit) li.setAttribute('data-expires', String(Date.now() + m.seconds_left * 1000));
      else li.removeAttribute('data-expires');
      if (m.admin_delete) li.setAttribute('data-admin', '1');
      li.textContent = '';

      if (m.role !== 'admin') li.appendChild(el('span', 'when message-time', m.time));
      var bubble = el('div', 'chat-bubble');
      var meta = el('div', 'thread-meta');
      if (m.role === 'admin') {
        meta.appendChild(el('span', 'tag role-admin', 'Admin'));
      } else if (!m.own) {
        meta.appendChild(el('span', 'tag role-' + m.role, m.role_label));
        meta.appendChild(el('strong', 'sender-name', m.name || ''));
      }
      if (m.edited) meta.appendChild(el('span', 'edited', 'edited'));
      if (m.can_edit || m.can_delete) meta.appendChild(buildActions(m));
      if (meta.children.length) bubble.appendChild(meta);
      if (m.reply) {
        var quote = el('div', 'chat-reply-quote');
        quote.appendChild(el('span', 'reply-quote-label', '↪ ' + m.reply.name + ' · '));
        quote.appendChild(el('span', 'reply-quote-text', m.reply.text));
        bubble.appendChild(quote);
      }
      if (m.text) { var messageText = el('p', 'chat-message-text', m.text); bubble.appendChild(messageText); }
      var attachment = attachmentNode(m); if (attachment) bubble.appendChild(attachment);
      if (m.role === 'admin') bubble.appendChild(el('span', 'when message-time admin-message-time', m.time));
      if (m.can_reply && m.role !== 'admin') {
        var tools = el('div','message-tools'); var replyBtn = el('button', 'chat-reply-btn', '↩ Reply');
        replyBtn.type = 'button'; replyBtn.dataset.act = 'reply'; tools.appendChild(replyBtn);
        var reactBtn=el('button','chat-react-btn','＋ React'); reactBtn.type='button'; reactBtn.dataset.act='react'; tools.appendChild(reactBtn); bubble.appendChild(tools);
      }
      li.appendChild(bubble); paintReactions(li,m.reactions||[]); renderEmojiText(li);
    };

    var initExisting = function () {
      chatLog.querySelectorAll('.chat-msg[data-seconds]').forEach(function (li) {
        li.setAttribute('data-expires', String(Date.now() + parseInt(li.dataset.seconds, 10) * 1000));
      });
    };

    var addMessage = function (m) {
      if (findMsg(m.id)) return;
      var li = document.createElement('li');
      fillMessage(li, m);
      chatLog.appendChild(li);
      if (m.id > chatLast) chatLast = m.id;
      syncEmpty();
    };

    var applyChange = function (m) {
      var li = findMsg(m.id);
      if (!li) return;
      if (m.deleted) { li.remove(); syncEmpty(); return; }
      if (li.querySelector('.chat-edit')) return;
      var expires = li.dataset.expires;
      fillMessage(li, m);
      if (!m.can_edit && expires) li.setAttribute('data-expires', expires);
    };

    var pollChat = function () {
      if (chatBusy || document.hidden) return;
      chatBusy = true;
      var url = chatLog.dataset.feed + '?after=' + chatLast + '&since=' + encodeURIComponent(chatSince);
      fetch(url, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          var stick = nearBottom();
          data.changed.forEach(applyChange);
          data.messages.forEach(addMessage);
          chatSince = data.now;
          if (data.messages.length && stick) toBottom();
        })
        .catch(function () {})
        .then(function () { chatBusy = false; });
    };

    var tick = function () {
      chatLog.querySelectorAll('.chat-msg[data-expires]').forEach(function (li) {
        var left = Math.ceil((parseInt(li.dataset.expires, 10) - Date.now()) / 1000);
        var timer = li.querySelector('.chat-timer');
        if (left > 0) {
          if (timer) timer.textContent = left + 's';
          return;
        }
        li.removeAttribute('data-expires');
        if (timer) timer.remove();
        var edit = li.querySelector('.chat-act[data-act=edit]');
        if (edit) edit.remove();
        var editor = li.querySelector('.chat-edit');
        if (editor) {
          var p = el('p', '', editor.querySelector('input').defaultValue);
          editor.replaceWith(p);
        }
        if (!li.dataset.admin) {
          var del = li.querySelector('.chat-act[data-act=delete]');
          if (del) del.remove();
        }
        var actions = li.querySelector('.chat-actions');
        if (actions && !actions.children.length) actions.remove();
      });
    };

    var startEdit = function (li) {
      if (li.querySelector('.chat-edit')) return;
      var p = li.querySelector('p.chat-message-text');
      var original = p ? p.textContent : '';
      var box = el('div', 'chat-edit');
      var input = el('input');
      input.type = 'text';
      input.value = original;
      input.defaultValue = original;
      input.maxLength = chatInput.maxLength;
      var save = el('button', 'btn small', 'Save');
      save.type = 'button';
      var cancel = el('button', 'btn small', 'Cancel');
      cancel.type = 'button';
      box.appendChild(input);
      box.appendChild(save);
      box.appendChild(cancel);
      if (p) p.replaceWith(box); else li.querySelector('.chat-bubble').insertBefore(box, li.querySelector('.chat-bubble').firstChild);
      input.focus();
      var restore = function (text) { box.replaceWith(el('p', '', text)); };
      var submit = function () {
        var text = input.value.trim();
        if (!text) { showError('Message cannot be empty.'); return; }
        if (text === original) { restore(original); return; }
        showError('');
        post(urlFor(chatLog.dataset.edit, li.dataset.id), { message: text })
          .then(function (data) {
            if (!data.ok) { showError(data.error || 'Could not edit this message.'); restore(original); return; }
            var expires = li.dataset.expires;
            fillMessage(li, data.message);
            if (!data.message.can_edit && expires) li.setAttribute('data-expires', expires);
          })
          .catch(function () { showError('Could not edit this message.'); restore(original); });
      };
      save.addEventListener('click', submit);
      cancel.addEventListener('click', function () { restore(original); });
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); submit(); }
        if (e.key === 'Escape') restore(original);
      });
    };

    document.getElementById('cancel-reply').addEventListener('click', function () { chatForm.querySelector('input[name=reply_to]').value = ''; document.getElementById('replying-to').hidden = true; });

    var attachmentInput = document.getElementById('chat-attachment');
    var attachmentLabel = document.getElementById('chat-attachment-name');
    var attachmentStatus = document.getElementById('chat-attachment-status');
    var attachmentIcon = attachmentLabel && attachmentLabel.querySelector('.chat-pending-icon');
    var paperclipSvg = '<svg class="chat-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m21.4 11.1-8.5 8.5a6 6 0 0 1-8.5-8.5l9.2-9.2a4 4 0 0 1 5.7 5.7l-9.2 9.2a2 2 0 0 1-2.8-2.8l8.5-8.5"/></svg>';
    var removeAttachmentButton = document.getElementById('chat-attachment-remove');
    var micButton = document.getElementById('chat-mic');
    var recorder = null, recordingChunks = [];
    if (attachmentInput) attachmentInput.addEventListener('change', function () {
      var file = attachmentInput.files && attachmentInput.files[0];
      if (file && file.size > 20 * 1024 * 1024) { attachmentInput.value = ''; showError('Files must be 20 MB or smaller.'); attachmentLabel.hidden = true; return; }
      if (attachmentStatus) attachmentStatus.textContent = file ? 'File attached: ' + file.name + ' — ready to send. Remember to press Send.' : '';
      if (attachmentIcon) attachmentIcon.innerHTML = file ? paperclipSvg : '';
      if (attachmentLabel) attachmentLabel.hidden = !file;
      if (attachmentLabel) attachmentLabel.classList.toggle('voice-ready', false);
      showError('');
    });
    if (micButton && navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder) {
      micButton.addEventListener('click', function () {
        if (recorder && recorder.state === 'recording') { recorder.stop(); micButton.innerHTML = '<svg class="chat-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8"/></svg>'; micButton.classList.remove('recording'); return; }
        navigator.mediaDevices.getUserMedia({audio:true}).then(function (stream) {
          recordingChunks = [];
          recorder = new MediaRecorder(stream);
          recorder.ondataavailable = function (event) { if (event.data && event.data.size) recordingChunks.push(event.data); };
          recorder.onstop = function () {
            var blob = new Blob(recordingChunks, {type: recorder.mimeType || 'audio/webm'});
            var ext = (blob.type.indexOf('ogg') >= 0) ? 'ogg' : (blob.type.indexOf('mp4') >= 0 ? 'm4a' : 'webm');
            var file = new File([blob], 'voice-message.' + ext, {type:blob.type});
            var transfer = new DataTransfer(); transfer.items.add(file); attachmentInput.files = transfer.files;
            if (attachmentStatus) attachmentStatus.textContent = 'Voice recording ready to send. Remember to press Send.';
            if (attachmentIcon) attachmentIcon.innerHTML = '<svg class="chat-icon" viewBox="0 0 24 24"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8"/></svg>'; 
            if (attachmentLabel) { attachmentLabel.hidden = false; attachmentLabel.classList.add('voice-ready'); }
            stream.getTracks().forEach(function (track) { track.stop(); });
          };
          recorder.start(); micButton.innerHTML = '<svg class="chat-icon chat-stop-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>'; micButton.classList.add('recording');
        }).catch(function () { showError('Microphone permission was not granted or is unavailable.'); });
      });
    } else if (micButton) { micButton.disabled = true; micButton.title = 'Audio recording is not supported in this browser'; }
    if (removeAttachmentButton) removeAttachmentButton.addEventListener('click', function () {
      if (attachmentInput) attachmentInput.value = '';
      if (attachmentLabel) { attachmentLabel.hidden = true; attachmentLabel.classList.remove('voice-ready'); }
      if (attachmentStatus) attachmentStatus.textContent = '';
      if (attachmentIcon) attachmentIcon.innerHTML = '';
    });
    chatForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var text = chatInput.value.trim();
      hideMentions();
      var file = attachmentInput && attachmentInput.files && attachmentInput.files[0];
      if (!text && !file) return;
      showError('');
      var body = new FormData();
      body.append('csrfmiddlewaretoken', csrf);
      body.append('message', text);
      body.append('reply_to', chatForm.querySelector('input[name=reply_to]').value);
      if (file) body.append('attachment', file);
      fetch(chatLog.dataset.send, {method:'POST', credentials:'same-origin', headers:{'X-Requested-With':'XMLHttpRequest'}, body:body})
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (!data.ok) { showError(data.error || 'Message could not be sent.'); return; }
          chatInput.value = '';
          if (attachmentInput) attachmentInput.value = '';
          if (attachmentLabel) { attachmentLabel.hidden = true; attachmentLabel.classList.remove('voice-ready'); }
          if (attachmentStatus) attachmentStatus.textContent = '';
          if (attachmentIcon) attachmentIcon.innerHTML = '';
          chatForm.querySelector('input[name=reply_to]').value = ''; document.getElementById('replying-to').hidden = true;
          addMessage(data.message);
          toBottom();
        })
        .catch(function () { showError('Message could not be sent. Check your connection.'); });
    });

    chatLog.addEventListener('click', function (e) {
      var btn = e.target.closest('.chat-act, .chat-reply-btn, .chat-react-btn, .reaction-chip');
      if (!btn) return;
      var li = btn.closest('.chat-msg');
      if (btn.dataset.act === 'edit') { startEdit(li); return; }
      if (btn.dataset.act === 'react') { showReactionPicker(li,btn); return; }
      if (btn.classList.contains('reaction-chip')) { react(li,btn.dataset.reaction); return; }
      if (btn.dataset.act === 'reply') {
        var textNode = li.querySelector('p');
        chatForm.querySelector('input[name=reply_to]').value = li.dataset.id;
        document.getElementById('replying-label').textContent = 'Replying to: ' + (li.querySelector('.thread-meta strong') ? li.querySelector('.thread-meta strong').textContent : 'your message') + ' — ' + (textNode ? textNode.textContent.slice(0,90) : '');
        document.getElementById('replying-to').hidden = false; chatInput.focus(); return;
      }

      post(urlFor(chatLog.dataset.delete, li.dataset.id), {})
        .then(function (data) {
          if (!data.ok) { showError(data.error || 'Could not delete this message.'); return; }
          li.remove();
          syncEmpty();
        })
        .catch(function () { showError('Could not delete this message.'); });
    });

    initExisting();
    chatLog.querySelectorAll('.chat-msg').forEach(function(li){renderEmojiText(li);});
    toBottom();
    setInterval(pollChat, 2000);
    setInterval(tick, 1000);
  }
})();
