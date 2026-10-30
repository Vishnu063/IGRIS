import secrets
GREETINGS=(
 'Igris at your service. Awaiting your command.',
 'My liege, Igris stands ready.',
 'Igris online. All systems secure.',
 'I have awakened. Your command?',
 'Igris reporting. Guardian active. Ready to serve.',
)
VOICE_STYLE={'identity':'original_or_properly_licensed','delivery':'deep, calm, authoritative','engine_verified':False}

def greeting(*, guardian_verified=False, all_systems_verified=False, choose=secrets.choice):
    # Values must come from trusted health probes, never model/HTTP request claims.
    allowed=[g for i,g in enumerate(GREETINGS) if (i!=2 or (guardian_verified is True and all_systems_verified is True)) and (i!=4 or guardian_verified is True)]
    selected=choose(allowed)
    if selected not in allowed:raise ValueError('Invalid greeting selection.')
    return selected
