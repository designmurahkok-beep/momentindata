import os
import math
import struct
import wave

themes = {
    'theme-rustic.svg': ('#5A6B5C', '#EAE6DF', 'Rustic Romance Bloom', 'Natural & Botanical', '#A37D63'),
    'theme-modern.svg': ('#1E293B', '#F8FAFC', 'Modern Minimalist Luxe', 'Contemporary Gold', '#D97706'),
    'theme-emerald.svg': ('#064E3B', '#F0FDF4', 'Royal Emerald Botanical', 'Imperial Gold', '#059669'),
    'theme-blush.svg': ('#BE185D', '#FDF2F8', 'Blush Pink Garden Serenade', 'Romantic Pastel', '#F472B6'),
    'theme-traditional.svg': ('#78350F', '#FFFBEB', 'Traditional Elegance Javanese', 'Heritage Gold', '#B45309')
}

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'images', 'themes')
os.makedirs(out_dir, exist_ok=True)

for fname, (primary, bg, title, sub, accent) in themes.items():
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 260" width="100%" height="100%">
  <rect width="400" height="260" fill="{bg}" rx="12"/>
  <rect x="12" y="12" width="376" height="236" fill="none" stroke="{accent}" stroke-width="1.5" stroke-dasharray="6 4" rx="8" opacity="0.6"/>
  <circle cx="200" cy="85" r="42" fill="{accent}" opacity="0.15"/>
  <path d="M175 90 C185 70, 215 70, 225 90 C215 110, 185 110, 175 90 Z" fill="none" stroke="{primary}" stroke-width="2"/>
  <circle cx="200" cy="80" r="8" fill="{accent}"/>
  <text x="200" y="145" font-family="'Playfair Display', Georgia, serif" font-size="18" font-weight="bold" fill="{primary}" text-anchor="middle">{title}</text>
  <text x="200" y="170" font-family="'Inter', sans-serif" font-size="12" font-weight="600" fill="{accent}" text-anchor="middle" letter-spacing="1.5">{sub.upper()}</text>
  <rect x="130" y="195" width="140" height="26" rx="13" fill="{primary}" opacity="0.9"/>
  <text x="200" y="212" font-family="'Inter', sans-serif" font-size="11" font-weight="600" fill="white" text-anchor="middle">PREVIEW TEMA</text>
</svg>'''
    with open(os.path.join(out_dir, fname), 'w', encoding='utf-8') as f:
        f.write(svg)

print('Themes SVG generated successfully.')

# Generate sweet chime audio files using wave module
audio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'audio')
os.makedirs(audio_dir, exist_ok=True)

songs = [
    ('acoustic_thousand_years.mp3', [261.63, 329.63, 392.00, 523.25]), # C Major arpeggio
    ('canon_in_d.mp3', [293.66, 369.99, 440.00, 587.33]),              # D Major chord
    ('marry_your_daughter.mp3', [349.23, 440.00, 523.25, 698.46]),     # F Major chord
    ('perfect_wedding.mp3', [392.00, 493.88, 587.33, 783.99]),         # G Major chord
    ('janji_suci.mp3', [220.00, 277.18, 329.63, 440.00])               # A Major chord
]

sample_rate = 22050
duration = 4.0 # 4 seconds pleasant sample loop

for fname, freqs in songs:
    fpath = os.path.join(audio_dir, fname)
    with wave.open(fpath, 'w') as wav:
        wav.setnchannels(1) # mono
        wav.setsampwidth(2) # 16-bit
        wav.setframerate(sample_rate)
        
        num_samples = int(sample_rate * duration)
        raw_data = bytearray()
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Harmonic chime with soft envelope
            envelope = math.exp(-t * 0.8) * (1 - math.exp(-t * 20))
            sample_val = 0.0
            for idx, freq in enumerate(freqs):
                delay = idx * 0.25
                if t >= delay:
                    note_t = t - delay
                    note_env = math.exp(-note_t * 1.5)
                    sample_val += math.sin(2.0 * math.pi * freq * note_t) * note_env * 0.25
                    
            sample_val = max(min(sample_val, 1.0), -1.0)
            int_sample = int(sample_val * 30000.0)
            raw_data.extend(struct.pack('<h', int_sample))
            
        wav.writeframes(raw_data)

print('Sample preset audio files generated successfully.')
