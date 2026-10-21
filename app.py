import os
import io
import json
import uuid
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify, redirect, url_for, session, send_file, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import database
import export_utils

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_PHOTO_DIR = os.path.join(BASE_DIR, 'static', 'uploads', 'photos')
UPLOAD_MUSIC_DIR = os.path.join(BASE_DIR, 'static', 'uploads', 'music')
UPLOAD_THEME_DIR = os.path.join(BASE_DIR, 'static', 'uploads', 'themes')

for d in [UPLOAD_PHOTO_DIR, UPLOAD_MUSIC_DIR, UPLOAD_THEME_DIR]:
    os.makedirs(d, exist_ok=True)

ALLOWED_PHOTO_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.svg'}
ALLOWED_MUSIC_EXTS = {'.mp3', '.wav', '.m4a', '.ogg'}

MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_MUSIC_SIZE = 10 * 1024 * 1024 # 10 MB

app = Flask(__name__)
app.secret_key = 'wedding-digital-super-secret-key-2026-secure'
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024 # 15 MB request ceiling

# Initialize database on startup
database.init_db()


# ------------------ AUTH HELPERS & DECORATORS ------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Akses khusus administrator.', 'error')
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def calculate_completion(data):
    """Calculates status for each of 7 sections and overall percentage."""
    statuses = {}

    # 1. Theme
    t_name = data.get('theme_name')
    if t_name and str(t_name).strip():
        statuses['theme'] = 'complete'
    else:
        statuses['theme'] = 'empty'

    # 2. Biodata
    g_req = [data.get('groom_name'), data.get('groom_nickname'), data.get('groom_father'), data.get('groom_mother')]
    b_req = [data.get('bride_name'), data.get('bride_nickname'), data.get('bride_father'), data.get('bride_mother')]
    g_filled = sum(1 for x in g_req if x and str(x).strip())
    b_filled = sum(1 for x in b_req if x and str(x).strip())
    
    if g_filled >= 3 and b_filled >= 3:
        statuses['groom_bride'] = 'complete'
    elif g_filled > 0 or b_filled > 0 or data.get('groom_photo') or data.get('bride_photo'):
        statuses['groom_bride'] = 'partial'
    else:
        statuses['groom_bride'] = 'empty'

    # 3. Events
    events = data.get('events', [])
    if isinstance(events, str):
        try:
            events = json.loads(events)
        except Exception:
            events = []
    
    if events and len(events) > 0:
        valid_evs = [e for e in events if e.get('name') and e.get('date') and e.get('location_name')]
        if len(valid_evs) == len(events) and len(valid_evs) > 0:
            statuses['events'] = 'complete'
        else:
            statuses['events'] = 'partial'
    else:
        statuses['events'] = 'empty'

    # 4. Love Story
    stories = data.get('love_stories', [])
    if isinstance(stories, str):
        try:
            stories = json.loads(stories)
        except Exception:
            stories = []

    if stories and len(stories) > 0:
        valid_stories = [s for s in stories if s.get('title') and s.get('story_text')]
        if len(valid_stories) >= 1:
            statuses['story'] = 'complete'
        else:
            statuses['story'] = 'partial'
    else:
        statuses['story'] = 'empty'

    # 5. Gifts
    gifts = data.get('gifts', {})
    if isinstance(gifts, str):
        try:
            gifts = json.loads(gifts)
        except Exception:
            gifts = {}
    
    banks = gifts.get('bank_accounts', [])
    ewallets = gifts.get('ewallets', [])
    phys = gifts.get('physical_gift', {})

    has_bank = any(b.get('bank_name') and b.get('account_number') for b in banks)
    has_ewallet = any(e.get('provider') and e.get('number') for e in ewallets)
    has_phys = bool(phys.get('address') and phys.get('recipient'))

    if has_bank or has_ewallet or has_phys:
        statuses['gifts'] = 'complete'
    elif banks or ewallets or phys:
        statuses['gifts'] = 'partial'
    else:
        statuses['gifts'] = 'empty'

    # 6. Inviters
    inviters = data.get('guest_inviters', [])
    if isinstance(inviters, str):
        try:
            inviters = json.loads(inviters)
        except Exception:
            inviters = []

    valid_inviters = [i for i in inviters if i.get('name') and i.get('name').strip()]
    if len(valid_inviters) > 0:
        statuses['inviters'] = 'complete'
    else:
        statuses['inviters'] = 'empty'

    # 7. Backsound
    m_type = data.get('music_choice_type', 'preset')
    if m_type == 'preset' and data.get('music_preset_id'):
        statuses['music'] = 'complete'
    elif m_type == 'upload' and (data.get('music_custom_file') or (data.get('music_title') and data.get('music_artist'))):
        statuses['music'] = 'complete'
    elif data.get('music_title') or data.get('music_artist'):
        statuses['music'] = 'partial'
    else:
        statuses['music'] = 'empty'

    # Progress points
    score = 0.0
    for s in statuses.values():
        if s == 'complete':
            score += 1.0
        elif s == 'partial':
            score += 0.5
            
    pct = int(round((score / 7.0) * 100))
    return statuses, pct


# ------------------ GENERAL ROUTES ------------------

@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('client_dashboard'))
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = database.get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            if not user['is_active']:
                flash('Akun ini telah dinonaktifkan oleh Administrator.', 'error')
                return render_template('login.html', username=username)

            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']

            if user['role'] == 'client':
                client = conn.execute('SELECT id, couple_name FROM clients WHERE user_id = ?', (user['id'],)).fetchone()
                if client:
                    session['client_id'] = client['id']
                    session['couple_name'] = client['couple_name']
                return redirect(url_for('client_dashboard'))
            else:
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Username atau password salah. Silakan coba kembali.', 'error')
            return render_template('login.html', username=username)

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah berhasil keluar.', 'info')
    return redirect(url_for('login_page'))

@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json() or {}
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')

    if not new_pw or len(new_pw) < 6:
        return jsonify({'success': False, 'message': 'Password baru minimal 6 karakter.'}), 400

    conn = database.get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not user or not check_password_hash(user['password_hash'], old_pw):
        return jsonify({'success': False, 'message': 'Password lama salah.'}), 400

    conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (generate_password_hash(new_pw), session['user_id']))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Password berhasil diperbarui!'})


# ------------------ FILE UPLOAD ROUTE ------------------

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Tidak ada file yang dipilih.'}), 400

    file = request.files['file']
    file_type = request.form.get('type', 'photo') # 'photo' or 'music' or 'theme'

    if not file or file.filename == '':
        return jsonify({'success': False, 'message': 'Nama file tidak valid.'}), 400

    orig_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_type == 'music':
        if orig_ext not in ALLOWED_MUSIC_EXTS:
            return jsonify({'success': False, 'message': f'Format musik tidak didukung. Gunakan: {", ".join(ALLOWED_MUSIC_EXTS)}'}), 400
        # Check size
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_MUSIC_SIZE:
            return jsonify({'success': False, 'message': 'Ukuran file musik maksimal 10 MB.'}), 400

        target_dir = UPLOAD_MUSIC_DIR
        sub_path = 'music'
    elif file_type == 'theme':
        if orig_ext not in ALLOWED_PHOTO_EXTS:
            return jsonify({'success': False, 'message': f'Format gambar tidak didukung. Gunakan: {", ".join(ALLOWED_PHOTO_EXTS)}'}), 400
        target_dir = UPLOAD_THEME_DIR
        sub_path = 'themes'
    else: # photo
        if orig_ext not in ALLOWED_PHOTO_EXTS:
            return jsonify({'success': False, 'message': f'Format foto tidak didukung. Gunakan: {", ".join(ALLOWED_PHOTO_EXTS)}'}), 400
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_PHOTO_SIZE:
            return jsonify({'success': False, 'message': 'Ukuran file foto maksimal 5 MB.'}), 400

        target_dir = UPLOAD_PHOTO_DIR
        sub_path = 'photos'

    unique_name = f"{uuid.uuid4().hex[:12]}_{secure_filename(file.filename)}"
    save_path = os.path.join(target_dir, unique_name)
    file.save(save_path)

    public_url = f"/static/uploads/{sub_path}/{unique_name}"
    return jsonify({
        'success': True,
        'url': public_url,
        'filename': file.filename,
        'message': 'File berhasil diunggah.'
    })


# ------------------ CLIENT DASHBOARD & API ------------------

@app.route('/client')
@login_required
def client_dashboard():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))

    client_id = session.get('client_id')
    if not client_id:
        flash('Data client tidak ditemukan.', 'error')
        return redirect(url_for('login_page'))

    return render_template('client_dashboard.html', client_id=client_id, is_admin=False)

@app.route('/api/client/data')
@login_required
def get_client_data():
    client_id = request.args.get('client_id')
    # If client, can only access their own client_id
    if session.get('role') != 'admin':
        client_id = session.get('client_id')
    elif not client_id:
        return jsonify({'success': False, 'message': 'Client ID diperlukan.'}), 400

    conn = database.get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    if not client:
        return jsonify({'success': False, 'message': 'Data client tidak ditemukan.'}), 404

    wedding_data = conn.execute('SELECT * FROM wedding_data WHERE client_id = ?', (client_id,)).fetchone()
    preset_themes = conn.execute('SELECT * FROM preset_themes WHERE is_active = 1 ORDER BY id ASC').fetchall()
    preset_musics = conn.execute('SELECT * FROM preset_musics WHERE is_active = 1 ORDER BY id ASC').fetchall()

    themes_list = []
    for t in preset_themes:
        td = dict(t)
        try:
            td['colors'] = json.loads(t['colors_json'])
        except Exception:
            td['colors'] = []
        themes_list.append(td)

    musics_list = [dict(m) for m in preset_musics]

    # Convert wedding data row to dict
    wd = dict(wedding_data) if wedding_data else {}
    for jfield in ['events_json', 'love_stories_json', 'gifts_json', 'guest_inviters_json', 'section_statuses_json']:
        if jfield in wd and wd[jfield]:
            try:
                clean_key = jfield.replace('_json', '')
                wd[clean_key] = json.loads(wd[jfield])
            except Exception:
                wd[clean_key] = [] if 'json' in jfield and 'gifts' not in jfield and 'statuses' not in jfield else {}

    conn.close()

    return jsonify({
        'success': True,
        'client': dict(client),
        'wedding_data': wd,
        'preset_themes': themes_list,
        'preset_musics': musics_list
    })

@app.route('/api/client/save', methods=['POST'])
@login_required
def save_client_data():
    payload = request.get_json() or {}
    client_id = payload.get('client_id')

    # Security: clients can only edit their own data
    if session.get('role') != 'admin':
        client_id = session.get('client_id')
    elif not client_id:
        return jsonify({'success': False, 'message': 'Client ID wajib diisi.'}), 400

    conn = database.get_db()
    
    # Calculate statuses & percentage
    calc_data = {
        'theme_name': payload.get('theme_name'),
        'theme_id': payload.get('theme_id'),
        'theme_color': payload.get('theme_color'),
        'theme_custom_note': payload.get('theme_custom_note'),
        'groom_name': payload.get('groom_name'),
        'groom_nickname': payload.get('groom_nickname'),
        'groom_photo': payload.get('groom_photo'),
        'groom_child_order': payload.get('groom_child_order'),
        'groom_father': payload.get('groom_father'),
        'groom_mother': payload.get('groom_mother'),
        'groom_instagram': payload.get('groom_instagram'),
        'bride_name': payload.get('bride_name'),
        'bride_nickname': payload.get('bride_nickname'),
        'bride_photo': payload.get('bride_photo'),
        'bride_child_order': payload.get('bride_child_order'),
        'bride_father': payload.get('bride_father'),
        'bride_mother': payload.get('bride_mother'),
        'bride_instagram': payload.get('bride_instagram'),
        'events': payload.get('events', []),
        'love_stories': payload.get('love_stories', []),
        'gifts': payload.get('gifts', {}),
        'guest_inviters': payload.get('guest_inviters', []),
        'music_choice_type': payload.get('music_choice_type', 'preset'),
        'music_preset_id': payload.get('music_preset_id'),
        'music_custom_file': payload.get('music_custom_file'),
        'music_title': payload.get('music_title'),
        'music_artist': payload.get('music_artist'),
    }

    section_statuses, completion_pct = calculate_completion(calc_data)

    events_json = json.dumps(payload.get('events', []))
    love_stories_json = json.dumps(payload.get('love_stories', []))
    gifts_json = json.dumps(payload.get('gifts', {}))
    guest_inviters_json = json.dumps(payload.get('guest_inviters', []))
    section_statuses_json = json.dumps(section_statuses)

    # Upsert wedding_data
    existing = conn.execute('SELECT id FROM wedding_data WHERE client_id = ?', (client_id,)).fetchone()
    if existing:
        conn.execute('''
        UPDATE wedding_data SET
            theme_name = ?, theme_id = ?, theme_color = ?, theme_custom_note = ?,
            groom_name = ?, groom_nickname = ?, groom_photo = ?, groom_child_order = ?, groom_father = ?, groom_mother = ?, groom_instagram = ?,
            bride_name = ?, bride_nickname = ?, bride_photo = ?, bride_child_order = ?, bride_father = ?, bride_mother = ?, bride_instagram = ?,
            events_json = ?, love_stories_json = ?, gifts_json = ?, guest_inviters_json = ?,
            music_choice_type = ?, music_preset_id = ?, music_custom_file = ?, music_title = ?, music_artist = ?,
            section_statuses_json = ?, completion_percent = ?, updated_at = CURRENT_TIMESTAMP
        WHERE client_id = ?
        ''', (
            payload.get('theme_name'), payload.get('theme_id'), payload.get('theme_color'), payload.get('theme_custom_note'),
            payload.get('groom_name'), payload.get('groom_nickname'), payload.get('groom_photo'), payload.get('groom_child_order'), payload.get('groom_father'), payload.get('groom_mother'), payload.get('groom_instagram'),
            payload.get('bride_name'), payload.get('bride_nickname'), payload.get('bride_photo'), payload.get('bride_child_order'), payload.get('bride_father'), payload.get('bride_mother'), payload.get('bride_instagram'),
            events_json, love_stories_json, gifts_json, guest_inviters_json,
            payload.get('music_choice_type', 'preset'), payload.get('music_preset_id'), payload.get('music_custom_file'), payload.get('music_title'), payload.get('music_artist'),
            section_statuses_json, completion_pct,
            client_id
        ))
    else:
        conn.execute('''
        INSERT INTO wedding_data (
            client_id, theme_name, theme_id, theme_color, theme_custom_note,
            groom_name, groom_nickname, groom_photo, groom_child_order, groom_father, groom_mother, groom_instagram,
            bride_name, bride_nickname, bride_photo, bride_child_order, bride_father, bride_mother, bride_instagram,
            events_json, love_stories_json, gifts_json, guest_inviters_json,
            music_choice_type, music_preset_id, music_custom_file, music_title, music_artist,
            section_statuses_json, completion_percent
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?
        )
        ''', (
            client_id, payload.get('theme_name'), payload.get('theme_id'), payload.get('theme_color'), payload.get('theme_custom_note'),
            payload.get('groom_name'), payload.get('groom_nickname'), payload.get('groom_photo'), payload.get('groom_child_order'), payload.get('groom_father'), payload.get('groom_mother'), payload.get('groom_instagram'),
            payload.get('bride_name'), payload.get('bride_nickname'), payload.get('bride_photo'), payload.get('bride_child_order'), payload.get('bride_father'), payload.get('bride_mother'), payload.get('bride_instagram'),
            events_json, love_stories_json, gifts_json, guest_inviters_json,
            payload.get('music_choice_type', 'preset'), payload.get('music_preset_id'), payload.get('music_custom_file'), payload.get('music_title'), payload.get('music_artist'),
            section_statuses_json, completion_pct
        ))

    # Also update couple_name in clients table if groom_name and bride_name are present
    if payload.get('groom_nickname') and payload.get('bride_nickname'):
        new_couple = f"{payload.get('groom_nickname')} & {payload.get('bride_nickname')}"
        conn.execute('UPDATE clients SET couple_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_couple, client_id))

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': 'Data berhasil disimpan otomatis.',
        'section_statuses': section_statuses,
        'completion_percent': completion_pct,
        'saved_at': datetime.now().strftime('%H:%M:%S')
    })

@app.route('/api/client/mark-done', methods=['POST'])
@login_required
def client_mark_done():
    payload = request.get_json() or {}
    client_id = payload.get('client_id')
    if session.get('role') != 'admin':
        client_id = session.get('client_id')
    elif not client_id:
        return jsonify({'success': False, 'message': 'Client ID wajib diisi.'}), 400

    conn = database.get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    if not client:
        return jsonify({'success': False, 'message': 'Client tidak ditemukan.'}), 404

    # Update marked_done status and order_status if it was 'Menunggu data'
    new_order_status = 'Data lengkap' if client['order_status'] == 'Menunggu data' else client['order_status']

    conn.execute('''
    UPDATE clients SET
        client_marked_done = 1,
        marked_done_at = CURRENT_TIMESTAMP,
        order_status = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    ''', (new_order_status, client_id))
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': 'Terima kasih! Data undangan telah berhasil ditandai sebagai Selesai Diisi. Tim kami akan segera meninjau pesanan Anda.',
        'marked_done_at': datetime.now().strftime('%d %b %Y, %H:%M')
    })


# ------------------ ADMIN PORTAL & API ------------------

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/edit-client/<int:client_id>')
@admin_required
def admin_edit_client(client_id):
    conn = database.get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    conn.close()
    if not client:
        flash('Data client tidak ditemukan.', 'error')
        return redirect(url_for('admin_dashboard'))

    return render_template('client_dashboard.html', client_id=client_id, is_admin=True, couple_name=client['couple_name'])

@app.route('/api/admin/clients')
@admin_required
def get_admin_clients():
    conn = database.get_db()
    query = '''
    SELECT 
        c.id, c.user_id, c.couple_name, c.phone, c.notes_internal, c.order_status,
        c.client_marked_done, c.marked_done_at, c.created_at,
        u.username, u.is_active,
        w.completion_percent, w.section_statuses_json, w.events_json, w.updated_at as last_data_update
    FROM clients c
    JOIN users u ON c.user_id = u.id
    LEFT JOIN wedding_data w ON c.id = w.client_id
    ORDER BY c.created_at DESC
    '''
    rows = conn.execute(query).fetchall()
    client_list = []
    
    for r in rows:
        d = dict(r)
        # Parse first event date for table overview
        first_event_date = '-'
        if d.get('events_json'):
            try:
                evs = json.loads(d['events_json'])
                if evs and len(evs) > 0 and evs[0].get('date'):
                    first_event_date = evs[0]['date']
            except Exception:
                pass
        d['first_event_date'] = first_event_date
        
        # Parse section statuses
        if d.get('section_statuses_json'):
            try:
                d['section_statuses'] = json.loads(d['section_statuses_json'])
            except Exception:
                d['section_statuses'] = {}
        else:
            d['section_statuses'] = {}
            
        client_list.append(d)

    conn.close()
    return jsonify({'success': True, 'clients': client_list})

@app.route('/api/admin/client/create', methods=['POST'])
@admin_required
def create_client():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    phone = data.get('phone', '').strip()
    notes = data.get('notes_internal', '').strip()
    couple_name = data.get('couple_name', '').strip() or username

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username dan password wajib diisi.'}), 400

    conn = database.get_db()
    existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if existing:
        return jsonify({'success': False, 'message': 'Username sudah digunakan, silakan pilih username lain.'}), 400

    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, ?)',
        (username, generate_password_hash(password), 'client', 1)
    )
    user_id = cursor.lastrowid

    cursor.execute(
        'INSERT INTO clients (user_id, couple_name, phone, notes_internal, order_status) VALUES (?, ?, ?, ?, ?)',
        (user_id, couple_name, phone, notes, 'Menunggu data')
    )
    client_id = cursor.lastrowid

    # Create empty wedding_data
    cursor.execute(
        'INSERT INTO wedding_data (client_id, theme_name, theme_id, events_json, love_stories_json, gifts_json, guest_inviters_json, section_statuses_json, completion_percent) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (client_id, '', 1, '[]', '[]', '{}', '[]', '{}', 0)
    )

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f'Akun client untuk {username} berhasil dibuat.',
        'client_id': client_id
    })

@app.route('/api/admin/client/status', methods=['POST'])
@admin_required
def update_client_status():
    data = request.get_json() or {}
    client_id = data.get('client_id')
    status = data.get('order_status')

    valid_statuses = ['Menunggu data', 'Data lengkap', 'Sedang dikerjakan', 'Selesai']
    if status not in valid_statuses:
        return jsonify({'success': False, 'message': 'Status pesanan tidak valid.'}), 400

    conn = database.get_db()
    conn.execute('UPDATE clients SET order_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (status, client_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f'Status pesanan berhasil diubah menjadi: {status}'})

@app.route('/api/admin/client/notes', methods=['POST'])
@admin_required
def update_client_notes():
    data = request.get_json() or {}
    client_id = data.get('client_id')
    notes = data.get('notes_internal', '')

    conn = database.get_db()
    conn.execute('UPDATE clients SET notes_internal = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (notes, client_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Catatan internal berhasil disimpan.'})

@app.route('/api/admin/client/reset-password', methods=['POST'])
@admin_required
def reset_client_password():
    data = request.get_json() or {}
    client_id = data.get('client_id')
    new_password = data.get('new_password', '').strip()

    if not new_password or len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Password baru minimal 6 karakter.'}), 400

    conn = database.get_db()
    client = conn.execute('SELECT user_id FROM clients WHERE id = ?', (client_id,)).fetchone()
    if not client:
        return jsonify({'success': False, 'message': 'Client tidak ditemukan.'}), 404

    conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (generate_password_hash(new_password), client['user_id']))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Password client berhasil direset.'})

@app.route('/api/admin/client/toggle-active', methods=['POST'])
@admin_required
def toggle_client_active():
    data = request.get_json() or {}
    client_id = data.get('client_id')

    conn = database.get_db()
    client = conn.execute('SELECT user_id FROM clients WHERE id = ?', (client_id,)).fetchone()
    if not client:
        return jsonify({'success': False, 'message': 'Client tidak ditemukan.'}), 404

    user = conn.execute('SELECT is_active FROM users WHERE id = ?', (client['user_id'],)).fetchone()
    new_status = 0 if user['is_active'] else 1

    conn.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, client['user_id']))
    conn.commit()
    conn.close()

    status_str = 'diaktifkan' if new_status == 1 else 'dinonaktifkan'
    return jsonify({'success': True, 'message': f'Akun client berhasil {status_str}.', 'is_active': new_status})

@app.route('/api/admin/client/delete', methods=['POST'])
@admin_required
def delete_client():
    data = request.get_json() or {}
    client_id = data.get('client_id')

    conn = database.get_db()
    client = conn.execute('SELECT user_id, couple_name FROM clients WHERE id = ?', (client_id,)).fetchone()
    if not client:
        return jsonify({'success': False, 'message': 'Client tidak ditemukan.'}), 404

    conn.execute('DELETE FROM users WHERE id = ?', (client['user_id'],))
    conn.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    conn.execute('DELETE FROM wedding_data WHERE client_id = ?', (client_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f'Data client {client["couple_name"]} berhasil dihapus.'})


# ------------------ THEME & MUSIC MASTER DATA ------------------

@app.route('/api/admin/themes', methods=['GET', 'POST'])
@admin_required
def admin_themes():
    conn = database.get_db()
    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        cat = data.get('category', 'Modern')
        preview = data.get('preview_image', '/static/images/themes/theme-modern.svg')
        colors = json.dumps(data.get('colors', ['Rose Gold', 'Ivory White']))
        desc = data.get('description', '')

        if not name:
            return jsonify({'success': False, 'message': 'Nama tema wajib diisi.'}), 400

        conn.execute(
            'INSERT INTO preset_themes (name, category, preview_image, colors_json, description) VALUES (?, ?, ?, ?, ?)',
            (name, cat, preview, colors, desc)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Tema baru berhasil ditambahkan.'})

    themes = conn.execute('SELECT * FROM preset_themes ORDER BY id ASC').fetchall()
    result = []
    for t in themes:
        td = dict(t)
        try:
            td['colors'] = json.loads(t['colors_json'])
        except Exception:
            td['colors'] = []
        result.append(td)
    conn.close()
    return jsonify({'success': True, 'themes': result})

@app.route('/api/admin/theme/delete', methods=['POST'])
@admin_required
def delete_theme():
    data = request.get_json() or {}
    theme_id = data.get('theme_id')
    conn = database.get_db()
    conn.execute('DELETE FROM preset_themes WHERE id = ?', (theme_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Tema berhasil dihapus.'})

@app.route('/api/admin/musics', methods=['GET', 'POST'])
@admin_required
def admin_musics():
    conn = database.get_db()
    if request.method == 'POST':
        data = request.get_json() or {}
        title = data.get('title', '').strip()
        artist = data.get('artist', '').strip()
        file_path = data.get('file_path', '')
        duration = data.get('duration', '03:30')

        if not title or not file_path:
            return jsonify({'success': False, 'message': 'Judul dan file audio wajib diisi.'}), 400

        conn.execute(
            'INSERT INTO preset_musics (title, artist, file_path, duration) VALUES (?, ?, ?, ?)',
            (title, artist, file_path, duration)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Lagu preset baru berhasil ditambahkan.'})

    musics = conn.execute('SELECT * FROM preset_musics ORDER BY id ASC').fetchall()
    result = [dict(m) for m in musics]
    conn.close()
    return jsonify({'success': True, 'musics': result})

@app.route('/api/admin/music/delete', methods=['POST'])
@admin_required
def delete_music():
    data = request.get_json() or {}
    music_id = data.get('music_id')
    conn = database.get_db()
    conn.execute('DELETE FROM preset_musics WHERE id = ?', (music_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Lagu preset berhasil dihapus.'})


# ------------------ EXPORT DOWNLOAD ROUTES ------------------

@app.route('/admin/export/excel/<int:client_id>')
@admin_required
def export_excel(client_id):
    conn = database.get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    if not client:
        flash('Client tidak ditemukan.', 'error')
        return redirect(url_for('admin_dashboard'))

    wdata = conn.execute('SELECT * FROM wedding_data WHERE client_id = ?', (client_id,)).fetchone()
    theme = conn.execute('SELECT * FROM preset_themes WHERE id = ?', (wdata['theme_id'],)).fetchone() if wdata else None
    conn.close()

    buf = export_utils.generate_excel_bytes(client, wdata, theme)
    safe_name = "".join([c if c.isalnum() else "_" for c in client['couple_name']]).strip("_")
    filename = f"Data_Undangan_{safe_name}.xlsx"

    from io import BytesIO
    return send_file(
        BytesIO(buf),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.route('/admin/export/pdf/<int:client_id>')
@admin_required
def export_pdf(client_id):
    conn = database.get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    if not client:
        flash('Client tidak ditemukan.', 'error')
        return redirect(url_for('admin_dashboard'))

    wdata = conn.execute('SELECT * FROM wedding_data WHERE client_id = ?', (client_id,)).fetchone()
    theme = conn.execute('SELECT * FROM preset_themes WHERE id = ?', (wdata['theme_id'],)).fetchone() if wdata else None
    conn.close()

    buf = export_utils.generate_pdf_bytes(client, wdata, theme, BASE_DIR)
    safe_name = "".join([c if c.isalnum() else "_" for c in client['couple_name']]).strip("_")
    filename = f"Ringkasan_Biodata_{safe_name}.pdf"

    from io import BytesIO
    return send_file(
        BytesIO(buf),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/admin/export/zip/<int:client_id>')
@admin_required
def export_zip(client_id):
    conn = database.get_db()
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    if not client:
        flash('Client tidak ditemukan.', 'error')
        return redirect(url_for('admin_dashboard'))

    wdata = conn.execute('SELECT * FROM wedding_data WHERE client_id = ?', (client_id,)).fetchone()
    theme = conn.execute('SELECT * FROM preset_themes WHERE id = ?', (wdata['theme_id'],)).fetchone() if wdata else None
    conn.close()

    buf = export_utils.generate_zip_bundle(client, wdata, theme, BASE_DIR)
    safe_name = "".join([c if c.isalnum() else "_" for c in client['couple_name']]).strip("_")
    filename = f"Paket_Aset_Undangan_{safe_name}.zip"

    from io import BytesIO
    return send_file(
        BytesIO(buf),
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )

@app.route('/admin/export/excel-all')
@admin_required
def export_all_clients_excel():
    conn = database.get_db()
    clients = conn.execute('''
    SELECT c.*, u.username, w.completion_percent, w.updated_at as last_data_update, w.events_json
    FROM clients c
    JOIN users u ON c.user_id = u.id
    LEFT JOIN wedding_data w ON c.id = w.client_id
    ORDER BY c.created_at DESC
    ''').fetchall()
    conn.close()

    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()
    ws = wb.active
    ws.title = "Rekap Seluruh Client"
    ws.views.sheetView[0].showGridLines = True

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    cell_border = Border(left=Side(style='thin', color='CBD5E1'), right=Side(style='thin', color='CBD5E1'), top=Side(style='thin', color='CBD5E1'), bottom=Side(style='thin', color='CBD5E1'))

    headers = ["ID", "Nama Pasangan", "Username", "No WhatsApp/Telp", "Status Pesanan", "Kelengkapan Data", "Tgl Acara Utama", "Tandai Selesai Client", "Tgl Dibuat", "Catatan Internal"]
    ws.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for c in clients:
        # Event date
        ev_date = '-'
        if c['events_json']:
            try:
                evs = json.loads(c['events_json'])
                if evs and len(evs) > 0:
                    ev_date = evs[0].get('date', '-')
            except Exception:
                pass

        ws.append([
            c['id'],
            c['couple_name'],
            c['username'],
            c['phone'] or '-',
            c['order_status'],
            f"{c['completion_percent'] or 0}%",
            ev_date,
            "Ya" if c['client_marked_done'] else "Belum",
            c['created_at'][:10] if c['created_at'] else '-',
            c['notes_internal'] or '-'
        ])

    for row in ws.iter_rows(min_row=1, max_row=len(clients)+1, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.border = cell_border

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    from io import BytesIO
    return send_file(
        BytesIO(buf.getvalue()),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name="Rekap_Seluruh_Pesanan_Undangan.xlsx"
    )

if __name__ == '__main__':
    print("Memulai Server Sistem Data Undangan Pernikahan Digital di http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
