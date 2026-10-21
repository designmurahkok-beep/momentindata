import sqlite3
import os
import json
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wedding_invitations.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'client', -- 'admin' or 'client'
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Clients table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        couple_name TEXT NOT NULL,
        phone TEXT,
        notes_internal TEXT DEFAULT '',
        order_status TEXT DEFAULT 'Menunggu data', -- 'Menunggu data', 'Data lengkap', 'Sedang dikerjakan', 'Selesai'
        client_marked_done INTEGER DEFAULT 0,
        marked_done_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')

    # Wedding Data (7 sections)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wedding_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER UNIQUE NOT NULL,
        
        -- Section 1: Tema Undangan
        theme_name TEXT DEFAULT '',
        theme_id INTEGER DEFAULT 1,
        theme_color TEXT DEFAULT 'Warm Gold',
        theme_custom_note TEXT DEFAULT '',
        
        -- Section 2: Biodata Pengantin
        groom_name TEXT DEFAULT '',
        groom_nickname TEXT DEFAULT '',
        groom_photo TEXT DEFAULT '',
        groom_child_order TEXT DEFAULT '',
        groom_father TEXT DEFAULT '',
        groom_mother TEXT DEFAULT '',
        groom_instagram TEXT DEFAULT '',
        
        bride_name TEXT DEFAULT '',
        bride_nickname TEXT DEFAULT '',
        bride_photo TEXT DEFAULT '',
        bride_child_order TEXT DEFAULT '',
        bride_father TEXT DEFAULT '',
        bride_mother TEXT DEFAULT '',
        bride_instagram TEXT DEFAULT '',
        
        -- Section 3: Detail Acara (JSON array)
        events_json TEXT DEFAULT '[]',
        
        -- Section 4: Love Story (JSON array)
        love_stories_json TEXT DEFAULT '[]',
        
        -- Section 5: Kado Digital (JSON object)
        gifts_json TEXT DEFAULT '{}',
        
        -- Section 6: Turut Mengundang (JSON array)
        guest_inviters_json TEXT DEFAULT '[]',
        
        -- Section 7: Backsound
        music_choice_type TEXT DEFAULT 'preset', -- 'preset' or 'upload'
        music_preset_id INTEGER DEFAULT 1,
        music_custom_file TEXT DEFAULT '',
        music_title TEXT DEFAULT '',
        music_artist TEXT DEFAULT '',
        
        -- Progress & statuses
        section_statuses_json TEXT DEFAULT '{}',
        completion_percent INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
    )
    ''')

    # Preset Themes (Master data admin)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS preset_themes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT DEFAULT 'Modern Floral',
        preview_image TEXT,
        colors_json TEXT DEFAULT '["Rose Gold", "Earthy Sage", "Champagne Gold", "Navy Blue", "Pure White"]',
        description TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Preset Musics (Master data admin)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS preset_musics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        artist TEXT NOT NULL,
        file_path TEXT NOT NULL,
        duration TEXT DEFAULT '03:45',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()

    # Migration check for existing DB: add theme_name if missing
    cursor.execute("PRAGMA table_info(wedding_data)")
    cols = [col[1] for col in cursor.fetchall()]
    if 'theme_name' not in cols:
        cursor.execute("ALTER TABLE wedding_data ADD COLUMN theme_name TEXT DEFAULT ''")
        conn.commit()

    # Seed Admin if not exists
    cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
    admin_row = cursor.fetchone()
    if not admin_row:
        cursor.execute(
            'INSERT INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, ?)',
            ('admin', generate_password_hash('admin123'), 'admin', 1)
        )
        conn.commit()

    # Seed Preset Themes if empty
    cursor.execute('SELECT COUNT(*) FROM preset_themes')
    if cursor.fetchone()[0] == 0:
        themes = [
            (
                'Rustic Romance Bloom',
                'Rustic & Natural',
                '/static/images/themes/theme-rustic.svg',
                json.dumps(['Earthy Sage', 'Warm Terracotta', 'Sand Cream', 'Forest Pine']),
                'Nuansa kayu hangat, dedaunan eucalytpus dan bunga kering elegan cocok untuk pesta outdoor atau semi-formal.'
            ),
            (
                'Modern Minimalist Luxe',
                'Minimalist',
                '/static/images/themes/theme-modern.svg',
                json.dumps(['Champagne Gold', 'Monochrome Charcoal', 'Soft Ivory', 'Dusty Mauve']),
                'Tipografi bersih, garis geometris tegas, dan sentuhan foil emas mewah untuk pasangan berjiwa kontemporer.'
            ),
            (
                'Royal Emerald Botanical',
                'Botanical Luxury',
                '/static/images/themes/theme-emerald.svg',
                json.dumps(['Emerald Green', 'Imperial Gold', 'Ivory Pearl', 'Deep Midnight']),
                'Warna hijau zamrud dipadukan dengan aksen emas kerajaan yang megah dan berkelas.'
            ),
            (
                'Blush Pink Garden Serenade',
                'Floral Pastel',
                '/static/images/themes/theme-blush.svg',
                json.dumps(['Blush Rose', 'Lavender Mist', 'Peach Sorbet', 'Cloud White']),
                'Sentuhan lembut kelopak mawar merah muda dan nuansa taman bermekaran yang romantis.'
            ),
            (
                'Traditional Elegance Javanese',
                'Traditional Heritage',
                '/static/images/themes/theme-traditional.svg',
                json.dumps(['Classic Gold', 'Prada Cokelat', 'Royal Velvet Black', 'Maroon']),
                'Ornamen batik klasik dan gunungan pewayangan dengan warna emas prada yang khidmat dan sakral.'
            )
        ]
        for t in themes:
            cursor.execute(
                'INSERT INTO preset_themes (name, category, preview_image, colors_json, description) VALUES (?, ?, ?, ?, ?)',
                t
            )
        conn.commit()

    # Seed Preset Musics if empty
    cursor.execute('SELECT COUNT(*) FROM preset_musics')
    if cursor.fetchone()[0] == 0:
        musics = [
            ('A Thousand Years (Acoustic Guitar & Violin)', 'Christina Perri (Acoustic)', '/static/audio/acoustic_thousand_years.mp3', '04:12'),
            ('Canon in D Major (Romantic Piano Strings)', 'Johann Pachelbel', '/static/audio/canon_in_d.mp3', '03:30'),
            ('Marry Your Daughter (Romantic Piano)', 'Brian McKnight (Instrumental)', '/static/audio/marry_your_daughter.mp3', '03:55'),
            ('Perfect (Orchestral Wedding Acoustic)', 'Ed Sheeran (Acoustic Strings)', '/static/audio/perfect_wedding.mp3', '04:20'),
            ('Janji Suci (Romantic Acoustic Cover)', 'Yovie & Nuno (Instrumental)', '/static/audio/janji_suci.mp3', '03:40')
        ]
        for m in musics:
            cursor.execute(
                'INSERT INTO preset_musics (title, artist, file_path, duration) VALUES (?, ?, ?, ?)',
                m
            )
        conn.commit()

    # Seed Sample Client (Rizky & Anisa) if not exists
    cursor.execute('SELECT id FROM users WHERE username = ?', ('rizky_anisa',))
    client_row = cursor.fetchone()
    if not client_row:
        cursor.execute(
            'INSERT INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, ?)',
            ('rizky_anisa', generate_password_hash('pass123'), 'client', 1)
        )
        user_id = cursor.lastrowid
        cursor.execute(
            '''INSERT INTO clients (user_id, couple_name, phone, notes_internal, order_status, client_marked_done)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (user_id, 'Rizky & Anisa', '081234567890', 'Paket Platinum. Client meminta revisi warna rose gold lebih lembut.', 'Sedang dikerjakan', 1)
        )
        client_id = cursor.lastrowid

        events_sample = [
            {
                'id': 1,
                'name': 'Akad Nikah',
                'date': '2026-11-20',
                'start_time': '08:00',
                'end_time': '10:00',
                'location_name': 'Masjid Agung Al-Azhar',
                'address': 'Jl. Sisingamangaraja No.1, Selong, Kebayoran Baru, Jakarta Selatan',
                'maps_url': 'https://maps.google.com/?q=Masjid+Agung+Al-Azhar'
            },
            {
                'id': 2,
                'name': 'Resepsi Pernikahan',
                'date': '2026-11-20',
                'start_time': '11:00',
                'end_time': '14:00',
                'location_name': 'Grand Ballroom Hotel Mulia Senayan',
                'address': 'Jl. Asia Afrika, Gelora, Tanah Abang, Jakarta Pusat',
                'maps_url': 'https://maps.google.com/?q=Hotel+Mulia+Senayan'
            }
        ]

        stories_sample = [
            {
                'id': 1,
                'title': 'Pertemuan Pertama di Kampus',
                'date_or_year': 'Maret 2020',
                'story_text': 'Kami pertama kali berpapasan di perpustakaan kampus saat sama-sama sedang menyelesaikan tugas akhir. Senyuman sederhana menjadi awal dari percakapan panjang.',
                'photo': ''
            },
            {
                'id': 2,
                'title': 'Mengikat Janji Komitmen',
                'date_or_year': '14 Februari 2024',
                'story_text': 'Setelah 4 tahun saling mendukung dalam suka dan duka, kami memutuskan untuk melangkah ke jenjang yang lebih serius di bawah terbenamnya matahari Labuan Bajo.',
                'photo': ''
            },
            {
                'id': 3,
                'title': 'Hari Bahagia Kita',
                'date_or_year': '20 November 2026',
                'story_text': 'Dengan doa restu kedua orang tua dan keluarga tercinta, kami siap memulai lembaran baru sebagai suami istri.',
                'photo': ''
            }
        ]

        gifts_sample = {
            'bank_accounts': [
                {'bank_name': 'BCA', 'account_number': '8830129841', 'account_holder': 'Rizky Pratama'},
                {'bank_name': 'Bank Mandiri', 'account_number': '1370019283912', 'account_holder': 'Anisa Putri Maharani'}
            ],
            'ewallets': [
                {'provider': 'GoPay / Dana', 'number': '081234567890', 'account_holder': 'Rizky Pratama'}
            ],
            'qr_image': '',
            'physical_gift': {
                'recipient': 'Rizky & Anisa',
                'phone': '081234567890',
                'address': 'Jl. Kemang Raya No. 45B, Mampang Prapatan, Jakarta Selatan 12730'
            }
        }

        inviters_sample = [
            {'id': 1, 'name': 'Keluarga Besar Bpk. H. Bambang Soedirman (Jakarta)'},
            {'id': 2, 'name': 'Keluarga Besar Bpk. Ir. H. Joko Santoso (Bandung)'},
            {'id': 3, 'name': 'Keluarga Besar Alm. H. Sutisna'}
        ]

        section_statuses = {
            'theme': 'complete',
            'groom_bride': 'complete',
            'events': 'complete',
            'story': 'complete',
            'gifts': 'complete',
            'inviters': 'complete',
            'music': 'complete'
        }

        cursor.execute('''
        INSERT INTO wedding_data (
            client_id, theme_name, theme_id, theme_color, theme_custom_note,
            groom_name, groom_nickname, groom_photo, groom_child_order, groom_father, groom_mother, groom_instagram,
            bride_name, bride_nickname, bride_photo, bride_child_order, bride_father, bride_mother, bride_instagram,
            events_json, love_stories_json, gifts_json, guest_inviters_json,
            music_choice_type, music_preset_id, music_title, music_artist,
            section_statuses_json, completion_percent
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?
        )
        ''', (
            client_id, 'Rustic Botanical Gold', 1, 'Warm Sand Gold', 'Mohon font nama pengantin pakai gaya kaligrafi bersambung modern.',
            'Rizky Pratama, S.T.', 'Rizky', '', 'Putra Pertama', 'Bpk. H. Bambang Soedirman', 'Ibu Hj. Siti Nurhaliza', '@rizky.pratama',
            'Anisa Putri Maharani, S.Kom.', 'Anisa', '', 'Putri Kedua', 'Bpk. Ir. H. Joko Santoso, M.T.', 'Ibu Hj. Ratna Juwita', '@anisa.maharani',
            json.dumps(events_sample), json.dumps(stories_sample), json.dumps(gifts_sample), json.dumps(inviters_sample),
            'preset', 1, 'A Thousand Years (Acoustic Guitar & Violin)', 'Christina Perri (Acoustic)',
            json.dumps(section_statuses), 100
        ))
        conn.commit()

    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
